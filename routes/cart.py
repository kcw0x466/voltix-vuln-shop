from flask import Blueprint,g,request,render_template,redirect,url_for,abort
from database import get_db
from routes.common import login_required,one,number
bp=Blueprint('cart',__name__)

def items():
    return get_db().execute('SELECT ci.*,p.name,p.price,p.image,p.stock,p.active FROM cart_items ci JOIN carts c ON c.id=ci.cart_id JOIN products p ON p.id=ci.product_id WHERE c.user_id=?',(g.user['id'],)).fetchall()

@bp.get('/cart')
@login_required
def index():
    rows=items();return render_template('orders/cart.html',items=rows,total=sum(r['price']*r['quantity'] for r in rows))

@bp.post('/cart/add/<int:pid>')
@login_required
def add(pid):
    p=one('SELECT * FROM products WHERE id=? AND active=1',(pid,));qty=number(request.form.get('quantity',1),1,99)
    db=get_db();cid=one('SELECT id FROM carts WHERE user_id=?',(g.user['id'],))['id']
    old=db.execute('SELECT quantity FROM cart_items WHERE cart_id=? AND product_id=?',(cid,pid)).fetchone()
    if qty+(old[0] if old else 0)>p['stock']: abort(409,'재고가 부족합니다.')
    with db: db.execute('INSERT INTO cart_items(cart_id,product_id,quantity) VALUES(?,?,?) ON CONFLICT(cart_id,product_id) DO UPDATE SET quantity=quantity+excluded.quantity',(cid,pid,qty))
    return redirect(url_for('cart.index'))

@bp.post('/cart/<int:item_id>')
@login_required
def update(item_id):
    row=one('SELECT ci.*,p.stock FROM cart_items ci JOIN carts c ON c.id=ci.cart_id JOIN products p ON p.id=ci.product_id WHERE ci.id=? AND c.user_id=?',(item_id,g.user['id']))
    db=get_db();qty=number(request.form.get('quantity',0),0,99)
    if qty>row['stock']: abort(409,'재고가 부족합니다.')
    with db:
        if qty: db.execute('UPDATE cart_items SET quantity=? WHERE id=?',(qty,item_id))
        else: db.execute('DELETE FROM cart_items WHERE id=?',(item_id,))
    return redirect(url_for('cart.index'))
