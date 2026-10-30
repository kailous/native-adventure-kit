"""Entry point for the bundled service."""
import os,sys
from pathlib import Path
if getattr(sys,'frozen',False):os.environ.setdefault('TOTK_RESOURCE_ROOT',str(Path(sys.executable).resolve().parent.parent))
else:sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
if '--migrate-offline-layout' in sys.argv:
 from offline_layout import main
elif '--douyin-worker' in sys.argv:
 from douyin_worker import main
else:
 from server import main
if __name__=='__main__':main()
