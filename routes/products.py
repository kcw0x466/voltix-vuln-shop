import sqlite3
from flask import Blueprint,render_template,request,g,redirect,url_for,abort
from database import get_db
from routes.common import one,number,login_required
from vulnerabilities import enabled
bp=Blueprint('products',__name__)

@bp.get('/')
def home():
    return render_template('products/home.html',products=get_db().execute('SELECT p.*,c.name category FROM products p JOIN categories c ON c.id=p.category_id WHERE active=1 ORDER BY p.id LIMIT 9').fetchall())

@bp.get('/products')
def listing():
    db=get_db();q=request.args.get('q','')[:200];args=[]
    sql='SELECT p.*,c.name category FROM products p JOIN categories c ON c.id=p.category_id WHERE p.active=1'
    if q:
        if enabled('VULN-01'): sql+=" AND (p.name LIKE '%"+q+"%' OR p.description LIKE '%"+q+"%')" # VULN-01
        else: sql+=' AND (p.name LIKE ? OR p.description LIKE ?)';args.extend(['%'+q+'%']*2)
    cat=request.args.get('category')
    if cat: sql+=' AND p.category_id=?';args.append(number(cat,1))
    for key,op in [('min_price','>='),('max_price','<=')]:
        if request.args.get(key): sql+=' AND p.price'+op+'?';args.append(number(request.args[key]))
    sort={'newest':'p.id DESC','price_asc':'p.price ASC','price_desc':'p.price DESC','name':'p.name ASC'}.get(request.args.get('sort'),'p.id DESC')
    sql+=' ORDER BY '+sort
    try: rows=db.execute(sql,args).fetchall()
    except sqlite3.Error: rows=[]
    return render_template('products/list.html',products=rows,q=q)

@bp.get('/products/<int:pid>')
def detail(pid):
    product=one('SELECT p.*,c.name category FROM products p JOIN categories c ON c.id=p.category_id WHERE p.id=? AND active=1',(pid,))
    db=get_db()
    return render_template('products/detail.html',p=product,images=db.execute('SELECT * FROM product_images WHERE product_id=?',(pid,)).fetchall(),reviews=db.execute('SELECT r.*,u.name FROM reviews r JOIN users u ON u.id=r.user_id WHERE product_id=? ORDER BY r.id DESC',(pid,)).fetchall())

@bp.post('/products/<int:pid>/reviews')
@login_required
def review(pid):
    one('SELECT id FROM products WHERE id=?',(pid,));rating=number(request.form.get('rating'),1,5);body=request.form.get('body','').strip()
    if not body: abort(400,'리뷰 내용을 입력하세요.')
    db=get_db()
    with db: db.execute('INSERT INTO reviews(product_id,user_id,rating,body) VALUES(?,?,?,?)',(pid,g.user['id'],rating,body[:3000]))
    return redirect(url_for('products.detail',pid=pid))
