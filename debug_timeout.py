#!/usr/bin/env python3
import asyncio
import json
import websockets

async def debug_timeout():
    print("🔍 Debug Timeout Test")
    
    session_id = "debug-timeout"
    ws_url = "ws://localhost:65432/ws"
    
    try:
        async with websockets.connect(ws_url) as w1:
            print("✅ Connected client 1")
            
            # Login
            await w1.send(json.dumps({"type":"login","player":"Marlow","session_id":session_id}))
            print("✅ Sent login")
            
            # Wait for response
            resp = await asyncio.wait_for(w1.recv(), timeout=5)
            print(f"📨 Login response: {resp}")
            
            # Connect second client
            async with websockets.connect(ws_url) as w2:
                print("✅ Connected client 2")
                
                # Login second client
                await w2.send(json.dumps({"type":"login","player":"Spade","session_id":session_id}))
                print("✅ Sent second login")
                
                # Wait for second login response
                resp2 = await asyncio.wait_for(w2.recv(), timeout=5)
                print(f"📨 Second login response: {resp2}")
                
                # Send action from first client
                print("📤 Sending action from Marlow...")
                await w1.send(json.dumps({"type":"action","player":"Marlow","session_id":session_id,"turn_id":0,"text_raw":"Przesłuchuję świadka"}))
                
                # Wait for action response
                resp = await asyncio.wait_for(w1.recv(), timeout=5)
                print(f"📨 Action response: {resp}")
                
                # Wait a bit and check health
                await asyncio.sleep(2)
                print("⏳ Waiting 2 seconds...")
                
                # Check if timer is running
                import httpx
                health = httpx.get("http://localhost:65432/health").json()
                print(f"🏥 Health: {health}")
                
                # Wait for timeout
                print("⏳ Waiting for timeout (15 seconds)...")
                start_time = asyncio.get_event_loop().time()
                
                while asyncio.get_event_loop().time() - start_time < 18:
                    try:
                        resp = await asyncio.wait_for(w1.recv(), timeout=1)
                        data = json.loads(resp)
                        if data.get("type") == "narrative_update":
                            elapsed = asyncio.get_event_loop().time() - start_time
                            print(f"🎉 Got narrative_update after {elapsed:.1f} seconds!")
                            print(f"   Text: {data.get('text')}")
                            return
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        print(f"Error receiving: {e}")
                        break
                
                print("❌ No narrative_update received")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(debug_timeout())
