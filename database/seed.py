from werkzeug.security import generate_password_hash

PRODUCTS = [
 (1,'VOLTIX 울트라북 14',1290000,'product01.png','가벼운 일상, 강력한 성능. 14인치 디스플레이와 16GB 메모리.'),
 (3,'VOLTIX 에어 사운드',129000,'product02.png','하루 종일 편안한 무선 헤드폰. 풍부한 저음과 긴 배터리.'),
 (1,'VOLTIX 프로북 16',1890000,'product03.png','창작과 개발을 위한 넓은 화면과 고성능 프로세서.'),
 (2,'VOLTIX 탭 11',499000,'product04.png','필기부터 영상까지, 선명한 11인치 태블릿.'),
 (3,'VOLTIX 스튜디오 헤드폰',249000,'product05.png','음악의 디테일을 살리는 오버이어 헤드폰.'),
 (1,'VOLTIX 슬림북 13',990000,'product06.png','휴대성을 높인 슬림한 노트북.'),
 (2,'VOLTIX 폰 X',799000,'product07.png','선명한 화면과 넉넉한 저장 공간을 갖춘 스마트폰.'),
 (1,'VOLTIX 데일리북',699000,'product08.png','학습과 업무를 위한 실용적인 노트북.'),
 (4,'VOLTIX 미러리스 C1',1090000,'product09.png','일상의 순간을 담는 가벼운 미러리스 카메라.')]

def create_user(db, username, password, name, role='user'):
    uid = db.execute('INSERT INTO users(username,password,name,email,phone,role) VALUES(?,?,?,?,?,?)', (username,generate_password_hash(password),name,username+'@example.test','010-0000-0000',role)).lastrowid
    db.execute('INSERT INTO carts(user_id) VALUES(?)',(uid,))
    db.execute('INSERT INTO wallets VALUES(?,?)',(uid,3000000))
    db.execute('INSERT INTO wallet_transactions(user_id,amount,kind) VALUES(?,?,?)',(uid,3000000,'WELCOME'))
    # TEST prefix deliberately prevents this identifier from being a real card number.
    db.execute('INSERT INTO virtual_cards(user_id,number,expiry,pin,balance) VALUES(?,?,?,?,?)',(uid,f'TEST-{uid:04d}-4242','12/30',generate_password_hash('1234'),5000000))
    db.execute('INSERT INTO addresses(user_id,recipient,phone,postcode,address) VALUES(?,?,?,?,?)',(uid,name,'010-0000-0000','00000','가상시 디지털로 101 실습동'))
    return uid

def seed(db):
    if db.execute('SELECT count(*) FROM users').fetchone()[0]:
        return
    for name in ['노트북','스마트 기기','오디오','카메라']:
        db.execute('INSERT INTO categories(name) VALUES(?)',(name,))
    for cat,name,price,image,desc in PRODUCTS:
        pid=db.execute('INSERT INTO products(category_id,name,description,price,stock,image) VALUES(?,?,?,?,?,?)',(cat,name,desc,price,30,image)).lastrowid
        db.execute('INSERT INTO product_images(product_id,image) VALUES(?,?)',(pid,image))
    create_user(db,'admin','Admin123!','가상 관리자','admin')
    for username,name in [('student','실습 학생'),('alice','가상 앨리스')]:
        uid=create_user(db,username,'Student123!',name)
        oid=db.execute("INSERT INTO orders(user_id,status,total,recipient,phone,postcode,address) VALUES(?,'PENDING',129000,?,'010-0000-0000','00000','가상시 디지털로 101')",(uid,name)).lastrowid
        db.execute('INSERT INTO order_items(order_id,product_id,name,price,quantity) VALUES(?,2,?,129000,1)',(oid,'VOLTIX 에어 사운드'))
        db.execute('UPDATE products SET stock=stock-1 WHERE id=2')
    db.execute('INSERT INTO posts(user_id,title,body) VALUES(1,?,?)',('VOLTIX에 오신 것을 환영합니다','배송, 상품 문의를 남겨 주세요. 모든 정보와 결제는 교육용 가상 데이터입니다.'))
    db.execute('INSERT INTO coupons(code,discount) VALUES(?,?)',('WELCOME',10000))
    db.commit()
