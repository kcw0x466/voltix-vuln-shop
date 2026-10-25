"""Run inside Compose shop: docker compose exec -T shop python scripts/verify_worker.py"""
import base64
import json
import os
from urllib.request import Request,urlopen
url=os.environ['VOLTIX_WORKER_URL']+'/run'
token=os.environ['VOLTIX_WORKER_TOKEN']

def run(action,**payload):
    req=Request(url,data=json.dumps({'action':action,**payload}).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+token})
    with urlopen(req,timeout=8) as response: return json.load(response)['output']

assert run('template',template='{{7*7}}').strip()=='49'
assert 'uid=' in run('command',target='voltix-demo; id')
assert 'ValueError' in run('command',target='voltix-demo; cat /etc/passwd')
assert run('upload',source=base64.b64encode(b'print("VOLTIX-UPLOAD-OK")').decode()).strip()=='VOLTIX-UPLOAD-OK'
network=run('upload',source=base64.b64encode(b'import socket; socket.socket()').decode())
assert 'Operation not permitted' in network,network
run('upload',source=base64.b64encode(b'while True: pass').decode())  # HTTP response must return within 8 seconds.
print('worker: SSTI, command injection, upload execution, command limits, network denial verified')
