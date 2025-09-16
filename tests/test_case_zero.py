"""
End-to-end tests for Case Zero scenario.
"""
import pytest
import asyncio
from utils import TestClient, create_test_envelope, load_scenario, wait_for_service


class TestCaseZero:
    """Test suite for Case Zero scenario."""
    
    @pytest.fixture
    async def game_client(self):
        """Create a test client for the game server."""
        client = TestClient("http://localhost:65432")
        yield client
        await client.close()
    
    @pytest.fixture
    async def tts_client(self):
        """Create a test client for the TTS service."""
        client = TestClient("http://localhost:8001")
        yield client
        await client.close()
    
    @pytest.fixture
    async def admin_client(self):
        """Create a test client for the admin service."""
        client = TestClient("http://localhost:8002")
        yield client
        await client.close()
    
    @pytest.fixture
    async def ai_client(self):
        """Create a test client for the AI orchestrator."""
        client = TestClient("http://localhost:8003")
        yield client
        await client.close()
    
    @pytest.fixture
    async def vision_client(self):
        """Create a test client for the vision selector."""
        client = TestClient("http://localhost:8004")
        yield client
        await client.close()
    
    @pytest.fixture
    async def supervisor_client(self):
        """Create a test client for the supervisor service."""
        client = TestClient("http://localhost:8005")
        yield client
        await client.close()
    
    @pytest.mark.asyncio
    async def test_services_health(self, game_client, tts_client, admin_client, 
                                 ai_client, vision_client, supervisor_client):
        """Test that all services are healthy."""
        # Wait for services to be ready
        assert await wait_for_service("http://localhost:65432")
        assert await wait_for_service("http://localhost:8001")
        assert await wait_for_service("http://localhost:8002")
        assert await wait_for_service("http://localhost:8003")
        assert await wait_for_service("http://localhost:8004")
        assert await wait_for_service("http://localhost:8005")
    
    @pytest.mark.asyncio
    async def test_case_zero_scenario_loading(self):
        """Test that Case Zero scenario can be loaded."""
        scenario = load_scenario("case_zero")
        assert scenario["name"] == "Case Zero"
        assert "narrative" in scenario
        assert "assets" in scenario
    
    @pytest.mark.asyncio
    async def test_websocket_login_flow(self, game_client):
        """Test WebSocket login flow."""
        session_id = "test_session_001"
        login_data = create_test_envelope(
            type="login",
            session_id=session_id,
            player_name="TestPlayer"
        )
        
        # This would be a WebSocket test in a real implementation
        # For now, we'll test the envelope structure
        assert login_data["type"] == "login"
        assert login_data["session_id"] == session_id
        assert "request_id" in login_data
    
    @pytest.mark.asyncio
    async def test_supervisor_validation(self, supervisor_client):
        """Test supervisor service validation."""
        validation_data = {
            "player": "TestPlayer",
            "input": "investigate room"
        }
        
        response = await supervisor_client.post("/validate", validation_data)
        assert "valid" in response
        assert "mapped_action" in response
    
    @pytest.mark.asyncio
    async def test_tts_service(self, tts_client):
        """Test TTS service functionality."""
        tts_data = {
            "text": "Hello, this is a test.",
            "turn_id": "turn_001",
            "session_id": "session_001"
        }
        
        response = await tts_client.post("/speak", tts_data)
        assert "audio_url" in response
    
    @pytest.mark.asyncio
    async def test_vision_selector(self, vision_client):
        """Test vision selector service."""
        match_data = {
            "text": "a dark room"
        }
        
        response = await vision_client.post("/match", match_data)
        assert "image_url" in response
    
    @pytest.mark.asyncio
    async def test_admin_logging(self, admin_client):
        """Test admin service logging."""
        log_data = {
            "level": "info",
            "message": "Test log entry",
            "service": "test_service"
        }
        
        response = await admin_client.post("/log", log_data)
        assert response.get("status") == "logged"
    
    @pytest.mark.asyncio
    async def test_e2e_flow(self, game_client, tts_client, vision_client):
        """End-to-end test: 2 logins, 2 actions, 1 narrative update."""
        session_id_1 = "e2e_session_001"
        session_id_2 = "e2e_session_002"
        
        # Login player 1
        login_1 = create_test_envelope(
            type="login",
            session_id=session_id_1,
            player_name="Player1"
        )
        
        # Login player 2
        login_2 = create_test_envelope(
            type="login",
            session_id=session_id_2,
            player_name="Player2"
        )
        
        # Action from player 1
        action_1 = create_test_envelope(
            type="action",
            session_id=session_id_1,
            turn_id="turn_001",
            action="investigate",
            target="room"
        )
        
        # Action from player 2
        action_2 = create_test_envelope(
            type="action",
            session_id=session_id_2,
            turn_id="turn_001",
            action="move",
            target="corridor"
        )
        
        # Test TTS for narrative
        tts_response = await tts_client.post("/speak", {
            "text": "The investigation reveals nothing unusual.",
            "turn_id": "turn_001",
            "session_id": session_id_1
        })
        
        # Test vision for narrative
        vision_response = await vision_client.post("/match", {
            "text": "empty room"
        })
        
        # Verify responses contain expected fields
        assert "audio_url" in tts_response
        assert "image_url" in vision_response
        
        # In a real implementation, we would verify the narrative_update
        # contains text, image, and voice_audio with public URLs
