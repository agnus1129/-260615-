======================================================================
 방송 대시보드 — 내 땅에 짓는 공개 호스팅 (Railway)
======================================================================
구조: 상규씨 PC(pusher.py) ──push──> Railway(relay_server.py) ──view──> 누구나(폰/PC)

[A] 클라우드(Railway)에 올릴 파일 = 이 cloud 폴더 통째
    - relay_server.py / dashboard.html / Procfile / requirements.txt

[B] 상규씨 PC에 둘 파일 (dash 폴더에 이미 있음)
    - pusher.py  (+ 기존 dash_server.py 그대로 필요 — 로직 재사용)

----------------------------------------------------------------------
■ 1단계 — GitHub에 cloud 폴더 올리기
  · github.com 새 저장소(private 가능) 생성 → cloud 폴더 안의 4개 파일 업로드
    (Procfile 은 확장자 없음, 이름 그대로여야 함 — 대소문자 주의)

■ 2단계 — Railway 배포
  · railway.app 로그인 → New Project → Deploy from GitHub repo → 그 저장소 선택
  · Variables(환경변수)에 추가:
        PUSH_TOKEN = NmKKe9K2D6ofw0jSRqDFEGVHCa3S8fMn
    (PORT 는 Railway가 자동 주입 — 직접 넣지 말 것)
  · 배포되면 Settings → Networking → Generate Domain 으로 공개주소 생성
        예) https://vom-dash-production.up.railway.app

■ 3단계 — PC 송신기 가동
  · pusher.py 상단(또는 환경변수)에 채우기:
        CLOUD_URL  = (2단계에서 받은 https 주소)
        PUSH_TOKEN = NmKKe9K2D6ofw0jSRqDFEGVHCa3S8fMn   (Railway 와 반드시 동일)
  · 실행:  cd "D:\봄프로젝트(260104)\MT5_ATS(260421)\dash"
           python pusher.py
    (dash_server.py 와 같은 폴더에서 실행 — import 재사용)

■ 4단계 — 확인
  · 폰/PC 브라우저에서 2단계 공개주소 열기 → 실시간 대시보드.
  · 검열 없는 내 주소 = 남이 철거 못 함. OBS·유튜브 불필요.

※ logs/pusher_YYYYMMDD.log 에 전송 기록(약 1분마다 계좌별 수익률 요약).
※ PUSH_TOKEN 은 비밀. 노출되면 Railway Variables에서 새 값으로 교체 후 pusher도 동일 교체.
======================================================================
