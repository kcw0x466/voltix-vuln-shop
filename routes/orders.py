from flask import Blueprint,g,request,render_template,redirect,url_for,abort,flash
from database import get_db
from routes.common import login_required,one,number
from routes.cart import items
from services.payment_service import cancel
from vulnerabilities import enabled
bp=Blueprint('orders',__name__)

@bp.route('/checkout',methods=['GET','POST'])
@login_required
def checkout():
    db=get_db()
    if request.method=='POST':
        aid=number(request.form.get('address_id'),1)
        db.execute('BEGIN IMMEDIATE')
        try:
            address=one('SELECT * FROM addresses WHERE id=? AND user_id=?',(aid,g.user['id']))
            rows=items()
            if not rows: abort(400,'장바구니가 비어 있습니다.')
            total=sum(r['price']*r['quantity'] for r in rows)
            oid=db.execute("INSERT INTO orders(user_id,status,total,recipient,phone,postcode,address) VALUES(?,'PENDING',?,?,?,?,?)",(g.user['id'],total,address['recipient'],address['phone'],address['postcode'],address['address'])).lastrowid
            for r in rows:
                if not r['active'] or not db.execute('UPDATE products SET stock=stock-? WHERE id=? AND stock>=?',(r['quantity'],r['product_id'],r['quantity'])).rowcount: abort(409,'상품 재고가 부족합니다.')
                db.execute('INSERT INTO order_items(order_id,product_id,name,price,quantity) VALUES(?,?,?,?,?)',(oid,r['product_id'],r['name'],r['price'],r['quantity']))
            db.execute('DELETE FROM cart_items WHERE cart_id=(SELECT id FROM carts WHERE user_id=?)',(g.user['id'],));db.commit()
        except Exception: db.rollback();raise
        return redirect(url_for('payments.checkout',oid=oid))
    rows=items()
    return render_template('orders/checkout.html',items=rows,total=sum(r['price']*r['quantity'] for r in rows),addresses=db.execute('SELECT * FROM addresses WHERE user_id=?',(g.user['id'],)).fetchall())

@bp.get('/orders')
@login_required
def index():
    return render_template('orders/index.html',orders=get_db().execute('SELECT * FROM orders WHERE user_id=? ORDER BY id DESC',(g.user['id'],)).fetchall())

@bp.get('/orders/<int:oid>')
@login_required
def detail(oid):
    order=one('SELECT * FROM orders WHERE id=?',(oid,))
    # VULN-05 deliberately omits object ownership for this read endpoint only.
    if not enabled('VULN-05') and order['user_id']!=g.user['id'] and g.user['role']!='admin': abort(403)
    db=get_db()
    return render_template('orders/detail.html',order=order,items=db.execute('SELECT * FROM order_items WHERE order_id=?',(oid,)).fetchall(),payments=db.execute('SELECT * FROM payments WHERE order_id=? ORDER BY id DESC',(oid,)).fetchall())

@bp.post('/orders/<int:oid>/cancel')
@login_required
def cancellation(oid):
    order=one('SELECT * FROM orders WHERE id=? AND user_id=?',(oid,g.user['id']))
    if not cancel(oid,g.user['id']): abort(409,'이미 취소된 주문입니다.')
    flash('주문이 취소되었습니다. 승인된 가상 결제는 환불됩니다.','success')
    return redirect(url_for('orders.detail',oid=oid))
