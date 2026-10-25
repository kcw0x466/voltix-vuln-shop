"""Disposable execution worker. Never run directly on a personal workstation."""
import base64
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
from flask import Flask, request, abort

app=Flask(__name__)
app.config['MAX_CONTENT_LENGTH']=3*1024*1024
TOKEN=os.environ.get('VOLTIX_WORKER_TOKEN','')

@app.post('/run')
def run():
    import secrets
    if not TOKEN or not secrets.compare_digest(request.headers.get('Authorization',''),'Bearer '+TOKEN): abort(403)
    body=request.get_json();action=body.get('action')
    if action not in ('template','command','upload'): abort(400)
    # The HTTP parent never evaluates user templates, shells, or uploaded code.
    with tempfile.TemporaryDirectory(dir='/scratch') as directory:
        payload=Path(directory)/'payload.json';payload.write_text(json.dumps(body))
        output=Path(directory)/'output.txt'
        with output.open('wb') as stream:
            try:
                process=subprocess.Popen([sys.executable,'/worker/child.py',str(payload)],cwd=directory,
                               env={'PATH':'/usr/local/bin:/usr/bin:/bin','LANG':'C.UTF-8'},
                               stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
                process.wait(timeout=3)
            except subprocess.TimeoutExpired as e:
                # Kill descendants too; no orphan shell can survive a timed-out lesson.
                import signal
                try: os.killpg(process.pid,signal.SIGKILL)
                except ProcessLookupError: pass
                process.wait()
                return {'output':'실행 시간 제한 (3초)'}
        import signal
        try: os.killpg(process.pid,signal.SIGKILL)
        except ProcessLookupError: pass
        return {'output':output.read_bytes()[:32768].decode('utf-8',errors='replace')}
