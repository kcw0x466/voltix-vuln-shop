"""Virtual providers only. A single write transaction serializes money and state changes."""
from datetime import datetime
from flask import current_app
from werkzeug.security import check_password_hash
from database import get_db

class Declined(Exception): pass

def wallet_charge(db,uid,amount,form):
    changed=db.execute('UPDATE wallets SET balance=balance-? WHERE user_id=? AND balance>=?',(amount,uid,amount)).rowcount
    if not changed: raise Declined('포인트 잔액 부족')
    return None

def card_charge(db,uid,amount,form):
    card=db.execute('SELECT * FROM virtual_cards WHERE user_id=? AND number=?',(uid,form.get('card_number',''))).fetchone()
    if not card or form.get('expiry')!=card['expiry'] or not check_password_hash(card['pin'],form.get('pin','')):
        raise Declined('테스트 카드 인증 실패')
    month,year=map(int,card['expiry'].split('/'))
    now=datetime.now()
    if (2000+year,month)<(now.year,now.month): raise Declined('테스트 카드 유효기간 만료')
    if not db.execute('UPDATE virtual_cards SET balance=balance-? WHERE id=? AND balance>=?',(amount,card['id'],amount)).rowcount:
        raise Declined('가상 카드 한도 부족')
    return card['id']

PROVIDERS={'wallet':wallet_charge,'card':card_charge}

def pay(order_id,uid,method,amount,form,trust_amount=False):
    db=get_db();db.execute('BEGIN IMMEDIATE')
    try:
        order=db.execute('SELECT * FROM orders WHERE id=? AND user_id=?',(order_id,uid)).fetchone()
        if not order or order['status'] not in ('PENDING','FAILED'):
            db.rollback();return False,'이미 처리되었거나 결제할 수 없는 주문입니다.'
        expected=db.execute('SELECT sum(price*quantity) FROM order_items WHERE order_id=?',(order_id,)).fetchone()[0]
        reason=None
        # VULN-11: trust client amount only when this individual lesson is enabled.
        if not trust_amount and amount!=expected: reason='서버 주문 금액과 요청 금액 불일치'
        elif method not in PROVIDERS: reason='지원하지 않는 결제 수단'
        card_id=None
        if not reason:
            try: card_id=PROVIDERS[method](db,uid,amount,form)
            except Declined as e: reason=str(e)
        status='DECLINED' if reason else 'APPROVED'
        db.execute('INSERT INTO payments(order_id,method,card_id,requested_amount,approved_amount,status,reason) VALUES(?,?,?,?,?,?,?)',(order_id,method,card_id,amount,None if reason else amount,status,reason))
        db.execute('UPDATE orders SET status=? WHERE id=?',('FAILED' if reason else 'PAID',order_id))
        if not reason and method=='wallet':
            db.execute("INSERT INTO wallet_transactions(user_id,amount,kind,order_id) VALUES(?,?,'PAYMENT',?)",(uid,-amount,order_id))
        db.commit()
        current_app.logger.info('payment order=%s result=%s method=%s',order_id,status,method if method in PROVIDERS else 'unknown')
        return not reason,reason or '가상 결제가 승인되었습니다.'
    except Exception:
        db.rollback();raise

def cancel(order_id,uid):
    db=get_db();db.execute('BEGIN IMMEDIATE')
    try:
        order=db.execute('SELECT * FROM orders WHERE id=? AND user_id=?',(order_id,uid)).fetchone()
        if not order or order['status'] in ('CANCELLED','REFUNDED'):
            db.rollback();return False
        payment=db.execute("SELECT * FROM payments WHERE order_id=? AND status='APPROVED'",(order_id,)).fetchone()
        state='CANCELLED'
        if payment:
            amount=payment['approved_amount'];state='REFUNDED'
            if payment['method']=='wallet':
                db.execute('UPDATE wallets SET balance=balance+? WHERE user_id=?',(amount,uid))
                db.execute("INSERT INTO wallet_transactions(user_id,amount,kind,order_id) VALUES(?,?,'REFUND',?)",(uid,amount,order_id))
            else: db.execute('UPDATE virtual_cards SET balance=balance+? WHERE id=?',(amount,payment['card_id']))
            db.execute("UPDATE payments SET status='REFUNDED' WHERE id=?",(payment['id'],))
        for item in db.execute('SELECT * FROM order_items WHERE order_id=?',(order_id,)).fetchall():
            db.execute('UPDATE products SET stock=stock+? WHERE id=?',(item['quantity'],item['product_id']))
        db.execute('UPDATE orders SET status=? WHERE id=?',(state,order_id));db.commit()
        current_app.logger.info('order cancellation order=%s result=%s',order_id,state)
        return True
    except Exception:
        db.rollback();raise
