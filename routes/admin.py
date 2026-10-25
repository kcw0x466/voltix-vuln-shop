from pathlib import Path
from flask import Blueprint,render_template,request,g,redirect,url_for,abort
from database import get_db
from routes.common import admin_required,login_required,one,number
from vulnerabilities import enabled,worker,IDS
bp=Blueprint('admin',__name__)

@bp.get('/admin')
@admin_required
def index():
    db=get_db()
    # Explicit projections: password hashes and PIN hashes are never displayed.
    tables={
      '회원':db.execute('SELECT id,username,name,email,phone,role FROM users').fetchall(),
      '상품':db.execute('SELECT id,name,price,stock,active FROM products').fetchall(),
      '주문':db.execute('SELECT * FROM orders ORDER BY id DESC').fetchall(),
      '결제':db.execute('SELECT id,order_id,method,requested_amount,approved_amount,status,reason,created_at FROM payments ORDER BY id DESC').fetchall(),
      '게시글':db.execute('SELECT id,title,user_id,created_at FROM posts ORDER BY id DESC').fetchall()}
    return render_template('admin/index.html',tables=tables)

@bp.post('/admin/users/<int:uid>')
@admin_required
def user(uid):
    one('SELECT id FROM users WHERE id=?',(uid,));role=request.form.get('role')
    if role not in ('user','admin'): abort(400)
    db=get_db()
    with db: db.execute('UPDATE users SET role=? WHERE id=?',(role,uid))
    return redirect(url_for('admin.index'))

@bp.route('/admin/products/new',methods=['GET','POST'])
@bp.route('/admin/products/<int:pid>',methods=['GET','POST'])
@admin_required
def product(pid=None):
    db=get_db();p=one('SELECT * FROM products WHERE id=?',(pid,)) if pid else None
    if request.method=='POST':
        if request.form.get('delete') and pid:
            with db: db.execute('UPDATE products SET active=0 WHERE id=?',(pid,))
        else:
            name=request.form.get('name','').strip();desc=request.form.get('description','').strip()
            price=number(request.form.get('price'),1);stock=number(request.form.get('stock'),0,100000)
            cat=number(request.form.get('category_id'),1,4);image=request.form.get('image','product01.png')
            if not name or image not in {f'product{i:02}.png' for i in range(1,10)}: abort(400)
            with db:
                if pid: db.execute('UPDATE products SET name=?,description=?,price=?,stock=?,category_id=?,image=?,active=1 WHERE id=?',(name,desc,price,stock,cat,image,pid));db.execute('UPDATE product_images SET image=? WHERE product_id=?',(image,pid))
                else:
                    new=db.execute('INSERT INTO products(name,description,price,stock,category_id,image) VALUES(?,?,?,?,?,?)',(name,desc,price,stock,cat,image)).lastrowid
                    db.execute('INSERT INTO product_images(product_id,image) VALUES(?,?)',(new,image))
        return redirect(url_for('admin.index'))
    return render_template('admin/product.html',p=p)

@bp.route('/admin/diagnostics',methods=['GET','POST'])
@admin_required
def diagnostics():
    output=None
    if request.method=='POST':
        target=request.form.get('target','voltix-demo')[:200]
        if enabled('VULN-10'):
            output=worker('command',target=target) # VULN-10 only inside disposable worker.
        else:
            if target not in {'voltix-demo','database','payment'}: abort(400,'지원되는 진단 대상이 아닙니다.')
            output=target+': 정상 (가상 진단)'
    return render_template('admin/diagnostics.html',output=output)

@bp.route('/account/message',methods=['GET','POST'])
@login_required
def message():
    output=None
    if request.method=='POST':
        text=request.form.get('message','')[:2000]
        # VULN-08: actual render_template_string runs only in isolated worker.
        output=worker('template',template=text) if enabled('VULN-08') else text
    return render_template('auth/message.html',output=output)

@bp.post('/admin/orders/<int:oid>/cancel')
@admin_required
def cancel_order(oid):
    from services.payment_service import cancel
    order=one('SELECT * FROM orders WHERE id=?',(oid,))
    if not cancel(oid,order['user_id']): abort(409,'이미 취소된 주문입니다.')
    return redirect(url_for('orders.detail',oid=oid))
