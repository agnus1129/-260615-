# -*- coding: utf-8 -*-
"""cloud_access.py — 레일웨이(중계서버)에 끼우는 '접속자 기록기'.
작성 2026-10-09 / PC1 / 크리.  주인님 지시: "대시보드 접속자 IP별로 구분해서 접속 순간에 카톡으로"

왜 레일웨이에 넣나
  주인님·참가자가 보는 화면은 **레일웨이가** 그린다. 손님 IP 를 보는 자도 레일웨이뿐이다.
  PC1 은 자료를 올려주기만 한다(3초마다 pusher.py → POST /push).
  그래서 **기록은 여기서, 카톡은 PC1 에서** 한다 — pusher 응답에 실어 3초 안에 건너간다.
  레일웨이 파일은 재배포 때 날아가므로 여기 쌓아두지 않는다. 건네주고 비운다.

레일웨이 프록시 뒤라서
  remote_addr 은 프록시 주소다. 진짜 손님은 X-Forwarded-For 의 **맨 앞**이다.

이 파일은 아무것도 막지 않는다. 전부 try 로 감싸서 기록이 실패해도 화면은 그대로 뜬다.
표준 라이브러리만 쓴다 — 레일웨이에 추가 설치가 필요 없다.
"""
import threading, time
from collections import OrderedDict

_LOCK = threading.Lock()
_SEEN = {}              # ip -> 마지막 요청 시각 (세션 묶기용)
_QUEUE = OrderedDict()  # ip -> {...}  (PC1 이 가져가면 비운다)
GAP = 600               # 같은 IP 10분 안의 재요청은 같은 방문으로 본다
MAXQ = 50               # 큐 상한 — 폭주해도 메모리가 안 터진다


def first_ip(headers_get, remote_addr=None):
    """프록시 뒤의 진짜 손님 주소. headers_get 은 헤더 이름을 받아 값을 주는 함수."""
    try:
        for h in ("CF-Connecting-IP", "True-Client-IP", "X-Real-IP"):
            v = headers_get(h)
            if v:
                return v.strip()
        xff = headers_get("X-Forwarded-For")
        if xff:
            return xff.split(",")[0].strip()      # 맨 앞이 원래 손님
    except Exception:
        pass
    return remote_addr or "-"


def note(headers_get, path="-", remote_addr=None):
    """요청 하나를 기록한다. 새 방문(처음 보는 IP 또는 10분 쉬었다 온 IP)만 큐에 담는다."""
    try:
        ip = first_ip(headers_get, remote_addr)
        if not ip or ip == "-":
            return
        ua = ""
        try:
            ua = (headers_get("User-Agent") or "")[:120]
        except Exception:
            pass
        now = time.time()
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now))
        with _LOCK:
            prev = _SEEN.get(ip)
            _SEEN[ip] = now
            fresh = (prev is None) or (now - prev > GAP)
            if len(_SEEN) > 2000:                 # 오래된 기억 정리
                for k in sorted(_SEEN, key=_SEEN.get)[:500]:
                    _SEEN.pop(k, None)
            if not fresh:
                e = _QUEUE.get(ip)
                if e:
                    e["hits"] += 1
                    e["last"] = ts
                return
            if len(_QUEUE) >= MAXQ:
                return
            _QUEUE[ip] = {"ip": ip, "first": ts, "last": ts, "hits": 1,
                          "path": str(path)[:80], "ua": ua}
    except Exception:
        pass


def drain():
    """PC1 이 가져간다. 돌려준 뒤 비운다 — 두 번 알리지 않는다."""
    try:
        with _LOCK:
            out = list(_QUEUE.values())
            _QUEUE.clear()
        return out
    except Exception:
        return []
