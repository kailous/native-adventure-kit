import json,sys,threading,unittest,ssl,tempfile,urllib.request,urllib.error,os,plistlib
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'map-client/backend'))
from phone_motion import PhoneMotion,MotionError
from local_https import LocalHTTPS
from server import Handler,ThreadingHTTPServer
class Native:
 def __init__(self):self.calls=[]
 def send(self,op=0,*args):
  self.calls.append((op,args));return dict(gameVersion='1.4.3',gyroEnabled=True,active=op==1,selected=op==1)
class Sessions(unittest.TestCase):
 def setUp(self):self.now=10;self.native=Native();self.motion=PhoneMotion(self.native,lambda:self.now)
 def test_owner_sequences_expiry_and_stop(self):
  token=self.motion.execute({'action':'start'},'phone')['token']
  with self.assertRaises(MotionError):self.motion.execute({'action':'start'},'other')
  data=dict(action='sample',token=token,sequence=1,acc=[0,0,-1],gyro=[0,.1,0],ageMs=10)
  self.assertTrue(self.motion.execute(data,'phone')['native']['selected'])
  with self.assertRaises(MotionError):self.motion.execute(data,'phone')
  with self.assertRaises(MotionError):self.motion.execute(dict(data,sequence=2),'other')
  self.motion.execute(dict(action='stop',token=token,sequence=2),'phone')
  self.assertEqual(self.native.calls[-1][0],2)
  with self.assertRaises(MotionError):self.motion.execute(dict(data,sequence=3),'phone')
  self.motion.execute({'action':'start'},'other');self.now+=4
  self.motion.execute({'action':'start'},'phone')
 def test_bad_vectors_age_and_calibration(self):
  token=self.motion.execute({'action':'start'},'phone')['token']
  data=dict(action='sample',token=token,sequence=1,acc=[0,0,-1],gyro=[0,0,0],ageMs=0)
  for bad in [dict(acc=[0,0,9]),dict(gyro=[float('nan'),0,0]),dict(sequence=True),dict(ageMs=101)]:
   with self.assertRaises((ValueError,MotionError)):self.motion.execute(dict(data,**bad),'phone')
  self.motion.execute(dict(action='calibrate',token=token,sequence=1),'phone')
  self.assertEqual(self.native.calls[-1][0],0)
  self.motion.execute(dict(data,sequence=2),'phone');self.motion.stop();self.assertIsNone(self.motion.owner)
class TLS(unittest.TestCase):
 def test_persistent_ca_leaf_ip_rotation_and_profile(self):
  with tempfile.TemporaryDirectory() as directory:
   tls=LocalHTTPS(Path(directory)/'tls');tls.prepare(['192.168.1.2']);ca=tls.certificate();fingerprint=tls.fingerprint
   leaf=(tls.root/'server.pem').read_bytes();tls.prepare(['192.168.1.2']);self.assertEqual(leaf,(tls.root/'server.pem').read_bytes())
   tls.prepare(['192.168.1.3']);self.assertEqual(ca,tls.certificate());self.assertEqual(fingerprint,tls.fingerprint)
   self.assertNotEqual(leaf,(tls.root/'server.pem').read_bytes())
   profile=plistlib.loads(tls.profile());self.assertEqual(profile['PayloadContent'][0]['PayloadContent'],ca)
   self.assertEqual((tls.root/'ca-key.pem').stat().st_mode&0o777,0o600)
   self.assertEqual(tls.root.stat().st_mode&0o777,0o700)
   (tls.root/'ca.pem').unlink()
   with self.assertRaises(RuntimeError):tls.prepare(['192.168.1.3'])
 def test_trusted_tls_routes_origin_and_http_motion_rejection(self):
  with tempfile.TemporaryDirectory() as directory:
   http=ThreadingHTTPServer(('127.0.0.1',0),Handler)
   for key,value in dict(lan_hosts=[],source=None,mcp_token='test',map_service=None,tunnel=None,phone_motion=PhoneMotion(Native())).items():setattr(http,key,value)
   tls=LocalHTTPS(Path(directory)/'tls');http.local_https=tls
   thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
   try:
    self.assertTrue(tls.start(http,Handler,port=0)['available']);port=tls.listener.server_port
    context=ssl.create_default_context(cafile=str(tls.root/'ca.pem'));base=f'https://127.0.0.1:{port}'
    result=json.load(urllib.request.urlopen(base+'/api/phone-motion',context=context));self.assertTrue(result['secure'])
    self.assertTrue(result['native']['available'])
    cert=urllib.request.urlopen(base+'/phone-certificate.cer',context=context).read();self.assertEqual(cert,tls.certificate())
    with self.assertRaises(urllib.error.URLError):urllib.request.urlopen(base+'/api/phone-motion')
    def post(url,origin):return urllib.request.Request(url+'/api/phone-motion',data=b'{"action":"start"}',headers={'Content-Type':'application/json','Origin':origin})
    self.assertIn('token',json.load(urllib.request.urlopen(post(base,base),context=context)))
    with self.assertRaises(urllib.error.HTTPError) as e:urllib.request.urlopen(post(base,'http://127.0.0.1:'+str(port)),context=context)
    self.assertEqual(e.exception.code,403)
    clear=f'http://127.0.0.1:{http.server_port}'
    with self.assertRaises(urllib.error.HTTPError) as e:urllib.request.urlopen(post(clear,clear))
    self.assertEqual(e.exception.code,426)
    for name in ['ca-key.pem','server-key.pem']:
     with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(base+'/'+name,context=context)
   finally:tls.stop();http.shutdown();http.server_close();thread.join()
