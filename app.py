import logging
import secrets
from pathlib import Path
import click
from flask import Flask, g, session, request, abort, render_template, redirect, url_for
from database import get_db, close_db, init_db
from config import Config
from vulnerabilities import enabled, IDS

def create_app(test_config=None):
    app=Flask(__name__)
    app.config.from_object(Config)
    if test_config: app.config.update(test_config)
    for key in ('UPLOAD_FOLDER','LAB_FILES'):
        Path(app.config[key]).mkdir(parents=True, exist_ok=True)
    lab=Path(app.config['LAB_FILES'])
    (lab/'attachments').mkdir(exist_ok=True)
    (lab/'dummy-secret.txt').write_text('VOLTIX-LAB-DUMMY-SECRET: classroom-only\n')
    (lab/'attachments'/'guide.txt').write_text('VOLTIX 가상 첨부파일\n')
    app.teardown_appcontext(close_db)
    with app.app_context(): init_db()
    from routes import auth, products, cart, orders, payments, board, admin
    for module in (auth,products,cart,orders,payments,board,admin): app.register_blueprint(module.bp)

    @app.before_request
    def load_user_and_csrf():
        g.user=get_db().execute('SELECT * FROM users WHERE id=?',(session.get('user_id'),)).fetchone()
        session.setdefault('csrf',secrets.token_hex(24))
        # VULN-07: only profile/address changes omit validation in this lesson.
        skip=enabled('VULN-07') and request.endpoint in {'auth.profile','auth.address'}
        if request.method in {'POST','PUT','DELETE','PATCH'} and not skip:
            if not secrets.compare_digest(session['csrf'].encode(),request.form.get('csrf_token','').encode()):
                abort(400,'요청 인증 토큰이 올바르지 않습니다. 페이지를 새로고침해 주세요.')

    @app.context_processor
    def context():
        count=0
        if g.user:
            count=get_db().execute('SELECT coalesce(sum(quantity),0) FROM cart_items JOIN carts ON carts.id=cart_items.cart_id WHERE user_id=?',(g.user['id'],)).fetchone()[0]
        return dict(categories=get_db().execute('SELECT * FROM categories').fetchall(),cart_count=count,vuln=enabled,csrf_token=lambda:session['csrf'])

    app.jinja_env.filters['krw']=lambda value:f'{int(value):,}원'
    @app.errorhandler(400)
    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(409)
    @app.errorhandler(413)
    @app.errorhandler(503)
    def error(e): return render_template('error.html',error=e),e.code

    # Existing template page names remain navigable.
    for old,endpoint in [('index.html','products.home'),('store.html','products.listing'),('checkout.html','orders.checkout'),('blank.html','board.index')]:
        app.add_url_rule('/'+old,old,lambda ep=endpoint:redirect(url_for(ep)))
    @app.get('/product.html')
    def old_product(): return redirect(url_for('products.detail',pid=1))

    @app.cli.command('init-db')
    def init_command():
        """Create missing schema; seed only an empty database."""
        init_db(); click.echo('DB 준비 완료 (기존 데이터 보존)')
    @app.cli.command('reset-db')
    @click.option('--yes',is_flag=True,help='Confirm destruction of all classroom data')
    def reset_command(yes):
        if not yes: raise click.ClickException('데이터 삭제 확인: --yes 를 지정하세요.')
        db=get_db()
        names=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        db.execute('PRAGMA foreign_keys=OFF')
        for name in names: db.execute('DROP TABLE "'+name+'"')
        db.commit(); db.execute('PRAGMA foreign_keys=ON');init_db()
        for file in Path(app.config['UPLOAD_FOLDER']).iterdir():
            if file.is_file(): file.unlink()
        click.echo('가상 데이터 초기화 완료')
    return app

if __name__=='__main__':
    import os
    logging.basicConfig(level=logging.INFO)
    create_app().run(host=os.getenv('VOLTIX_HOST','127.0.0.1'),port=int(os.getenv('VOLTIX_PORT','5000')),debug=False)
