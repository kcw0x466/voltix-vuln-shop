from functools import wraps
from flask import g, session, redirect, url_for, abort, request
from database import get_db
from vulnerabilities import enabled

def login_required(f):
    @wraps(f)
    def wrapped(*args,**kwargs):
        if not g.user:
            return redirect(url_for('auth.login'))
        return f(*args,**kwargs)
    return wrapped

def admin_required(f):
    @wraps(f)
    @login_required
    def wrapped(*args,**kwargs):
        # VULN-06: UI role hiding alone is not authorization.
        if not enabled('VULN-06') and g.user['role'] != 'admin':
            abort(403)
        return f(*args,**kwargs)
    return wrapped

def one(sql, args=()):
    row=get_db().execute(sql,args).fetchone()
    if row is None: abort(404)
    return row

def number(value, minimum=0, maximum=100000000):
    try: n=int(value)
    except (ValueError,TypeError): abort(400,'숫자 형식을 확인해 주세요.')
    if not minimum <= n <= maximum: abort(400,'허용 범위를 벗어난 값입니다.')
    return n

def owns(row):
    if row['user_id'] != g.user['id'] and g.user['role'] != 'admin': abort(403)
