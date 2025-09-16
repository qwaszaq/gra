# 🕵️ Partnerzy w Zbrodni - Noir Detective Game

**Immersywna gra detektywistyczna w stylu noir z AI, gdzie gracze prowadzą śledztwo w atmosferze mokrych ulic, neonów i tajemnic.**

## 🎯 Przegląd Projektu

"Partnerzy w Zbrodni" to zaawansowana gra detektywistyczna wykorzystująca sztuczną inteligencję do generowania dynamicznych scenariuszy, obrazów i narracji w stylu film noir. Gracze wcielają się w rolę detektywów prowadzących śledztwo w mrocznym świecie przestępczości.

### 🎮 Kluczowe Funkcje

- **🤖 AI-Powered Storytelling** - LLM generuje dynamiczne sceny i dialogi
- **🎨 Dynamic Image Generation** - AI tworzy obrazy w stylu noir na podstawie akcji
- **🎵 Immersive Audio** - TTS narracja + SFX + muzyka tła
- **🧩 Case Board System** - Graficzna reprezentacja dowodów i powiązań
- **👥 Multiplayer Support** - Współpraca detektywów w czasie rzeczywistym
- **🎭 NPC Relations** - System relacji z postaciami (mood/trust/fear)
- **🔍 Free-Form Investigation** - Natural language input dla akcji

## 🏗️ Architektura Systemu

### Backend Services (Microservices)

#### 🧠 AI Orchestrator (`services/ai_orchestrator/`)
**Główny mózg systemu** - koordynuje wszystkie komponenty AI
- **LLM Integration** - Generuje sceny, dialogi, epilogi
- **Story Engine** - Przetwarza natural language input na akcje
- **Shot Planning** - Wybiera ujęcia filmowe na podstawie tagów
- **Graph Memory** - Zarządza grafem sprawy (węzły, krawędzie)
- **Image Generation** - Koordynuje generowanie obrazów (local/cloud)
- **Reframe Logic** - Przekształca off-topic input na noir context

#### 🎮 Game Server (`services/game_server/`)
**Serwer gry** - zarządza sesjami i stanem gry
- **WebSocket Management** - Real-time communication
- **Session Handling** - Multiplayer session isolation
- **Turn Management** - Turn-based gameplay
- **State Management** - Game state, inventory, relations
- **Story Mode** - Single-player z AI bot

#### 🛡️ Supervisor Service (`services/supervisor_service/`)
**Walidacja inputu** - sprawdza poprawność akcji gracza
- **Input Validation** - Waliduje akcje gracza
- **Domain Detection** - Wykrywa off-topic input
- **Action Mapping** - Mapuje input na akcje gry
- **Rate Limiting** - Ogranicza częstotliwość akcji

#### 👁️ Vision Selector (`services/vision_selector/`)
**Wybór obrazów** - dopasowuje obrazy do scen
- **CLIP Embeddings** - Semantic image matching
- **FAISS Index** - Szybkie wyszukiwanie podobnych obrazów
- **Library Management** - Zarządza biblioteką obrazów
- **Top-K Matching** - Zwraca najlepsze dopasowania

#### 🎤 TTS Service (`services/tts_service/`)
**Text-to-Speech** - generuje narrację
- **Multi-Provider** - ElevenLabs, local TTS
- **Caching** - Redis cache dla wydajności
- **Audio Processing** - Konwersja do różnych formatów
- **Voice Selection** - Różne głosy dla różnych postaci

#### 🖼️ Image Generator (`services/image_gen/`)
**Generowanie obrazów** - tworzy obrazy w stylu noir
- **Local MPS SD** - Stable Diffusion na CPU
- **Multi-Provider** - Google Vertex AI, Banana.dev
- **Caching** - Redis + disk cache
- **Style Consistency** - Noir aesthetic enforcement

#### 📊 Admin Service (`services/admin_service/`)
**Administracja** - logi i raporty
- **Logging** - Centralized logging system
- **PDF Reports** - Generuje raporty z sesji
- **Database** - SQLite storage
- **Admin Panel** - Web interface

### Frontend

#### 🌐 Web Client (`web_client/`)
**React/Vite aplikacja** - interfejs użytkownika
- **Real-time UI** - WebSocket communication
- **Case Board** - Graficzna reprezentacja sprawy
- **Gallery** - Wyświetlanie obrazów
- **Audio Player** - TTS + SFX + muzyka
- **State Management** - React hooks + context

## 🎲 Mechanika Gry

### 🎯 Tryby Gry

#### Single Player Mode
- **AI Bot Partner** - Gracz współpracuje z AI botem
- **Story Mode** - LLM generuje dynamiczne sceny
- **Free-Form Actions** - Natural language input
- **Auto Turn Management** - Bot automatycznie zamyka tury

#### Multiplayer Mode
- **2 Players** - Współpraca detektywów
- **Turn-Based** - Alternujące tury graczy
- **Real-time Communication** - WebSocket sync
- **Shared State** - Wspólny stan gry

### 🧩 System Sprawy (Case Board)

#### Węzły (Nodes)
- **Clues** - Dowody materialne
- **Suspects** - Podejrzani
- **Witnesses** - Świadkowie
- **Locations** - Miejsca zdarzeń

#### Krawędzie (Edges)
- **implies** - Sugeruje powiązanie
- **contradicts** - Zaprzecza
- **found_at** - Znaleziono w miejscu
- **seen_with** - Widziano z kimś

#### Dedukcja
- **Manual Linking** - Gracz łączy węzły ręcznie
- **AI Inference** - System automatycznie sugeruje powiązania
- **Confidence Scoring** - Poziomy pewności powiązań

### 🎭 System Relacji NPC

#### Atrybuty Relacji
- **Mood** (0-100) - Nastrój postaci
- **Trust** (0-100) - Zaufanie do gracza
- **Fear** (0-100) - Strach przed graczem

#### Dynamika
- **Delta Updates** - Zmiany po każdej scenie
- **Behavioral Impact** - Wpływ na dialogi i akcje
- **Long-term Memory** - Trwałe zmiany w relacjach

### 🎨 System Obrazów

#### Two-Gear Image System
1. **Immediate** - Biblioteka obrazów (Vision Selector)
2. **Background** - AI generation (local/cloud)
3. **Live Swap** - Płynna zamiana obrazów

#### Shot Grammar
- **12+ Shot Templates** - Ujęcia filmowe
- **Tag Matching** - Automatyczny wybór ujęcia
- **Provider Prompts** - Optymalizowane prompty dla AI
- **Style Consistency** - Noir aesthetic

### 🎵 System Audio

#### Komponenty Audio
- **TTS Narration** - Głos narratora
- **SFX** - Efekty dźwiękowe (reload, lighter, rain, gavel, heartbeat)
- **Background Music** - Muzyka atmosferyczna
- **Voice Acting** - Różne głosy dla postaci

#### Zarządzanie Audio
- **Queue System** - Kolejkowanie dźwięków
- **Mute Controls** - Kontrola głośności
- **Auto-play** - Automatyczne odtwarzanie
- **Caching** - Cache dla wydajności

## 🛠️ Technologie

### Backend Stack
- **Python 3.12** - Główny język
- **FastAPI** - Web framework
- **Pydantic** - Data validation
- **httpx** - Async HTTP client
- **WebSockets** - Real-time communication
- **Redis** - Caching i session storage
- **SQLite** - Logging database

### AI/ML Stack
- **LLM Integration** - OpenAI, local models
- **CLIP** - Image embeddings
- **FAISS** - Vector similarity search
- **Stable Diffusion** - Image generation
- **ElevenLabs** - TTS
- **Google Vertex AI** - Cloud image generation

### Frontend Stack
- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **WebSocket** - Real-time communication
- **CSS3** - Styling

### DevOps & Infrastructure
- **Docker** - Containerization
- **Docker Compose** - Orchestration
- **Makefile** - Automation
- **Playwright** - E2E testing
- **Pytest** - Backend testing

## 🚀 Instalacja i Uruchomienie

### Wymagania
- Docker & Docker Compose
- Node.js 18+ (dla frontend)
- Python 3.12+ (dla development)

### Szybki Start

```bash
# Klonowanie repozytorium
git clone https://github.com/qwaszaq/gra.git
cd gra

# Konfiguracja środowiska
cp .env.example .env
# Edytuj .env - dodaj API keys

# Uruchomienie wszystkich serwisów
make up

# Uruchomienie frontend
cd web_client && npm install && npm run dev

# Otwórz http://localhost:5173
```

### Konfiguracja Environment

```bash
# .env - Kluczowe zmienne
STORY_MODE=1
SINGLE_PLAYER_DEFAULT=1
STORY_NL_MODE=1
ENABLE_SFX=1
ENABLE_CASEBOARD=1

# AI Providers
LLM_ENABLED=1
LLM_URL=http://localhost:11434
IMAGE_PROVIDER=diffusers
TTS_PROVIDER=elevenlabs

# API Keys
ELEVENLABS_API_KEY=your_key
GOOGLE_APPLICATION_CREDENTIALS=path/to/credentials.json
```

## 🧪 Testowanie

### Backend Tests
```bash
# Wszystkie testy
make test

# Konkretne testy
pytest tests/test_e2e_ws.py
pytest tests/test_single_player_basic.py
```

### Frontend Tests
```bash
cd web_client

# Playwright E2E tests
npm run test:ui

# Konkretne testy
npm run test:ui:sp    # Single Player
npm run test:ui:mp    # Multiplayer
npm run test:ui:all   # Wszystkie
```

### Smoke Tests
```bash
# Testy funkcjonalności
make smoke-providers
make smoke-swap
make shot-smoke
```

## 📊 Monitoring i Logi

### Logi Serwisów
```bash
# Wszystkie logi
docker-compose logs -f

# Konkretny serwis
docker logs gra-ai_orchestrator-1 -f
docker logs gra-game_server-1 -f
```

### Admin Panel
- **URL**: http://localhost:8005
- **Funkcje**: Logi, raporty PDF, statystyki

### Health Checks
```bash
# Sprawdzenie statusu
curl http://localhost:8003/health  # AI Orchestrator
curl http://localhost:65432/health # Game Server
curl http://localhost:8004/health  # Vision Selector
```

## 🎯 Scenariusze Użycia

### 1. Single Player Investigation
```
1. Gracz łączy się z grą
2. Wprowadza akcję: "Przesłuchuję świadka w barze"
3. AI generuje scenę noir z dialogiem
4. System wybiera odpowiednie ujęcie filmowe
5. Generuje obraz w stylu noir
6. Odtwarza TTS narrację
7. Aktualizuje Case Board z nowymi węzłami
8. Bot automatycznie zamyka turę
```

### 2. Multiplayer Collaboration
```
1. Dwóch graczy łączy się z tą samą sesją
2. Gracz A: "Przeszukuję biuro podejrzanego"
3. Gracz B: "Sprawdzam alibi świadka"
4. System synchronizuje stan gry
5. Oba akcje wpływają na wspólny Case Board
6. Gracze widzą postęp w czasie rzeczywistym
```

### 3. Case Resolution
```
1. Gracz gromadzi dowody przez kilka tur
2. Łączy węzły na Case Board
3. Kliknie "Oskarż" i wybiera podejrzanego
4. AI generuje epilog i werdykt
5. System odtwarza SFX (gavel/heartbeat)
6. Wyświetla modal z zakończeniem
```

## 🔧 Development

### Struktura Projektu
```
gra/
├── services/           # Backend microservices
│   ├── ai_orchestrator/    # AI coordination
│   ├── game_server/        # Game logic
│   ├── supervisor_service/ # Input validation
│   ├── vision_selector/    # Image matching
│   ├── tts_service/        # Text-to-speech
│   ├── image_gen/          # Image generation
│   └── admin_service/      # Administration
├── web_client/         # React frontend
├── tests/              # Backend tests
├── config/             # Configuration files
├── data/               # Assets (images, audio, etc.)
├── tools/              # Utility scripts
└── docs/               # Documentation
```

### Dodawanie Nowych Funkcji

#### 1. Nowy Serwis
```bash
# Utwórz katalog serwisu
mkdir services/new_service
cd services/new_service

# Dockerfile
FROM python:3.12-slim
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

#### 2. Nowy Endpoint
```python
# services/ai_orchestrator/orchestrator.py
@app.post("/new_endpoint")
async def new_endpoint(req: NewReq):
    # Implementacja
    return {"result": "success"}
```

#### 3. Nowy Test
```python
# tests/test_new_feature.py
@pytest.mark.asyncio
async def test_new_feature():
    # Test logic
    assert result == expected
```

### Code Style
- **Python**: Black formatter, type hints
- **TypeScript**: ESLint, Prettier
- **Commits**: Conventional commits
- **Documentation**: Inline comments, README updates

## 📈 Performance

### Optymalizacje
- **Redis Caching** - TTS, images, embeddings
- **Async Operations** - Non-blocking I/O
- **Connection Pooling** - HTTP client reuse
- **Image Compression** - Optimized file sizes
- **Lazy Loading** - On-demand resource loading

### Monitoring
- **Response Times** - API endpoint monitoring
- **Memory Usage** - Container resource tracking
- **Error Rates** - Exception monitoring
- **User Metrics** - Gameplay analytics

## 🔒 Bezpieczeństwo

### Measures
- **Input Validation** - Pydantic schemas
- **Rate Limiting** - Request throttling
- **CORS** - Cross-origin protection
- **Environment Variables** - Secret management
- **Container Isolation** - Docker security

### API Keys
- **ElevenLabs** - TTS service
- **Google Cloud** - Image generation
- **OpenAI** - LLM (optional)
- **Banana.dev** - Alternative image generation

## 🤝 Contributing

### Workflow
1. Fork repository
2. Create feature branch
3. Implement changes
4. Add tests
5. Update documentation
6. Submit pull request

### Guidelines
- **Test Coverage** - Maintain >80%
- **Documentation** - Update README/docs
- **Backward Compatibility** - Don't break existing features
- **Performance** - Consider impact on response times

## 📝 License

MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

- **Stable Diffusion** - Image generation
- **ElevenLabs** - Text-to-speech
- **Google Vertex AI** - Cloud image generation
- **OpenAI** - Language models
- **React/Vite** - Frontend framework
- **FastAPI** - Backend framework

## 📞 Support

- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions
- **Documentation**: `/docs` folder
- **Examples**: `/examples` folder

---

**🕵️ "W mroku miasta, prawda czeka na tych, którzy mają odwagę jej szukać."**
