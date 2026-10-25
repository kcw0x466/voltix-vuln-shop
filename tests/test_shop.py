import io
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app import create_app
from database import get_db,init_db

class ShopTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();d=self.tmp.name
        self.app=create_app({'TESTING':True,'SECRET_KEY':'test','DATABASE':d+'/db','UPLOAD_FOLDER':d+'/uploads','LAB_FILES':d+'/files','LAB_MODE':False})
        self.c=self.app.test_client()
    def tearDown(self): self.tmp.cleanup()
    def csrf(self):
        self.c.get('/')
        with self.c.session_transaction() as s: return s['csrf']
    def post(self,url,data=None,**kw):
        values={'csrf_token':self.csrf(),**(data or {})}
        return self.c.post(url,data=values,**kw)
    def login(self,name='student',password='Student123!'):
        return self.post('/login',{'username':name,'password':password})
    def scalar(self,sql,args=()):
        with self.app.app_context(): return get_db().execute(sql,args).fetchone()[0]
    def lab(self,*ids): self.app.config.update(LAB_MODE=True,VULNS=','.join(ids))
    def order(self,pid=2,qty=1):
        self.assertEqual(self.post(f'/cart/add/{pid}',{'quantity':qty}).status_code,302)
        aid=self.scalar('SELECT id FROM addresses WHERE user_id=2')
        r=self.post('/checkout',{'address_id':aid});self.assertEqual(r.status_code,302)
        return int(r.location.rsplit('/',1)[-1])
    def test_public_pages_and_assets(self):
        for url in ['/','/products','/products/1','/board','/board/1','/login','/register','/static/css/style.css','/static/js/main.js','/static/img/product01.png']:
            with self.subTest(url=url):
                response=self.c.get(url);self.assertEqual(response.status_code,200);response.close()
        self.assertIn('129,000원',self.c.get('/products/2').text)
    def test_register_login_logout_password(self):
        self.assertEqual(self.post('/register',{'username':'new_user','password':'Class123!','name':'가상 학생'}).status_code,302)
        self.assertEqual(self.scalar("SELECT balance FROM wallets WHERE user_id=(SELECT id FROM users WHERE username='new_user')"),3000000)
        self.post('/account/password',{'current_password':'Class123!','new_password':'Changed123!'})
        self.post('/logout')
        self.login('new_user','Changed123!')
        self.assertEqual(self.c.get('/account').status_code,200)
    def test_duplicate_and_invalid_registration(self):
        self.assertEqual(self.post('/register',{'username':'student','password':'12345678','name':'dup'}).status_code,409)
        self.assertEqual(self.post('/register',{'username':'x','password':'x','name':'x'}).status_code,400)
    def test_profile_address_and_topup(self):
        self.login();self.post('/account',{'name':'변경 이름','email':'dummy@example.test','phone':'010-0000-0000'})
        self.assertEqual(self.scalar('SELECT name FROM users WHERE id=2'),'변경 이름')
        self.post('/account/addresses',{'recipient':'가상','phone':'010-0000-0000','postcode':'12345','address':'가상로'})
        aid=self.scalar('SELECT max(id) FROM addresses WHERE user_id=2')
        self.post('/account/addresses',{'id':aid,'delete':'1'})
        self.post('/account/topup',{'amount':'1000'})
        self.assertEqual(self.scalar('SELECT balance FROM wallets WHERE user_id=2'),3001000)
    def test_cart_update_delete(self):
        self.login();self.post('/cart/add/2',{'quantity':2})
        iid=self.scalar('SELECT id FROM cart_items')
        self.post(f'/cart/{iid}',{'quantity':3})
        self.assertEqual(self.scalar('SELECT quantity FROM cart_items'),3)
        self.post(f'/cart/{iid}',{'quantity':0});self.assertEqual(self.scalar('SELECT count(*) FROM cart_items'),0)
    def test_filters_and_review(self):
        r=self.c.get('/products?category=3&min_price=100000&max_price=150000&sort=price_asc')
        self.assertIn('에어 사운드',r.text);self.assertNotIn('스튜디오 헤드폰</a>',r.text)
        self.login();self.post('/products/2/reviews',{'rating':5,'body':'가상 리뷰 <script>x</script>'})
        self.assertIn('&lt;script&gt;',self.c.get('/products/2').text)
    def test_wallet_payment_refund_and_duplicates(self):
        self.login();stock=self.scalar('SELECT stock FROM products WHERE id=2');oid=self.order(qty=2)
        self.assertEqual(self.scalar('SELECT stock FROM products WHERE id=2'),stock-2)
        data={'method':'wallet','amount':258000}
        self.post(f'/payments/{oid}',data);self.post(f'/payments/{oid}',data)
        self.assertEqual(self.scalar('SELECT balance FROM wallets WHERE user_id=2'),2742000)
        self.assertEqual(self.scalar('SELECT count(*) FROM payments WHERE order_id=?',(oid,)),1)
        self.post(f'/orders/{oid}/cancel');r=self.post(f'/orders/{oid}/cancel')
        self.assertEqual(r.status_code,409)
        self.assertEqual(self.scalar('SELECT balance FROM wallets WHERE user_id=2'),3000000)
        self.assertEqual(self.scalar('SELECT stock FROM products WHERE id=2'),stock)
        self.assertEqual(self.scalar('SELECT status FROM orders WHERE id=?',(oid,)),'REFUNDED')
    def test_simultaneous_payment(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        self.login();oid=self.order();barrier=Barrier(2)
        def submit():
            client=self.app.test_client()
            with client.session_transaction() as session:
                session['user_id']=2;session['csrf']='parallel-test'
            barrier.wait()
            return client.post(f'/payments/{oid}',data={'csrf_token':'parallel-test','method':'wallet','amount':'129000'}).status_code
        with ThreadPoolExecutor(max_workers=2) as executor:
            results=list(executor.map(lambda _:submit(),range(2)))
        self.assertEqual(results,[302,302])
        self.assertEqual(self.scalar('SELECT count(*) FROM payments WHERE order_id=?',(oid,)),1)
        self.assertEqual(self.scalar('SELECT balance FROM wallets WHERE user_id=2'),2871000)
    def test_admin_cancel_order(self):
        self.login('admin','Admin123!')
        self.assertEqual(self.post('/admin/orders/1/cancel').status_code,302)
        self.assertEqual(self.scalar('SELECT status FROM orders WHERE id=1'),'CANCELLED')
    def test_card_approval_decline_refund(self):
        self.login();oid=self.order()
        self.post(f'/payments/{oid}',{'method':'card','amount':129000,'card_number':'TEST-0002-4242','expiry':'12/30','pin':'wrong'})
        self.assertEqual(self.scalar('SELECT status FROM orders WHERE id=?',(oid,)),'FAILED')
        self.post(f'/payments/{oid}',{'method':'card','amount':129000,'card_number':'TEST-0002-4242','expiry':'12/30','pin':'1234'})
        self.assertEqual(self.scalar('SELECT balance FROM virtual_cards WHERE user_id=2'),4871000)
        self.post(f'/orders/{oid}/cancel')
        self.assertEqual(self.scalar('SELECT balance FROM virtual_cards WHERE user_id=2'),5000000)
    def test_insufficient_balance_and_cancel_failed(self):
        self.login();oid=self.order()
        with self.app.app_context():
            db=get_db();db.execute('UPDATE wallets SET balance=1 WHERE user_id=2');db.commit()
        self.post(f'/payments/{oid}',{'method':'wallet','amount':129000})
        self.assertEqual(self.scalar('SELECT status FROM orders WHERE id=?',(oid,)),'FAILED')
        self.assertEqual(self.scalar('SELECT status FROM payments WHERE order_id=?',(oid,)),'DECLINED')
        self.post(f'/orders/{oid}/cancel')
        self.assertEqual(self.scalar('SELECT status FROM orders WHERE id=?',(oid,)),'CANCELLED')
    def test_price_manipulation_pair(self):
        self.login();oid=self.order()
        self.post(f'/payments/{oid}',{'method':'wallet','amount':1})
        self.assertEqual(self.scalar('SELECT status FROM orders WHERE id=?',(oid,)),'FAILED')
        self.lab('VULN-11');self.post(f'/payments/{oid}',{'method':'wallet','amount':1})
        self.assertEqual(self.scalar('SELECT status FROM orders WHERE id=?',(oid,)),'PAID')
        self.assertEqual(self.scalar('SELECT balance FROM wallets WHERE user_id=2'),2999999)
        self.post(f'/orders/{oid}/cancel')
        self.assertEqual(self.scalar('SELECT balance FROM wallets WHERE user_id=2'),3000000)
    def test_student_payment_views(self):
        self.login()
        for url in ['/payments/1','/payments/1/complete']:
            self.assertEqual(self.c.get(url).status_code,200)
    def test_stock_and_negative_input(self):
        self.login();self.assertEqual(self.post('/cart/add/2',{'quantity':99}).status_code,409)
        self.assertEqual(self.post('/cart/add/2',{'quantity':-1}).status_code,400)
        self.assertEqual(self.post('/payments/1',{'amount':-1,'method':'wallet'}).status_code,400)
    def test_idor_pair(self):
        self.login();self.assertEqual(self.c.get('/orders/2').status_code,403)
        self.assertEqual(self.c.get('/account?user_id=3').status_code,403)
        self.lab('VULN-05');self.assertEqual(self.c.get('/orders/2').status_code,200)
        self.assertIn('가상 앨리스',self.c.get('/account?user_id=3').text)
        self.assertEqual(self.post('/orders/2/cancel').status_code,404)
    def test_admin_access_pair_and_crud(self):
        self.login();self.assertEqual(self.c.get('/admin').status_code,403)
        self.lab('VULN-06');self.assertEqual(self.c.get('/admin').status_code,200)
        self.post('/admin/products/new',{'name':'테스트 상품','description':'설명','price':10000,'stock':5,'category_id':1,'image':'product01.png'})
        pid=self.scalar('SELECT max(id) FROM products');self.assertEqual(pid,10)
        self.post(f'/admin/products/{pid}',{'delete':1})
        self.assertEqual(self.scalar('SELECT active FROM products WHERE id=?',(pid,)),0)
        self.app.config['LAB_MODE']=False;self.post('/logout');self.login('admin','Admin123!')
        self.assertEqual(self.c.get('/admin').status_code,200)
    def test_sqli_login_pair(self):
        self.login("' OR 1=1 -- ",'bad');self.assertEqual(self.c.get('/account').status_code,302)
        self.lab('VULN-01');self.login("' OR 1=1 -- ",'bad')
        with self.c.session_transaction() as s: self.assertEqual(s['user_id'],1)
    def test_sqli_search_pair(self):
        payload="absent%') OR 1=1 -- "
        self.assertNotIn('product-name',self.c.get('/products',query_string={'q':payload}).text)
        self.lab('VULN-01');self.assertIn('product-name',self.c.get('/products',query_string={'q':payload}).text)
    def test_reflected_xss_pair(self):
        q='<img src=x onerror=alert(1)>'
        self.assertIn('&lt;img',self.c.get('/products',query_string={'q':q}).text)
        self.lab('VULN-02');self.assertIn(q,self.c.get('/products',query_string={'q':q}).text)
    def test_board_crud_stored_xss_and_comment(self):
        self.login();payload='<script>alert(3)</script>'
        r=self.post('/board/new',{'title':'테스트','body':payload});url=r.location
        self.assertIn('&lt;script&gt;',self.c.get(url).text)
        self.lab('VULN-03');self.assertIn(payload,self.c.get(url).text)
        self.post(url+'/comments',{'body':payload});self.assertEqual(self.c.get(url).text.count(payload),2)
        self.post(url+'/edit',{'title':'수정','body':'바뀐 내용'});self.assertIn('바뀐 내용',self.c.get(url).text)
        self.post(url+'/delete');self.assertEqual(self.c.get(url).status_code,404)
    def test_upload_pair_download_and_worker_gate(self):
        self.login()
        self.assertEqual(self.post('/board/new',{'title':'x','body':'y','attachment':(io.BytesIO(b'print(42)'),'demo.py')}).status_code,400)
        self.lab('VULN-04')
        self.post('/board/new',{'title':'x','body':'y','attachment':(io.BytesIO(b'print(42)'),'demo.py')})
        aid=self.scalar('SELECT id FROM attachments')
        r=self.c.get(f'/attachments/{aid}');self.assertEqual(r.data,b'print(42)');self.assertIn('attachment',r.headers['Content-Disposition']);r.close()
        self.assertEqual(self.c.get(f'/attachments/{aid}/preview').status_code,503)
        with patch('routes.board.worker',return_value='42') as mock:
            self.assertIn('42',self.c.get(f'/attachments/{aid}/preview').text);mock.assert_called_once()
    def test_traversal_outer_jail(self):
        self.login();self.assertEqual(self.c.get('/download?file=../dummy-secret.txt').status_code,403)
        self.lab('VULN-09');r=self.c.get('/download?file=../dummy-secret.txt');self.assertIn(b'VOLTIX-LAB-DUMMY-SECRET',r.data);r.close()
        self.assertEqual(self.c.get('/download?file=../../../../etc/passwd').status_code,403)
        self.assertEqual(self.c.get('/download?file=/etc/passwd').status_code,403)
    def test_csrf_pair(self):
        self.login();self.assertEqual(self.c.post('/account',data={'name':'csrf'}).status_code,400)
        self.assertEqual(self.c.post('/account',data={'csrf_token':'한글','name':'csrf'}).status_code,400)
        self.lab('VULN-07');self.assertEqual(self.c.post('/account',data={'name':'csrf'}).status_code,302)
        self.assertEqual(self.scalar('SELECT name FROM users WHERE id=2'),'csrf')
        self.assertEqual(self.c.post('/account/topup',data={'amount':1000}).status_code,400)
    def test_ssti_pair_and_gate(self):
        self.login();self.assertIn('{{7*7}}',self.post('/account/message',{'message':'{{7*7}}'}).text)
        self.lab('VULN-08');self.assertEqual(self.post('/account/message',{'message':'{{7*7}}'}).status_code,503)
        with patch('routes.admin.worker',return_value='49') as mock:
            self.assertIn('49',self.post('/account/message',{'message':'{{7*7}}'}).text);mock.assert_called_once_with('template',template='{{7*7}}')
    def test_command_pair_and_gate(self):
        self.login('admin','Admin123!')
        self.assertEqual(self.post('/admin/diagnostics',{'target':'demo;id'}).status_code,400)
        self.lab('VULN-10');self.assertEqual(self.post('/admin/diagnostics',{'target':'demo;id'}).status_code,503)
        with patch('routes.admin.worker',return_value='uid=10002'):
            self.assertIn('uid=10002',self.post('/admin/diagnostics',{'target':'demo;id'}).text)
    def test_init_idempotent_and_reset(self):
        with self.app.app_context(): init_db();init_db()
        self.assertEqual(self.scalar('SELECT count(*) FROM products'),9)
        r=self.app.test_cli_runner().invoke(args=['reset-db','--yes']);self.assertEqual(r.exit_code,0,r.output)
        self.assertEqual(self.scalar('SELECT count(*) FROM users'),3)
    def test_authenticated_views(self):
        self.login('admin','Admin123!')
        for url in ['/account','/account/message','/cart','/checkout','/orders','/orders/1','/board/new','/board/1/edit','/admin','/admin/products/new','/admin/products/1','/admin/diagnostics']:
            with self.subTest(url=url): self.assertEqual(self.c.get(url).status_code,200)

if __name__=='__main__': unittest.main()
