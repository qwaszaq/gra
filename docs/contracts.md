# Kontrakty komunikacji (skrót)

Wersja: zob. contracts/VERSION.md (obecnie 1.0.0)

## WebSocket
- Login (client → game_server): ws_login.schema.json
- Action (client → game_server): ws_action.schema.json
- Narrative Update (server → clients): ws_narrative_update.schema.json

## HTTP
- Supervisor /validate: supervisor_request/response.schema.json
- Orchestrator /orchestrate: orchestrate_request/response.schema.json
- TTS /speak: tts_request.schema.json
- Admin /log: admin_log.schema.json

Każda wiadomość może mieć envelope: contract_version (domyślnie "1.0.0"), timestamp, request_id.

Przykłady:

Login
{ "type":"login", "player":"Marlow", "session_id":"demo-1" }

Action
{ "type":"action", "player":"Marlow", "session_id":"demo-1", "turn_id":1, "text_raw":"Przesłuchuję świadka" }

Narrative Update
{
  "type":"narrative_update",
  "session_id":"demo-1",
  "turn_id":1,
  "text":"Deszcz bębni o dach...",
  "image":"http://localhost:8004/assets/images/case_zero/turn1.png",
  "voice_audio":"http://localhost:8001/audio/turn1_demo-1.wav",
  "music": null
}
