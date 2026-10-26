"""TOTK offline MCP stdio server."""
import sys,json,argparse
from pathlib import Path
from server import SaveSource,default_save_roots
from map_service import MapService
from mcp_protocol import TOOLS,dispatch

def run(service):
 for line in sys.stdin:
  try:response=dispatch(service,json.loads(line))
  except json.JSONDecodeError as e:response={'jsonrpc':'2.0','id':None,'error':{'code':-32700,'message':str(e)}}
  if response is not None:print(json.dumps(response,ensure_ascii=False),flush=True)
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--save-dir',type=Path,action='append');args=parser.parse_args();run(MapService(SaveSource(args.save_dir or default_save_roots())))
