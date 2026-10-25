# VOLTIX 교육용 취약점 실습 안내

모든 데이터는 가상입니다. 인터넷 공개 금지, 학생별 일회용 VM/Compose 프로젝트에서 실습합니다. 기본 `VOLTIX_LAB_MODE=0`에서는 아래 실습이 꺼집니다. 각 시나리오는 `VOLTIX_LAB_MODE=1`, `VOLTIX_VULNS=해당-ID`를 설정하고 재시작한 뒤 수행하세요. 정상 모드 비교는 해당 ID를 목록에서 제거합니다. 조합 실습은 쉼표 구분 또는 `all`입니다.

일반 POST 요청에는 페이지에서 발급받은 `csrf_token`과 로그인 쿠키가 필요합니다(VULN-07의 지정 경로만 예외). Burp Suite Proxy에서 브라우저 요청을 캡처하고 Repeater로 보내 값만 변경하면 토큰과 세션을 유지할 수 있습니다. 토큰은 로그인 후 새로 발급됩니다. 상태 변경/실패 시 결과는 302 이후 주문 상세와 DB 기록에서 확인합니다. CSRF를 제외한 시나리오에서 토큰을 제거하면 실습 전 단계에서 400으로 거절됩니다.

OWASP 분류는 수업 기준을 고정하기 위해 **Top 10:2021**을 사용하며 최신판이라는 의미가 아닙니다. 아래 매핑은 본 프로젝트 시나리오에 대한 분류입니다. SQL·XSS·명령 주입은 [OWASP A03:2021 Injection](https://top10.owasp.org/2021/A03_2021-Injection/), 권한·CSRF는 [A01:2021 Broken Access Control](https://top10.owasp.org/2021/A01_2021-Broken_Access_Control/), 금액 신뢰 설계는 [A04:2021 Insecure Design](https://top10.owasp.org/2021/A04_2021-Insecure_Design/)과 비교합니다.

## VULN-01 — SQL Injection

- 코드: `routes/auth.py::login`, `routes/products.py::listing`.
- URL/메서드: `POST /login`, `GET /products?q=...`.
- 원인: 사용자명을 SQL 문자열에 직접 연결하고 검색어를 LIKE 조건 문자열에 연결. 취약 로그인도 정상 비밀번호 해시 검증용 SQLite 함수를 사용하지만 사용자명 부분의 주석으로 검증 조건을 제거할 수 있음.
- 사전 조건: 비로그인, VULN-01 활성화. 초기 가상 회원 데이터.
- 검증: 로그인 화면에서 정상 요청을 캡처한 뒤 `username=' OR 1=1 -- `, `password=anything`으로 변경. 검색은 `q=absent%') OR 1=1 -- `을 URL 인코딩하여 요청.
- 예상 결과: 틀린 비밀번호로 첫 회원(admin) 세션 생성. 검색은 일치하지 않는 단어인데 상품이 반환됨. 정상 모드는 로그인 거절/검색 0건.
- 영향: 가상 회원 인증 우회, SQLite 데이터 열람. sqlite3 단일 statement 제한이 SQLi 방어를 의미하지 않음.
- 안전한 수정: `WHERE username=?`, `LIKE ?` 바인딩, 조회 후 비밀번호 해시 검증. 검색 정렬은 허용 목록으로 고정(양 모드 공통).
- 분류: CWE-89, OWASP A03:2021.

## VULN-02 — Reflected XSS

- 코드: `templates/products/list.html`의 `search-query` 영역, `routes/products.py::listing`.
- URL/메서드: `GET /products?q=...`.
- 원인: 검색 결과 안내에 사용자 입력을 `|safe`로 출력.
- 사전 조건: VULN-02 활성화. 로그인 불필요.
- 검증: 검색어 `<img src=x onerror=alert('VOLTIX-02')>`를 입력하고 결과 페이지 조회. HTTP 원문과 브라우저 DOM을 비교.
- 예상 결과: 응답에 태그가 그대로 포함되고 브라우저 경고 표시. 정상 모드는 `&lt;img...`로 인코딩되어 텍스트 표시.
- 영향: 방문자의 가상 세션으로 요청 실행, 페이지 변조. HttpOnly는 스크립트의 세션 쿠키 직접 읽기를 막지만 인증 요청 실행은 막지 않음.
- 안전한 수정: Jinja2 자동 이스케이프 유지, `safe` 제거, 문맥별 인코딩.
- 분류: CWE-79, OWASP A03:2021.

## VULN-03 — Stored XSS

- 코드: `routes/board.py::create/edit/comment`, `templates/board/detail.html`.
- URL/메서드: `POST /board/new`, `POST /board/<id>/edit`, `POST /board/<id>/comments`; 실행은 `GET /board/<id>`.
- 원인: 저장된 글/댓글을 신뢰하여 `|safe`로 렌더링. 제목과 상품 리뷰는 자동 이스케이프 유지.
- 사전 조건: 로그인 후 VULN-03 활성화.
- 검증: 글 본문 또는 댓글에 `<script>alert('VOLTIX-03')</script>` 저장. 별도 브라우저 프로필로 해당 글 조회.
- 예상 결과: 다른 방문자의 페이지에서도 경고 실행. 정상 모드에서는 저장값이 같아도 태그 문자열로 표시.
- 영향: 게시글 방문자를 대상으로 지속적 스크립트 실행, 가상 관리자 세션 동작 악용.
- 안전한 수정: 자동 이스케이프. 서식 허용이 필요하면 서버에서 검증된 HTML sanitizer/허용 목록 사용.
- 분류: CWE-79, OWASP A03:2021.

## VULN-04 — Unrestricted File Upload / 격리된 서버 코드 실행

- 코드: `routes/board.py::create/preview`, `lab/child.py`의 upload 분기.
- URL/메서드: `POST /board/new` multipart의 `attachment`, `GET /attachments/<id>`, `GET /attachments/<id>/preview`.
- 원인: 활성화 시 업로드 확장자 검증 누락. preview가 업로드 Python 소스를 실행 대상으로 전달. 임의 파일명 자체는 UUID+secure_filename으로 저장되어 호스트 경로 덮어쓰기는 실습 범위 밖.
- 사전 조건: 로그인, VULN-04 활성화. 코드 실행은 Compose worker + 일회용 VM 필수.
- 검증: 내용이 `print('VOLTIX-UPLOAD-OK')`인 `demo.py`를 게시글에 첨부. 첨부 ID 확인 후 미리보기 클릭. 별도로 `<h1>첨부 미리보기</h1>`을 담은 html 파일 업로드/미리보기도 가능.
- 예상 결과: Python 출력이 미리보기 결과 화면에 표시. worker 미연결은 503. 정상 모드는 py/html 업로드 400, preview 403. 다운로드 자체는 attachment 헤더 사용.
- 영향: worker 컨테이너 내부 임의 Python 실행, HTML 미리보기에서 동일 origin 스크립트 실행 가능. 실제 호스트/다른 학생 파일은 worker에 마운트하지 않음.
- 안전한 수정: 실행 가능한 확장자와 능동 콘텐츠 거부, MIME/파일 signature 검사, 크기 제한, 별도 비실행 저장소/독립 다운로드 origin, 항상 다운로드로 제공. 현재 정상 비교 구현은 확장자 허용 목록+강제 다운로드이며 악성코드 검사기는 아님.
- 분류: CWE-434 (업로드), CWE-94 (코드 실행), OWASP A04:2021 (본 시나리오 설계 분류).

## VULN-05 — IDOR

- 코드: `routes/orders.py::detail`, `routes/auth.py::profile` GET.
- URL/메서드: `GET /orders/<id>`, `GET /account?user_id=<id>`.
- 원인: 로그인 여부만 확인하고 읽는 객체 소유자 검증 생략.
- 사전 조건: student 로그인, VULN-05 활성화. 초기 주문 #1 student, #2 alice; 회원 ID 2 student, 3 alice.
- 검증: `/orders/2`와 `/account?user_id=3` 요청.
- 예상 결과: 가상 앨리스의 주문·배송지·포인트/테스트 카드 정보를 볼 수 있음. 정상 모드는 403. 타인 주문 결제/취소와 주소 수정은 이 ID로 열리지 않음.
- 영향: 타인 가상 회원/주문 데이터 노출. 주소·카드 등은 모두 dummy.
- 안전한 수정: 현재 사용자 ID로 조회 범위를 한정, 필요 시 명시적 관리자 정책 적용. 난수 ID만으로 권한 검증을 대체하지 않음.
- 분류: CWE-639, OWASP A01:2021.

## VULN-06 — Broken Access Control

- 코드: `routes/common.py::admin_required`, `routes/admin.py`.
- URL/메서드: `GET /admin`, `GET/POST /admin/products/new`, `GET/POST /admin/products/<id>`, `POST /admin/users/<id>`, `POST /admin/orders/<id>/cancel`, `GET/POST /admin/diagnostics`.
- 원인: UI는 관리자 메뉴를 숨기지만 서버 장식자가 로그인만 검증하고 role 확인 생략.
- 사전 조건: 일반 student 로그인, VULN-06 활성화.
- 검증: 메뉴에 관리자가 없는 상태에서 주소창에 `/admin` 직접 입력. 상품 등록 폼 제출까지 비교.
- 예상 결과: 관리자 대시보드 및 관리 변경 가능. 정상 모드는 일반 회원 요청에 403. 비로그인은 양 모드 모두 로그인으로 이동.
- 영향: 가상 회원 권한/상품 변경, 주문 취소. 타인 소유 객체의 전용 안전 엔드포인트는 별도 권한 검증이 있으므로 모든 화면이 자동으로 열리는 것은 아님.
- 안전한 수정: 모든 관리 라우트에서 서버의 세션 사용자 role 확인. API/직접 URL에도 동일 정책 적용.
- 분류: CWE-862 / CWE-863, OWASP A01:2021.

## VULN-07 — CSRF

- 코드: `app.py::load_user_and_csrf`, `routes/auth.py::profile/address`.
- URL/메서드: `POST /account`, `POST /account/addresses`.
- 원인: 지정 회원정보/배송지 변경 경로의 CSRF 토큰 검증 누락. 다른 POST는 검증 유지.
- 사전 조건: student 로그인, VULN-07 활성화. SameSite=Lax 쿠키는 유지하므로 다른 사이트에서의 POST는 브라우저가 쿠키를 생략할 수 있음. 같은 사이트의 다른 origin(예: 127.0.0.1:8000)을 공격 페이지로 사용.
- 검증: 먼저 Burp Repeater에서 `/account` 정상 요청의 `csrf_token`을 제거하고 name을 `가상CSRF변경`으로 전송. 브라우저 재현은 아래 HTML을 별도 로컬 정적 서버에서 열고 버튼 클릭. 호스트명을 양쪽 모두 127.0.0.1로 통일.

```html
<form action="http://127.0.0.1:5000/account" method="post">
  <input name="name" value="가상CSRF변경">
  <input name="email" value="csrf@example.test">
  <input name="phone" value="010-0000-0000">
  <button>가상 이벤트 확인</button>
</form>
```

- 예상 결과: 토큰 없이 정보가 변경됨. 정상 모드는 400이며 기존 정보 유지.
- 영향: 로그인한 피해자의 가상 정보/배송지 변경.
- 안전한 수정: 모든 상태 변경에 서버 검증 CSRF 토큰, Origin 검사/적절한 SameSite를 보조 수단으로 적용.
- 분류: CWE-352, OWASP A01:2021.

## VULN-08 — Server-Side Template Injection

- 코드: `routes/admin.py::message`, `lab/child.py` template 분기.
- URL/메서드: `GET/POST /account/message` (`message` 필드).
- 원인: 메시지를 템플릿 데이터 대신 `render_template_string`의 코드로 해석.
- 사전 조건: 로그인, VULN-08 활성화, Compose worker, 일회용 VM.
- 검증: 메시지에 `{{7*7}}` 입력. 요청/응답과 결과 영역 확인.
- 예상 결과: `49` 출력. 정상 모드는 `{{7*7}}` 그대로 출력. worker 미연결은 503. 템플릿 출력은 쇼핑몰 응답에서 다시 escape하여 별도의 XSS 경로와 구분.
- 영향: Jinja2 표현식 평가, worker 컨테이너 내부 코드 실행으로 확대 가능. 파일/환경은 worker의 dummy 데이터만 접근 대상으로 구성.
- 안전한 수정: 고정 템플릿에 `message` 변수를 데이터로 전달. 사용자 템플릿 기능과 실행 worker 자체를 제거.
- 분류: CWE-1336, OWASP A03:2021 (본 시나리오 분류).

## VULN-09 — Path Traversal

- 코드: `routes/board.py::traversal`.
- URL/메서드: `GET /download?file=...`.
- 원인: 첨부 디렉터리 경계 검사를 생략. 교육용 바깥 jail 검사는 양 모드 모두 유지.
- 사전 조건: 로그인, VULN-09 활성화. 자동 생성 `instance/lab-files/attachments/guide.txt`와 상위 `dummy-secret.txt`.
- 검증: `/download?file=../dummy-secret.txt` 요청.
- 예상 결과: `VOLTIX-LAB-DUMMY-SECRET` 응답. 정상 모드 403. `../../../../etc/passwd`나 절대 `/etc/passwd`는 양 모드 403.
- 영향: 첨부 디렉터리 바깥 더미 파일 노출. 실제 OS 파일 접근은 의도적으로 차단하여 경계 검증을 비교.
- 안전한 수정: 파일 ID로 DB 레코드 조회 → 서버 저장 경로 사용. 경로 입력이 필요하면 resolve 후 올바른 base 포함 여부 검사(단순 문자열 prefix 금지).
- 분류: CWE-22, OWASP A01:2021.

## VULN-10 — OS Command Injection

- 코드: `routes/admin.py::diagnostics`, `lab/child.py` command 분기.
- URL/메서드: `GET/POST /admin/diagnostics` (`target` 필드).
- 원인: worker가 `echo `+사용자값을 shell=True로 실행. 메타문자에 따라 추가 명령 실행. 예제는 진단 서비스의 echo 기반 출력으로 구성.
- 사전 조건: admin 로그인(또는 별도의 VULN-06 실습), VULN-10 활성화, Compose worker, 일회용 VM.
- 검증: `target=voltix-demo; id` 제출. `voltix-demo | uname`도 비교.
- 예상 결과: 진단 텍스트 외에 worker uid 또는 커널 이름 출력. 정상 모드는 허용된 진단 대상만 처리하고 주입 문자열은 400. worker 미연결은 503.
- 영향: 격리된 worker 내 shell 명령 실행. 실습 parser는 echo/id/whoami/pwd/uname만 허용하고 경로·치환·리다이렉션은 거부. Python/SSTI의 실행 능력과 이 제한된 명령 수업은 별개.
- 안전한 수정: 가상 진단처럼 셸 제거, 대상 allowlist. 외부 실행이 필요하면 고정 실행 파일+인자 배열, shell=False.
- 분류: CWE-78, OWASP A03:2021.

## VULN-11 — Price Manipulation

- 코드: `templates/payment/checkout.html` hidden amount, `routes/payments.py::checkout`, `services/payment_service.py::pay`.
- URL/메서드: `GET/POST /payments/<order-id>`.
- 원인: 결제 요청의 amount를 승인 금액으로 신뢰. 주문 상품/원래 금액과 실제 승인 금액은 별도 보존.
- 사전 조건: student 로그인, VULN-11 활성화, 가상 포인트 잔액 보유.
- 검증: 에어 사운드(129,000원) 장바구니 추가 → 주문 → VOLTIX Pay 선택. Burp에서 결제 POST의 `amount=129000`을 `amount=1`로 변경하고 나머지 토큰/쿠키 유지. 또는 개발자 도구로 hidden amount 수정.
- 예상 결과: 1원만 차감되어 PAID, payments.requested_amount=1 / approved_amount=1, 원래 주문 total=129000 유지. 주문 상세에서 두 금액 비교. 취소 시 1원만 환불.
- 정상 비교: VULN-11 OFF 후 새 주문으로 동일 요청 → DECLINED, 주문 FAILED, 잔액 유지. 정상 금액으로 재시도하면 승인.
- 영향: 가상 잔액보다 큰 가치의 주문을 낮은 금액에 승인. 외부 PG나 실제 금융 거래에는 연결되지 않음.
- 안전한 수정: 주문 생성 시 DB 상품 가격으로 계산하고 주문 항목에 서버 스냅샷 저장. 승인 시 서버의 주문 항목 합계를 재계산/비교. 공급자는 서버 금액으로만 호출. 서버 금액 기준 환불, 원자적 상태 전이와 중복 승인 차단.
- 분류: CWE-472 / CWE-602, OWASP A04:2021 (사업 로직 신뢰 경계에 대한 본 프로젝트 분류).

## 검증 범위와 복원

`tests/test_shop.py`는 정상/취약 쌍을 비교하며 실제 HTTP 응답, DB 상태, 금액, 재고, 중복·동시 승인/환불을 검사합니다. VULN-04/08/10은 호스트 실행을 하지 않고 worker 호출 mock 및 503 fail-closed를 검사합니다. 실제 실행은 `docker compose exec -T shop python scripts/verify_worker.py`에서 확인합니다. 실제 브라우저 스크립트 실행, 컨테이너 격리 검증 여부는 `docs/PROGRESS.md`를 확인하세요.

복원은 앱을 중지한 뒤 `python scripts/reset_db.py --yes` 또는 Compose shop에서 `flask --app app:create_app reset-db --yes`. 초기 가상 계정/주문/포인트/재고로 돌아가며 업로드도 제거됩니다. 학생 VM/worker는 실습 종료 후 폐기합니다. 취약 기능을 끄는 것은 과거 저장된 악성 데이터 삭제를 의미하지 않습니다.
