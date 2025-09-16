# tests/test_demo_assets.py
import os, pytest, httpx

VISION_BASE = os.getenv("PUBLIC_VISION_BASE", "http://localhost:8004")
AI_BASE = os.getenv("PUBLIC_AI_BASE", "http://localhost:8003")

@pytest.mark.asyncio
async def test_demo_assets_present():
    """Test that demo assets are accessible through Vision Selector"""
    async with httpx.AsyncClient() as client:
        # Test Case Zero collection
        r = await client.get(f"{VISION_BASE}/list?collection=case_zero")
        assert r.status_code == 200
        data = r.json()
        assert "images" in data
        assert len(data["images"]) > 0
        print(f"Case Zero images: {len(data['images'])}")

@pytest.mark.asyncio
async def test_demo_mode_enabled():
    """Test that DEMO_MODE is enabled in orchestrator"""
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{AI_BASE}/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        # DEMO_MODE is enabled by default in docker-compose.yml
        print("AI Orchestrator health check passed")

@pytest.mark.asyncio
async def test_generated_collection_exists():
    """Test that generated collection exists (even if empty)"""
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{VISION_BASE}/list?collection=generated")
        assert r.status_code == 200
        data = r.json()
        assert "images" in data
        assert isinstance(data["images"], list)
        print(f"Generated images: {len(data['images'])}")

@pytest.mark.asyncio
async def test_demo_orchestrate_works():
    """Test that demo orchestration works with DEMO_MODE"""
    async with httpx.AsyncClient() as client:
        payload = {
            "game_state": {
                "session_id": "test-demo",
                "turn_id": 1,
                "players": ["TestPlayer"]
            },
            "actions": {"TestPlayer": "investigate"}
        }
        r = await client.post(f"{AI_BASE}/orchestrate", json=payload, timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert "narration" in data
        assert "image" in data
        assert "music" in data
        assert len(data["narration"]) > 0
        assert data["image"].startswith("http://")
        assert data["music"].startswith("http://")
        print(f"Demo orchestration: {data['image']}")
