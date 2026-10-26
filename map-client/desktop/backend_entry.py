"""Entry point for the bundled service."""
import os,sys
from pathlib import Path
if getattr(sys,'frozen',False):os.environ.setdefault('TOTK_RESOURCE_ROOT',str(Path(sys.executable).resolve().parent.parent))
else:sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from server import main
if __name__=='__main__':main()
