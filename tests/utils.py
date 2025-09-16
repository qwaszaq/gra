"""
Test utilities for the game system.
"""
import asyncio
import json
import uuid
from typing import Dict, Any, Optional
import httpx


class TestClient:
    """Test client for making HTTP requests to services."""
    
    def __init__(self, base_url: str, timeout: int = 15):
        self.base_url = base_url
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
    
    async def post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make a POST request to the service."""
        response = await self.client.post(
            f"{self.base_url}{endpoint}",
            json=data
        )
        return response.json()
    
    async def get(self, endpoint: str) -> Dict[str, Any]:
        """Make a GET request to the service."""
        response = await self.client.get(f"{self.base_url}{endpoint}")
        return response.json()
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


def create_test_envelope(
    type: str,
    session_id: str,
    turn_id: Optional[str] = None,
    contract_version: str = "1.0.0",
    **kwargs
) -> Dict[str, Any]:
    """Create a test envelope for WebSocket/HTTP communication."""
    envelope = {
        "type": type,
        "session_id": session_id,
        "contract_version": contract_version,
        "timestamp": "2024-01-01T00:00:00Z",
        "request_id": str(uuid.uuid4())
    }
    
    if turn_id:
        envelope["turn_id"] = turn_id
    
    envelope.update(kwargs)
    return envelope


def load_scenario(scenario_name: str = "case_zero") -> Dict[str, Any]:
    """Load scenario configuration from JSON file."""
    with open(f"scenarios/{scenario_name}/scenario.json", "r") as f:
        return json.load(f)


async def wait_for_service(base_url: str, timeout: int = 30) -> bool:
    """Wait for a service to become available."""
    client = TestClient(base_url)
    start_time = asyncio.get_event_loop().time()
    
    while asyncio.get_event_loop().time() - start_time < timeout:
        try:
            await client.get("/health")
            await client.close()
            return True
        except:
            await asyncio.sleep(1)
    
    await client.close()
    return False
