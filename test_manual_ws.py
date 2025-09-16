#!/usr/bin/env python3

import asyncio
import websockets
import json
import time

async def test_single_player():
    uri = "ws://localhost:65432/ws"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to WebSocket")
            
            # Login with single player
            login_msg = {
                "type": "login",
                "player": "TestManual",
                "session_id": "manual-test",
                "single_player": True,
                "bot_style": "ostrożny śledczy"
            }
            await websocket.send(json.dumps(login_msg))
            print("Sent login message")
            
            # Wait for response
            response = await websocket.recv()
            print("Received:", response)
            
            # Send action
            action_msg = {
                "type": "action",
                "player": "TestManual",
                "session_id": "manual-test",
                "turn_id": 0,
                "text_raw": "Sprawdzam miejsce zbrodni"
            }
            await websocket.send(json.dumps(action_msg))
            print("Sent action message")
            
            # Wait for responses (bot should respond + narrative_update)
            timeout = 30
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5)
                    data = json.loads(response)
                    print(f"Received message: {data.get('type', 'unknown')}")
                    
                    if data.get('type') == 'narrative_update':
                        print("SUCCESS: Received narrative_update!")
                        print(f"  Text: {data.get('text', '')[:100]}...")
                        print(f"  Image: {data.get('image', 'NONE')}")
                        print(f"  Voice: {data.get('voice_audio', 'NONE')}")
                        print(f"  Music: {data.get('music', 'NONE')}")
                        return True
                        
                except asyncio.TimeoutError:
                    print("No message received in 5s, continuing...")
                    continue
                    
            print("TIMEOUT: No narrative_update received")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_single_player())
    print(f"Test result: {'PASS' if result else 'FAIL'}")
