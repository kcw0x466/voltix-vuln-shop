import sqlite3
from flask import Blueprint,render_template,request,redirect,url_for,session,g,flash,abort
from werkzeug.security import check_password_hash,generate_password_hash
from database import get_db
from database.seed import create_user
from routes.common import login_required,one,owns,number
from vulnerabilities import enabled
bp=Blueprint('auth',__name__)

@bp.route('/register',methods=['GET','POST'])
def register():
    if request.method=='POST':
        username=request.form.get('username','').strip()
        password=request.form.get('password','')
        name=request.form.get('name','').strip()
        if not username.isascii() or not username.replace('_','').isalnum() or len(username)>40 or len(password)<8 or not name:
            abort(400,'아이디는 영문/숫자/밑줄, 비밀번호는 8자 이상, 이름을 입력하세요.')
        db=get_db()
        try:
            with db: uid=create_user(db,username,password,name)
        except sqlite3.IntegrityError: abort(409,'이미 사용 중인 아이디입니다.')
        session.clear();session['user_id']=uid
        return redirect(url_for('auth.profile'))
    return render_template('auth/login.html',register=True)

@bp.route('/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
        db=get_db(); username=request.form.get('username','');password=request.form.get('password','')
        if enabled('VULN-01'):
            # VULN-01: raw username concatenation; password function preserves normal logins.
            db.create_function('verify_password',1,lambda stored:int(check_password_hash(stored,password)))
            try: user=db.execute("SELECT * FROM users WHERE username='"+username+"' AND verify_password(password)=1").fetchone()
            except sqlite3.Error: user=None
        else:
            user=db.execute('SELECT * FROM users WHERE username=?',(username,)).fetchone()
            if user and not check_password_hash(user['password'],password): user=None
        if user:
            session.clear();session['user_id']=user['id']
            return redirect(url_for('products.home'))
        flash('아이디 또는 비밀번호를 확인해 주세요.','danger')
    return render_template('auth/login.html',register=False)

@bp.post('/logout')
def logout():
    session.clear();return redirect(url_for('products.home'))

@bp.route('/account',methods=['GET','POST'])
@login_required
def profile():
    db=get_db()
    if request.method=='POST':
        # VULN-07: see central CSRF guard; fields remain parameterized.
        with db: db.execute('UPDATE users SET name=?,email=?,phone=? WHERE id=?',(request.form.get('name',''),request.form.get('email',''),request.form.get('phone',''),g.user['id']))
        flash('회원정보를 저장했습니다.','success');return redirect(url_for('auth.profile'))
    uid=number(request.args.get('user_id',g.user['id']),1)
    if not enabled('VULN-05') and uid!=g.user['id']: abort(403)
    return render_template('auth/profile.html',profile=one('SELECT * FROM users WHERE id=?',(uid,)),addresses=db.execute('SELECT * FROM addresses WHERE user_id=?',(uid,)).fetchall(),wallet=one('SELECT * FROM wallets WHERE user_id=?',(uid,)),cards=db.execute('SELECT id,number,expiry,balance FROM virtual_cards WHERE user_id=?',(uid,)).fetchall(),transactions=db.execute('SELECT * FROM wallet_transactions WHERE user_id=? ORDER BY id DESC LIMIT 30',(uid,)).fetchall())

@bp.post('/account/password')
@login_required
def password():
    if not check_password_hash(g.user['password'],request.form.get('current_password','')): abort(400,'현재 비밀번호를 확인하세요.')
    new=request.form.get('new_password','')
    if len(new)<8: abort(400,'비밀번호는 8자 이상이어야 합니다.')
    db=get_db()
    with db: db.execute('UPDATE users SET password=? WHERE id=?',(generate_password_hash(new),g.user['id']))
    flash('비밀번호를 변경했습니다.','success');return redirect(url_for('auth.profile'))

@bp.post('/account/addresses')
@login_required
def address():
    db=get_db();aid=request.form.get('id')
    if aid:
        item=one('SELECT * FROM addresses WHERE id=?',(number(aid,1),));owns(item)
        if request.form.get('delete'):
            with db: db.execute('DELETE FROM addresses WHERE id=?',(aid,))
            return redirect(url_for('auth.profile'))
    fields=[request.form.get(k,'').strip() for k in ('recipient','phone','postcode','address')]
    if not all(fields) or len(fields[2])!=5 or not fields[2].isdigit(): abort(400,'배송지와 5자리 우편번호를 입력하세요.')
    with db:
        if aid: db.execute('UPDATE addresses SET recipient=?,phone=?,postcode=?,address=? WHERE id=?',(*fields,aid))
        else: db.execute('INSERT INTO addresses(recipient,phone,postcode,address,user_id) VALUES(?,?,?,?,?)',(*fields,g.user['id']))
    return redirect(url_for('auth.profile'))

@bp.post('/account/topup')
@login_required
def topup():
    amount=number(request.form.get('amount'),1000,1000000)
    db=get_db()
    with db:
        db.execute('UPDATE wallets SET balance=balance+? WHERE user_id=?',(amount,g.user['id']))
        db.execute("INSERT INTO wallet_transactions(user_id,amount,kind) VALUES(?,?,'TOPUP')",(g.user['id'],amount))
    flash('가상 포인트를 충전했습니다.','success');return redirect(url_for('auth.profile'))
