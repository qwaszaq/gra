import os, httpx

ADMIN_BASE = os.getenv("ADMIN_BASE","http://localhost:8002")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN","dev_admin_token_123")

def test_admin_pdf_generation():
    r = httpx.get(f"{ADMIN_BASE}/report/pdf", headers={"X-Admin-Token":ADMIN_TOKEN}, timeout=20)
    assert r.status_code == 200
    assert r.headers.get("content-type","").startswith("application/pdf")
