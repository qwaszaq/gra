# Kontrakty komunikacji

Wersja: zob. contracts/VERSION.md (obecnie 1.0.0)

## Architektura systemu

System składa się z następujących serwisów:
- **Game Server** (port 65432) - główny serwer gry z WebSocket
- **TTS Service** (port 8001) - synteza mowy
- **Admin Service** (port 8002) - logowanie i administracja
- **AI Orchestrator** (port 8003) - orkiestracja AI
- **Vision Selector** (port 8004) - selekcja obrazów
- **Supervisor Service** (port 8005) - walidacja akcji graczy
- **Client** (port 3000) - interfejs użytkownika
- **Redis** (port 6379) - cache i sesje

## WebSocket (Game Server)
- Login (client → game_server): ws_login.schema.json
- Action (client → game_server): ws_action.schema.json
- Narrative Update (server → clients): ws_narrative_update.schema.json

## HTTP API

### Supervisor Service (port 8005)
- POST /validate - walidacja akcji gracza
  - Request: supervisor_request.schema.json
  - Response: supervisor_response.schema.json

### AI Orchestrator (port 8003)
- POST /orchestrate - orkiestracja narracji
  - Request: orchestrate_request.schema.json
  - Response: orchestrate_response.schema.json

### TTS Service (port 8001)
- POST /speak - synteza mowy
  - Request: tts_request.schema.json
  - Response: { "audio_url": "string" }

### Vision Selector (port 8004)
- GET /assets - serwowanie zasobów
- POST /match - dopasowanie obrazu do tekstu
  - Request: { "text": "string" }
  - Response: { "image_url": "string" }

### Admin Service (port 8002)
- POST /log - logowanie zdarzeń
  - Request: admin_log.schema.json
- GET / - dashboard administracyjny
- GET /report/pdf - raport PDF

## Envelope format

Każda wiadomość może mieć envelope z następującymi polami:
- `type` - typ wiadomości
- `session_id` - identyfikator sesji
- `turn_id` - identyfikator tury (opcjonalny)
- `contract_version` - wersja kontraktu (domyślnie "1.0.0")
- `timestamp` - znacznik czasu
- `request_id` - unikalny identyfikator żądania (UUID)

## Przykłady

### Login
```json
{
  "type": "login",
  "session_id": "demo-1",
  "contract_version": "1.0.0",
  "timestamp": "2024-01-01T00:00:00Z",
  "request_id": "uuid-here",
  "player": "Marlow"
}
```

### Action
```json
{
  "type": "action",
  "session_id": "demo-1",
  "turn_id": 1,
  "contract_version": "1.0.0",
  "timestamp": "2024-01-01T00:00:00Z",
  "request_id": "uuid-here",
  "player": "Marlow",
  "text_raw": "Przesłuchuję świadka"
}
```

### Narrative Update
```json
{
  "type": "narrative_update",
  "session_id": "demo-1",
  "turn_id": 1,
  "contract_version": "1.0.0",
  "timestamp": "2024-01-01T00:00:00Z",
  "request_id": "uuid-here",
  "text": "Deszcz bębni o dach...",
  "image": "http://localhost:8004/assets/images/case_zero/turn1.png",
  "voice_audio": "http://localhost:8001/audio/turn1_demo-1.wav",
  "music": null
}
```

## Environment Variables

Kluczowe zmienne środowiskowe:
- `PUBLIC_TTS_BASE` - publiczny URL TTS service
- `PUBLIC_VISION_BASE` - publiczny URL Vision Selector
- `PUBLIC_AI_BASE` - publiczny URL AI Orchestrator
- `ADMIN_BASE` - publiczny URL Admin Service
- `DATABASE_URL` - URL bazy danych (SQLite)
- `REDIS_URL` - URL Redis
- `SCENARIO` - aktywny scenariusz (case_zero)
- `ADMIN_TOKEN` - token autoryzacji admin

## Case Zero Fallback

Gdy `SCENARIO=case_zero`, system używa:
- Narracji z `scenarios/case_zero/scenario.json`
- Obrazów z `scenarios/case_zero/images/`
- Audio z `scenarios/case_zero/audio/`
