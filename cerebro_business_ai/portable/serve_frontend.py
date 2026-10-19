"""Serve the bundled React build on loopback, including runtime API config."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import urlsplit

class Frontend(SimpleHTTPRequestHandler):
    gateway_port=8900
    def do_GET(self):
        if urlsplit(self.path).path=='/cerebro-config.js':
            data=('window.__CEREBRO_CONFIG__ = '+json.dumps({'apiUrl':f'http://127.0.0.1:{self.gateway_port}'})+';').encode()
            self.send_response(200);self.send_header('Content-Type','application/javascript');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
            return
        return super().do_GET()
    def list_directory(self,path):
        self.send_error(404,'Directory browsing is disabled')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8905);parser.add_argument('--gateway-port',type=int,default=8900);args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]/'frontend/dist'
    Frontend.gateway_port=args.gateway_port
    ThreadingHTTPServer(('127.0.0.1',args.port),partial(Frontend,directory=str(root))).serve_forever()
