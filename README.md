# VOLTIX — Power Your Digital Life

기존 Electro HTML 템플릿으로 만든 한국어 전자제품 쇼핑몰이자 대학교 웹보안 수업용 Flask 애플리케이션입니다. 상품·회원·배송지·장바구니·주문·리뷰·게시판·관리자·가상 결제를 제공합니다. 모든 회원, 상품, 배송 및 금융 데이터는 가상입니다.

## 빠른 실행 (Ubuntu / Python 3.10 이상)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

접속: http://127.0.0.1:5000. 최초 실행에서 스키마와 기본 데이터가 자동 생성됩니다. 별도의 Apache, MySQL, PHP 설치가 필요하지 않습니다. `.env`는 Compose가 읽으며 Python 자체 실행은 자동으로 읽지 않습니다. 필요한 변수는 셸에서 `export`하세요.

```bash
export VOLTIX_HOST=127.0.0.1
export VOLTIX_PORT=5000
export VOLTIX_DB=instance/voltix.sqlite3
export VOLTIX_SECRET='실습-인스턴스별-긴-무작위-문자열'
python app.py
```

`VOLTIX_DB` 상대 경로는 실행 디렉터리 기준입니다. 기본 경로는 프로젝트 `instance/`입니다. 비밀키를 지정하지 않으면 실행마다 생성되어 재시작 시 로그인 세션이 만료됩니다. 여러 프로세스로 운영할 때 반드시 같은 환경변수 키를 설정하세요. 개발 디버거는 비활성화되어 있습니다.

## DB 관리

```bash
flask --app app:create_app init-db          # 기존 데이터 보존, 중복 seed 없음
flask --app app:create_app reset-db --yes   # 실습 데이터와 첨부파일 삭제 후 재생성
python scripts/reset_db.py --yes           # 같은 초기화 명령
```

실행 중 초기화는 진행하지 마세요. 초기화는 명시적인 삭제 명령이며 테스트 계정/가상 주문을 재생성합니다.

## 테스트 계정

| 아이디 | 비밀번호 | 권한 |
|---|---|---|
| admin | Admin123! | 관리자 |
| student | Student123! | 일반 |
| alice | Student123! | 일반 |

가입 시 3,000,000 가상 포인트와 5,000,000원 한도의 테스트 카드가 발급됩니다. 마이페이지에서 카드 식별자(`TEST-0002-4242` 등), 유효기간 `12/30`, 테스트 PIN `1234`를 확인합니다. 비밀번호와 PIN은 해시로 저장합니다. 실제 카드번호를 받는 필드/PG 연동은 없습니다.

## 사용 흐름

- 상품 목록: 검색, 카테고리, 최소/최대 가격, 정렬 → 상세, 리뷰, 장바구니 담기
- 회원: 가입/로그인, 정보·비밀번호 수정, 배송지 추가·수정·삭제
- 장바구니: 수량 변경/삭제 → 배송지 선택 → 주문 생성 및 재고 예약
- 결제: VOLTIX Pay 또는 테스트 카드 인증 → 승인/거절 → 결과·주문·결제 이력 조회
- 포인트: 가상 충전(1회 1,000~1,000,000), 차감, 환불 이력
- 주문 취소: 미결제 주문은 CANCELLED, 승인된 주문은 REFUNDED; 재고 복원, 실제 승인 금액만 환불
- 게시판: 글 CRUD, 댓글, 첨부 다운로드. 일반 모드는 txt/png/jpg/pdf 확장자만 허용하고 다운로드로 제공
- 관리자: `/login`에서 관리자 계정 로그인 → 회원 권한 관리, 상품 등록/수정/판매 종료, 주문 조회/취소, 결제 내역, 글 관리, 시스템 진단
- 사용자 지정 메시지: 마이페이지 → 나만의 인사 메시지

상품 삭제는 주문 이력을 보존하는 판매 종료 방식입니다. 쿠폰은 확장용 스키마/seed만 제공하며 할인 적용 UI는 없습니다. 실제 배송, 외부 이메일 발송, 실결제는 구현 범위에 포함하지 않습니다.

## 보안 실습 모드

기본은 모든 취약점 OFF입니다. 개별 활성화 예시:

```bash
export VOLTIX_LAB_MODE=1
export VOLTIX_VULNS=VULN-01,VULN-02,VULN-11
python app.py
```

일반 모드 비교는 `VOLTIX_LAB_MODE=0`, 개별 OFF는 목록에서 해당 ID 제거 후 재시작합니다. `VOLTIX_VULNS=all`은 11개 전부 활성화합니다. 취약한 XSS 세션이 다른 실습에 영향을 주지 않도록 시나리오별 새 데이터/브라우저 프로필을 권장합니다.

**VULN-04 Python 실행, VULN-08 SSTI, VULN-10 명령 주입은 별도 worker 없이는 503으로 차단됩니다.** 호스트 Python 프로세스는 업로드를 실행하거나 사용자 템플릿을 평가하거나 셸 명령을 호출하지 않습니다.

### 격리된 실행 실습

학생별 별도 일회용 Ubuntu VM 안에서 Docker Compose를 실행하세요. 컨테이너는 호스트 커널을 공유하므로 VM은 격리 경계의 일부입니다. 공용 인터넷에 노출하지 않습니다.

```bash
cp .env.example .env
# .env의 VOLTIX_SECRET, VOLTIX_WORKER_TOKEN을 각각 긴 무작위 문자열로 설정
# 예: python3 -c 'import secrets; print(secrets.token_hex(32))'
docker compose up --build -d
docker compose exec -T shop python scripts/verify_worker.py
docker compose logs -f shop worker
```

Compose는 실습 모드를 켜며 호스트 `127.0.0.1:5000`만 게시합니다. worker 포트, Docker 소켓, 호스트 파일, 학생 간 공유 폴더는 마운트하지 않습니다. 내부 네트워크, 비특권 UID, cap_drop, read-only root, 임시 scratch, CPU/메모리/PID 제한을 적용합니다. 실행 자식 프로세스는 seccomp로 새 소켓/연결·추적·마운트·namespace 작업을 거부합니다. 사용자 코드는 2초 CPU/3초 wall time, 출력 32KB, 메모리 192MB로 제한하고 프로세스 그룹을 정리합니다. 명령 실습은 `echo`, `id`, `whoami`, `pwd`, `uname`만 허용합니다. Python 업로드 실습 소스 한도는 64KB입니다. worker에 실제 데이터나 비밀을 넣지 마세요. worker 침해/서비스 중단 가능성 자체는 의도된 실습 범위입니다.

학생별 `docker compose -p student01 ...`처럼 프로젝트를 분리하고 포트도 겹치지 않게 변경하세요. 한 인스턴스를 여러 학생의 신뢰 경계로 사용하지 않습니다. VM 스냅샷/Compose 데이터는 실습 후 폐기합니다.

## 테스트

```bash
python -m unittest discover -s tests -v
python -m compileall -q app.py config.py routes services database vulnerabilities lab scripts
```

현재 27개 통합 테스트: 기능 흐름, 결제 실패/재시도/환불, 동시 결제, DB 재초기화, 11개 실습의 정상/취약 모드 및 고위험 worker 전달/차단. 고위험 테스트는 mock을 사용하므로 실제 실행 검증과 구분합니다. 실제 Linux worker 검증은 위 `verify_worker.py`로 수행합니다.

## 구조 및 문서

```text
app.py / config.py             앱 팩토리, 설정, CLI, CSRF
routes/                       auth/products/cart/orders/payments/board/admin
services/payment_service.py   가상 결제 공급자, 원자적 승인/환불
vulnerabilities/              ID별 토글, 격리 worker 연결
 database/                    schema.sql, seed.py
 templates/                   base 및 기능별 Jinja2
 static/                      기존 CSS/JS/폰트/이미지 사본 + voltix.css
 lab/                         격리 worker, seccomp 실행 자식, Dockerfile
 scripts/                     초기화, 실제 worker 검증
 tests/                       Flask test client 통합 테스트
 docs/                        템플릿 분석, 단계별 결과, Apache 설정 예시
 instance/                    자동 생성 DB, 업로드, 더미 실습 파일 (Git 제외)
```

원본 HTML 5개와 css/js/img/fonts/screenshot 디렉터리를 보존했습니다. 템플릿 저작권/라이선스는 원본 제공 조건을 별도로 확인하세요.

- [템플릿 분석 및 계획](docs/TEMPLATE_ANALYSIS.md)
- [취약점별 재현 및 수정 방법](VULNERABILITIES.md)
- [구조·DB 관계·배포](ARCHITECTURE.md)
- [단계별 구현·검증 현황](docs/PROGRESS.md)
