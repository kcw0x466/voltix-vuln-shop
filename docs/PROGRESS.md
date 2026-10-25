# 단계별 구현 및 검증 현황

기준일: 2026-10-23 (Asia/Seoul). 구현 상태와 실제 환경 검증 상태를 구분한다.

## Phase 1 — 분석 및 설계

- 결과: 원본 HTML 5개, CSS/JS/폰트, 이미지 14개, 스크린샷 5개 조사. 링크 대부분이 #이고 서버 기능 없음 확인. 가격 입력 null 참조 확인.
- 변경: `docs/TEMPLATE_ANALYSIS.md`, `database/schema.sql`, Blueprint/서비스/격리 worker 설계.
- 확인: 원본 Asset과 Flask 정적 사본 해시 비교. JS main.js 외 기존 Asset 사본은 동일. 원본 HTML/Asset은 보존.
- 남은 작업: 없음. 원본 템플릿 라이선스의 재배포 조건 확인은 배포자 책임.

## Phase 2 — Flask 쇼핑몰

- 결과: 한국어 VOLTIX 공통 레이아웃과 기존 스타일/배너/상품 이미지 재사용. 회원 CRUD 일부(가입/프로필/비밀번호/배송지), 상품 검색·필터·정렬·리뷰, 장바구니, 주문, 게시판 CRUD/댓글/첨부, 관리자 회원 권한·상품·주문·글 관리.
- 변경: `app.py`, `config.py`, `routes/*.py`, `templates/**`, `static/**`, `database/**`.
- 테스트: 공개/인증 페이지 렌더, Asset 응답, 가입/중복/비밀번호, 배송지, 리뷰, 카트, 관리자 상품/취소, DB 초기화 통합 테스트 통과.
- 남은 검증: 실제 브라우저 반응형 레이아웃/JavaScript 슬라이더·확대·모바일 메뉴. 연결된 브라우저가 없고 native Chrome 제어는 컴퓨터 권한 미부여로 실패하여 시각 검증하지 못함. UI 애니메이션 보존을 코드상 확인했으나 실행 검증 완료로 간주하지 않음.

## Phase 3 — 가상 결제

- 결과: TEST- 접두어 카드/만료·PIN·한도, VOLTIX Pay/충전/원장, 승인·거절 이력, 재시도, 5가지 주문 상태, 재고 예약·취소 복원, 실제 승인액 환불. 공급자 registry로 확장 지점 제공.
- 변경: `services/payment_service.py`, `routes/orders.py`, `routes/payments.py`, `templates/orders/**`, `templates/payment/**`.
- 테스트: 포인트 차감/환불, 카드 인증 실패/승인/환불, 잔액 부족, 금액 불일치, 중복 승인/환불, 동시 승인 한 번만 처리, 재고 복원 통과.
- 남은 작업: 실제 금융 연동은 요구 범위 밖. 자동 예약 만료/쿠폰 적용은 구현하지 않음.

## Phase 4 — 실습

- 결과: VULN-01~11 경로와 개별 토글 구현. 기본 OFF. 실제 실행은 격리 worker만 사용. 더미 파일 경계 외 traversal 차단.
- 변경: `vulnerabilities/__init__.py`, 각 라우트의 ID 표시 분기, 관련 Jinja2, `lab/worker.py`, `lab/child.py`, Compose/Dockerfile, `scripts/verify_worker.py`, `VULNERABILITIES.md`.
- 테스트: SQLi 로그인/검색, reflected/stored XSS 응답 인코딩 차이, unrestricted upload 허용/거절, IDOR/관리 접근, CSRF 누락, traversal, 금액 변조 실결과 비교 통과. VULN-04/08/10의 worker 전달과 미연결 503은 mock/Flask로 검증.
- 남은 검증: Linux 컨테이너에서 Python 업로드 실행, 실제 SSTI 평가, 실제 shell 주입과 seccomp/network/resource 격리 확인. Docker CLI는 있으나 데몬 소켓이 없어 실행하지 못함. 격리 기능의 정상 동작이나 호스트 무영향을 실제 검증 완료로 보고하지 않음. README 명령으로 VM에서 검증해야 함.

## Phase 5 — 테스트 및 문서

- 결과: `python3 -m unittest discover -s tests -v`: **27개 통과**. compileall 통과. 환경변수 임시값으로 `docker compose config --quiet` 통과. Flask 개발 서버의 loopback 시작 확인.
- 변경: `tests/test_shop.py`, `README.md`, `VULNERABILITIES.md`, `ARCHITECTURE.md`, `.env.example`, 초기화/worker 검증 스크립트, Apache 샘플.
- 미검증: Ubuntu VM/실제 컨테이너, Gunicorn 실행(현재 호스트에 미설치), Apache proxy 실제 통합, 실제 브라우저 XSS/CSRF/시각·JS 동작. requirements의 Flask 3.1.2와 동일한 호스트 Flask 환경에서 테스트했으며, 호스트 Python은 3.14이다. VM Python 3.12 이미지는 아직 빌드하지 못함.
- 주의: 정상 기능과 취약 분기는 구현했으나 위 환경별 검증이 남아 있으므로 최종 배포 검증 완료 상태는 아니다. Git commit/push는 수행하지 않음.
