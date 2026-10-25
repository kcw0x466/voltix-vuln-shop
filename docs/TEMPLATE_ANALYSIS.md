# Phase 1 — 기존 템플릿 분석 및 구현 계획

## 원본 현황
- `index.html`: 카테고리 프로모션 3개, 신상품/인기상품 Slick, hotdeal 배너, 공통 헤더/푸터.
- `store.html`: 카테고리·가격 필터, 정렬, 상품 그리드 및 페이지 UI.
- `product.html`: 이미지 캐러셀/zoom, 상품 설명/리뷰 탭, 수량 입력.
- `checkout.html`: 배송지 입력, 주문 요약, 결제 수단 선택.
- `blank.html`: 공통 헤더/푸터를 가진 일반 콘텐츠 틀. 고객센터/회원/관리 화면에 활용.

## Asset 목록
- css: Bootstrap 3, Font Awesome, Slick + theme, noUiSlider, style.css (원본 색상 #D10024 / #15161D).
- js: jQuery, Bootstrap, Slick, noUiSlider, jquery.zoom, main.js.
- fonts: Font Awesome 및 Slick 로컬 폰트 10개. 원본 Montserrat는 Google CDN 의존이므로 한국어 시스템 폰트로 대체.
- img: product01~09.png, shop01~03.png, hotdeal.png, logo.png (14개). 로고 이미지는 원본 보존, 서비스 로고는 VOLTIX 텍스트.
- screenshot: 원본 페이지 스크린샷 5개.

## 기존 기능과 미구현 기능
모든 HTML 내부 서비스 링크는 대부분 `#`; 외부 템플릿 제공처 링크와 탭 앵커만 존재한다. 페이지 간 실제 서비스 이동, 폼 서버 처리, 데이터 저장, 회원/상품/결제 로직은 없다. 모바일 nav, Slick, zoom, 수량 스텝퍼 및 가격 슬라이더만 브라우저 동작이다. main.js의 priceInputMax/Min null 참조를 Flask용 사본에서 수정한다. 원본 파일은 수정/삭제하지 않는다.

## 변환 계획
`base.html`에 원본 헤더/검색/Bootstrap navigation/푸터, 공통 CSS·JS를 배치한다. 원본 `.shop`, `.product`, `.products-slick`, `#hot-deal`, `#product-main-img`, `.billing-details`, `.order-details` 구조/클래스를 재사용한다. 내부 링크/Asset은 url_for, 상품 카드는 include로 통합한다. 필터와 정렬은 실제 GET 요청, 주문/리뷰 등은 POST 요청으로 연결한다. 추가 페이지는 원본 section/container/grid를 사용한다. 한국어 UI, 원화 필터, 가상 국내 주소를 사용한다.

## Blueprint / 데이터 설계
- auth: 가입/로그인/회원정보/비밀번호/배송지/지갑
- products: 홈/목록/상세/리뷰
- cart, orders, payments: 서버 장바구니 → 재고 예약 주문 → 결제 시도 → 승인/거절 → 취소/환불
- board: 게시글 CRUD/댓글/첨부
- admin: 회원/상품/주문/게시판/결제/진단
- vulnerabilities: ID별 설정, 고위험 실습 worker 호출, 경계 검증
DB: users → addresses/carts/wallets/virtual_cards/orders/posts; products → images/reviews/cart_items/order_items; orders → payments; wallets → wallet_transactions; posts → comments/attachments. 상세 DDL은 database/schema.sql.

## 단계별 검증 기준
1. 분석 및 설계: 원본 5개와 Asset 전수 조사 (완료).
2. 정상 쇼핑몰: 회원/상품/장바구니/주문/게시판/관리자 CRUD 테스트.
3. 결제: 원자적 포인트·카드 승인/거절, 중복 결제/환불 방지, 재고 복원 테스트.
4. 실습: VULN-01~11 재현, 비활성화 시 차단 비교. 실행 위험 기능은 worker 없으면 503.
5. 문서/테스트: 초기화 재실행, Flask test client 통합 테스트, 가능한 범위의 브라우저 검증. 실제 컨테이너 검증 여부는 명확히 기록.
