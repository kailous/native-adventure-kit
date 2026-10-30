"""Local-only TLS with a persistent per-client CA. Never installs trust."""
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import plistlib
import secrets
import ssl
import subprocess
import tempfile
import threading
import uuid

from paths import local_https_path

def _openssl(*args):
    result=subprocess.run(['/usr/bin/openssl',*map(str,args)],capture_output=True,timeout=30)
    if result.returncode:raise RuntimeError('本地 HTTPS 证书生成或校验失败，请保留证书目录并查看设置')
    return result.stdout

class LocalHTTPS:
    def __init__(self,root=None):
        self.root=Path(root) if root is not None else local_https_path()
        self.listener=None;self.error=None;self.fingerprint=None;self.hosts=[]

    def prepare(self,hosts):
        ips=sorted({str(ipaddress.IPv4Address(h)) for h in hosts if ipaddress.ip_address(h).is_private}|{'127.0.0.1'})
        root=self.root
        if root.is_symlink():raise RuntimeError('证书目录不能是符号链接')
        root.mkdir(parents=True,exist_ok=True);root.chmod(0o700)
        for p in root.iterdir():
            if p.is_symlink():raise RuntimeError('证书文件不能是符号链接')
        ca=root/'ca.pem';key=root/'ca-key.pem'
        if ca.exists()!=key.exists():raise RuntimeError('根证书不完整，请保留现有目录并手动处理；不会自动替换已信任证书')
        with tempfile.TemporaryDirectory(prefix='prepare-',dir=root) as directory:
            temp=Path(directory);cfg=temp/'extensions.cnf'
            cfg.write_text('[req]\ndistinguished_name=dn\nx509_extensions=ca\nprompt=no\n[dn]\nCN=TOTK Local Phone CA\n[ca]\nbasicConstraints=critical,CA:true,pathlen:0\nkeyUsage=critical,keyCertSign,cRLSign\nsubjectKeyIdentifier=hash\n[leaf]\nbasicConstraints=critical,CA:false\nkeyUsage=critical,digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\nsubjectAltName=DNS:localhost,'+','.join('IP:'+h for h in ips)+'\n')
            if not ca.exists():
                _openssl('req','-x509','-newkey','rsa:2048','-nodes','-sha256','-days','3650','-config',cfg,'-keyout',temp/'ca-key.pem','-out',temp/'ca.pem')
                for name in ('ca-key.pem','ca.pem'):
                    (temp/name).chmod(0o600);os.replace(temp/name,root/name)
            key.chmod(0o600);ca.chmod(0o600)
            _openssl('x509','-in',ca,'-checkend','86400','-noout')
            # Compare public keys so an accidentally replaced private key cannot
            # sign an unusable leaf or silently change the trusted identity.
            if _openssl('x509','-in',ca,'-pubkey','-noout')!=_openssl('pkey','-in',key,'-pubout'):
                raise RuntimeError('根证书与私钥不匹配；不会自动更换根证书')
            leaf=root/'server.pem';leaf_key=root/'server-key.pem';manifest=root/'hosts.json'
            try:renew=json.loads(manifest.read_text())!=ips
            except (OSError,ValueError):renew=True
            if not renew and leaf.exists() and leaf_key.exists():
                try:_openssl('x509','-in',leaf,'-checkend','604800','-noout');_openssl('verify','-CAfile',ca,leaf)
                except RuntimeError:renew=True
            else:renew=True
            if renew:
                _openssl('req','-new','-newkey','rsa:2048','-nodes','-sha256','-subj','/CN=TOTK Local Phone','-keyout',temp/'server-key.pem','-out',temp/'server.csr')
                _openssl('x509','-req','-in',temp/'server.csr','-CA',ca,'-CAkey',key,'-set_serial',str(secrets.randbits(128) or 1),'-days','365','-sha256','-extfile',cfg,'-extensions','leaf','-out',temp/'server.pem')
                for name in ('server-key.pem','server.pem'):
                    (temp/name).chmod(0o600);os.replace(temp/name,root/name)
                manifest.write_text(json.dumps(ips));manifest.chmod(0o600)
        leaf_key.chmod(0o600);leaf.chmod(0o600)
        der=self.certificate()
        self.fingerprint=':'.join(hashlib.sha256(der).hexdigest()[i:i+2] for i in range(0,64,2)).upper()
        self.hosts=ips
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.minimum_version=ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(leaf,leaf_key)
        return context

    def certificate(self):
        return ssl.PEM_cert_to_DER_cert((self.root/'ca.pem').read_text())

    def profile(self):
        der=self.certificate();identity=hashlib.sha256(der).hexdigest()
        def uid(kind):return str(uuid.uuid5(uuid.NAMESPACE_URL,'totk-local-https:'+identity+':'+kind)).upper()
        return plistlib.dumps({'PayloadType':'Configuration','PayloadVersion':1,'PayloadIdentifier':'local.totk.phone.'+identity[:16],
            'PayloadUUID':uid('profile'),'PayloadDisplayName':'TOTK 局域网陀螺仪证书','PayloadDescription':'仅安装本机地图 HTTPS 的公开根证书。请在电脑核对 SHA-256 指纹后手动启用信任；不含管理或代理设置。',
            'PayloadContent':[{'PayloadType':'com.apple.security.root','PayloadVersion':1,'PayloadIdentifier':'local.totk.phone.ca.'+identity[:16],
                'PayloadUUID':uid('ca'),'PayloadDisplayName':'TOTK Local Phone CA','PayloadCertificateFileName':'totk-phone-ca.cer','PayloadContent':der}]})

    def start(self,server,handler,port=8767):
        from http_server import ThreadingHTTPServer
        try:
            context=self.prepare(server.lan_hosts)
            try:listener=ThreadingHTTPServer(('0.0.0.0',port),handler)
            except OSError:listener=ThreadingHTTPServer(('0.0.0.0',0),handler)
            for key in ('source','mcp_token','lan_hosts','map_service','tunnel','phone_motion'):
                setattr(listener,key,getattr(server,key))
            listener.local_https=self;listener.is_local_https=True
            listener.socket=context.wrap_socket(listener.socket,server_side=True,do_handshake_on_connect=False)
            self.listener=listener
            threading.Thread(target=listener.serve_forever,name='totk-phone-https',daemon=True).start()
        except (OSError,RuntimeError,ValueError,subprocess.SubprocessError) as error:
            self.error=str(error)
        return self.status()

    def status(self):
        return {'available':self.listener is not None,'error':self.error,'fingerprint':self.fingerprint,
                'urls':[] if not self.listener else ['https://'+h+':'+str(self.listener.server_port)+'/' for h in self.listener.lan_hosts],
                'port':self.listener.server_port if self.listener else None}

    def stop(self):
        if self.listener:self.listener.shutdown();self.listener.server_close();self.listener=None
