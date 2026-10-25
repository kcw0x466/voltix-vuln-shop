"""Explicit educational switches. High-risk evaluation lives only in lab/worker.py."""
import json
from urllib.request import Request, urlopen
from urllib.error import URLError
from flask import current_app, abort

IDS = {f'VULN-{n:02d}' for n in range(1,12)}

def enabled(vid):
    configured = current_app.config['VULNS']
    selected = set(configured.split(',')) if isinstance(configured,str) else set(configured)
    return current_app.config['LAB_MODE'] and ('all' in selected or vid in selected)

def worker(action, **payload):
    url=current_app.config['WORKER_URL']
    token=current_app.config['WORKER_TOKEN']
    if not (current_app.config['LAB_MODE'] and url and token):
        abort(503, '격리 실습 컨테이너가 연결되지 않았습니다. Docker Compose로 실행해 주세요.')
    data=json.dumps({'action':action,**payload}).encode()
    req=Request(url+'/run',data=data,headers={'Content-Type':'application/json','Authorization':'Bearer '+token})
    try:
        with urlopen(req,timeout=5) as response:
            return json.loads(response.read(65536))['output']
    except (URLError,TimeoutError,ValueError,KeyError):
        abort(503,'실습 컨테이너 응답 오류 또는 실행 시간 초과')
