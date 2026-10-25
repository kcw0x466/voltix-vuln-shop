import base64
import uuid
from pathlib import Path
from flask import Blueprint,request,render_template,redirect,url_for,g,abort,current_app,send_file
from werkzeug.utils import secure_filename
from database import get_db
from routes.common import login_required,one,owns
from vulnerabilities import enabled,worker
bp=Blueprint('board',__name__)

@bp.get('/board')
def index():
    rows=get_db().execute('SELECT p.*,u.name FROM posts p JOIN users u ON u.id=p.user_id ORDER BY p.id DESC').fetchall()
    return render_template('board/index.html',posts=rows)

@bp.route('/board/new',methods=['GET','POST'])
@login_required
def create():
    if request.method=='POST':
        title=request.form.get('title','').strip();body=request.form.get('body','').strip()
        if not title or not body: abort(400,'제목과 내용을 입력하세요.')
        file=request.files.get('attachment');stored=None;original=None
        if file and file.filename:
            original=file.filename[:200]
            # VULN-04: active HTML and Python files are accepted only in this lesson.
            if not enabled('VULN-04') and Path(original).suffix.lower() not in {'.txt','.png','.jpg','.jpeg','.pdf'}:
                abort(400,'허용된 첨부파일: txt, png, jpg, pdf')
            stored=uuid.uuid4().hex+'_'+(secure_filename(original) or 'attachment')
            file.save(Path(current_app.config['UPLOAD_FOLDER'])/stored)
        db=get_db()
        with db:
            pid=db.execute('INSERT INTO posts(user_id,title,body) VALUES(?,?,?)',(g.user['id'],title[:200],body[:20000])).lastrowid
            if stored: db.execute('INSERT INTO attachments(post_id,original_name,stored_name) VALUES(?,?,?)',(pid,original,stored))
        return redirect(url_for('board.detail',pid=pid))
    return render_template('board/form.html',post=None)

@bp.get('/board/<int:pid>')
def detail(pid):
    p=one('SELECT p.*,u.name FROM posts p JOIN users u ON u.id=p.user_id WHERE p.id=?',(pid,))
    db=get_db()
    return render_template('board/detail.html',post=p,comments=db.execute('SELECT c.*,u.name FROM comments c JOIN users u ON u.id=c.user_id WHERE post_id=? ORDER BY c.id',(pid,)).fetchall(),attachments=db.execute('SELECT * FROM attachments WHERE post_id=?',(pid,)).fetchall())

@bp.route('/board/<int:pid>/edit',methods=['GET','POST'])
@login_required
def edit(pid):
    post=one('SELECT * FROM posts WHERE id=?',(pid,));owns(post)
    if request.method=='POST':
        title=request.form.get('title','').strip();body=request.form.get('body','').strip()
        if not title or not body: abort(400)
        db=get_db()
        with db: db.execute('UPDATE posts SET title=?,body=? WHERE id=?',(title[:200],body[:20000],pid))
        return redirect(url_for('board.detail',pid=pid))
    return render_template('board/form.html',post=post)

@bp.post('/board/<int:pid>/delete')
@login_required
def delete(pid):
    post=one('SELECT * FROM posts WHERE id=?',(pid,));owns(post)
    db=get_db()
    files=db.execute('SELECT stored_name FROM attachments WHERE post_id=?',(pid,)).fetchall()
    with db: db.execute('DELETE FROM posts WHERE id=?',(pid,))
    for file in files: (Path(current_app.config['UPLOAD_FOLDER'])/file['stored_name']).unlink(missing_ok=True)
    return redirect(url_for('board.index'))

@bp.post('/board/<int:pid>/comments')
@login_required
def comment(pid):
    one('SELECT id FROM posts WHERE id=?',(pid,));body=request.form.get('body','').strip()
    if not body: abort(400)
    db=get_db()
    with db: db.execute('INSERT INTO comments(post_id,user_id,body) VALUES(?,?,?)',(pid,g.user['id'],body[:5000]))
    return redirect(url_for('board.detail',pid=pid))

@bp.get('/attachments/<int:aid>')
def download(aid):
    item=one('SELECT * FROM attachments WHERE id=?',(aid,));path=Path(current_app.config['UPLOAD_FOLDER'])/item['stored_name']
    if not path.is_file(): abort(404)
    return send_file(path,as_attachment=True,download_name=item['original_name'])

@bp.get('/attachments/<int:aid>/preview')
@login_required
def preview(aid):
    if not enabled('VULN-04'): abort(403)
    item=one('SELECT * FROM attachments WHERE id=?',(aid,));path=Path(current_app.config['UPLOAD_FOLDER'])/item['stored_name']
    if not path.is_file(): abort(404)
    if Path(item['original_name']).suffix.lower()=='.py':
        # Never import, exec or spawn the uploaded source on the application host.
        output=worker('upload',source=base64.b64encode(path.read_bytes()).decode())
        return render_template('admin/result.html',title='첨부파일 실행 결과',output=output)
    return send_file(path,as_attachment=False,download_name=item['original_name'])

@bp.get('/download')
@login_required
def traversal():
    # VULN-09: attachment boundary is missing; outer fixture jail is always enforced.
    root=Path(current_app.config['LAB_FILES']).resolve();base=root/'attachments'
    target=(base/request.args.get('file','guide.txt')).resolve()
    boundary=root if enabled('VULN-09') else base
    if not target.is_relative_to(boundary): abort(403,'실습 파일 경계 밖에는 접근할 수 없습니다.')
    if not target.is_file(): abort(404)
    return send_file(target,as_attachment=True)
