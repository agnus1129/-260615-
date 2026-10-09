# -*- coding: utf-8 -*-
"""
방송 대시보드 — 클라우드 중계 서버 (Railway 등에 배포)
- 방문자에게 dashboard.html + GET /api/state 제공 (공개)
- 상규씨 PC의 pusher.py 가 보내는 POST /push 를 받아 최신 상태를 메모리에 보관
- /push 는 PUSH_TOKEN 으로 잠금 (헤더 X-Push-Token) → 아무나 가짜 숫자 못 넣음
- 민감정보 없음: 계좌 별명/금액만 중계 (login·계좌번호는 애초에 안 들어옴)

★[크리 261009 S578] 접속자 기록 추가 — 주인님 지시 "접속자 IP별로 구분해서 접속 순간에 카톡으로"
  손님 IP 를 보는 자는 이 서버뿐이다(화면을 그리는 쪽). PC1 은 자료만 올린다.
  그런데 pusher 가 3초마다 /push 를 때리니, **그 응답에 실어 보내면 통로가 공짜다.**
  기록은 cloud_access.py 가 하고, 카톡은 PC1 이 쏜다. 여기엔 아무것도 쌓지 않는다.

필요 환경변수:
  PORT       : Railway가 자동 주입 (직접 설정 X)
  PUSH_TOKEN : 임의의 긴 비밀 문자열 — pusher.py 와 반드시 동일하게
표준 라이브러리만 사용 (추가 패키지 없음).
"""
import os, json, time, threading, logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cloud_access                      # [S578] 접속자 기록기 (같은 폴더)

# ─────────────────────── 설정 ───────────────────────
PORT = int(os.environ.get("PORT", "8787"))        # Railway가 $PORT 주입, 로컬 테스트는 8787
PUSH_TOKEN = os.environ.get("PUSH_TOKEN", "")     # 비면 push 차단(안전). 운영 시 반드시 설정
STALE_SEC = 30                                    # 이 시간 넘게 push 없으면 stale 플래그
# ─────────────────────────────────────────────────────

HERE = os.path.dirname(os.path.abspath(__file__))
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("relay")

_STATE = {"accounts": [], "brief": [], "ts": 0}
_PUSHED_AT = 0.0
_LOCK = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):           # 접속 로그 소음 제거
        # ★[S578] 소음은 그대로 0 으로 두고, 손님만 조용히 적는다.
        #   /push 는 PC1 이 때리는 것이니 손님이 아니다 — 빼야 PC1 에게 알림이 가지 않는다.
        #   기록이 실패해도 화면은 그대로 뜬다(cloud_access 안에서 전부 try 로 감쌈).
        try:
            p = str(getattr(self, "path", "") or "")
            if not p.startswith("/push") and not p.startswith("/healthz"):
                cloud_access.note(self.headers.get, p,
                                  self.client_address[0] if self.client_address else None)
        except Exception:
            pass

    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/api/state"):
            with _LOCK:
                st = dict(_STATE)
            st["stale"] = ((time.time() - _PUSHED_AT) > STALE_SEC) if _PUSHED_AT else True
            payload = json.dumps(st, ensure_ascii=False).encode("utf-8")
            self._send(200, payload, "application/json; charset=utf-8")
            return
        if self.path.startswith("/healthz"):      # Railway 헬스체크용
            self._send(200, b"ok", "text/plain; charset=utf-8")
            return
        # 그 외 → 대시보드 화면
        try:
            with open(os.path.join(HERE, "dashboard.html"), "rb") as f:
                self._send(200, f.read(), "text/html; charset=utf-8")
        except Exception as e:
            self._send(500, ("dashboard.html 없음: %s" % e).encode("utf-8"), "text/plain; charset=utf-8")

    def do_POST(self):
        if not self.path.startswith("/push"):
            self._send(404, b"not found", "text/plain; charset=utf-8")
            return
        # 토큰 검증
        token = self.headers.get("X-Push-Token", "")
        if (not PUSH_TOKEN) or (token != PUSH_TOKEN):
            self._send(403, b"forbidden", "text/plain; charset=utf-8")
            log.warning("push 거부 — 토큰 불일치/미설정")
            return
        try:
            ln = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(ln)
            data = json.loads(raw.decode("utf-8"))
        except Exception as e:
            self._send(400, ("bad json: %s" % e).encode("utf-8"), "text/plain; charset=utf-8")
            return
        global _PUSHED_AT
        with _LOCK:
            _STATE["accounts"] = data.get("accounts", [])
            _STATE["brief"] = data.get("brief", [])
            _STATE["ts"] = data.get("ts", int(time.time() * 1000))
            _PUSHED_AT = time.time()
        # ★[S578] 모아둔 손님 명단을 응답에 실어 PC1 으로 넘긴다 (넘긴 뒤 큐는 비워진다).
        #   조회가 실패해도 {"ok":true} 는 반드시 나간다 — pusher 가 전과 똑같이 돌게.
        try:
            _acc = cloud_access.drain()
        except Exception:
            _acc = []
        _body = json.dumps({"ok": True, "acc": _acc}, ensure_ascii=False).encode("utf-8")
        self._send(200, _body, "application/json; charset=utf-8")


def main():
    log.info("=" * 60)
    log.info("중계 서버 시작 — 0.0.0.0:%d" % PORT)
    if not PUSH_TOKEN:
        log.warning("⚠ PUSH_TOKEN 미설정 — push가 모두 차단됩니다. 환경변수 PUSH_TOKEN 설정 필수!")
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        log.info("종료")


if __name__ == "__main__":
    main()
