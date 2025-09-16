# tools/seed_admin_fake_logs.py
import httpx, time
from common import ADMIN_BASE, admin_headers

def main():
    for i in range(1,4):
        payload = {
            "level": "INFO",
            "message": f"[seed] Tura {i}: dym tnie powietrze.",
            "service": "game_server",
            "session_id": f"demo-{i}",
            "turn_id": str(i),
            "player": "Marlow",
            "action": "investigate",
            "extra_data": {"actions": {"Marlow":"investigate","Spade":"interrogate"}}
        }
        r = httpx.post(f"{ADMIN_BASE}/log", headers=admin_headers(), json=payload, timeout=10)
        print("Admin log:", r.status_code, payload["session_id"])
        time.sleep(0.2)

if __name__ == "__main__":
    main()
