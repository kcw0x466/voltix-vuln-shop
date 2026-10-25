from flask import Blueprint,request,g,render_template,redirect,url_for,flash
from database import get_db
from routes.common import login_required,one,number
from services.payment_service import pay
from vulnerabilities import enabled
bp=Blueprint('payments',__name__)

@bp.route('/payments/<int:oid>',methods=['GET','POST'])
@login_required
def checkout(oid):
    order=one('SELECT * FROM orders WHERE id=? AND user_id=?',(oid,g.user['id']))
    if request.method=='POST':
        amount=number(request.form.get('amount'),1,100000000)
        ok,message=pay(oid,g.user['id'],request.form.get('method',''),amount,request.form,enabled('VULN-11'))
        flash(message,'success' if ok else 'danger')
        return redirect(url_for('payments.complete',oid=oid))
    return render_template('payment/checkout.html',order=order,wallet=one('SELECT * FROM wallets WHERE user_id=?',(g.user['id'],)))

@bp.get('/payments/<int:oid>/complete')
@login_required
def complete(oid):
    order=one('SELECT * FROM orders WHERE id=? AND user_id=?',(oid,g.user['id']))
    payment=get_db().execute('SELECT * FROM payments WHERE order_id=? ORDER BY id DESC LIMIT 1',(oid,)).fetchone()
    return render_template('payment/complete.html',order=order,payment=payment)
