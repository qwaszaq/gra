# Client CLI

Interactive command-line client for the detective game.

## Features

- WebSocket connection to Game Server
- Text-based action input
- Asynchronous audio playback (WAV files)
- Optional image opening in browser
- Real-time narrative updates

## Installation

```bash
# Create virtual environment
python3 -m venv client_env
source client_env/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

```bash
# Activate virtual environment
source client_env/bin/activate

# Run client
python3 client.py
```

## Environment Variables

- `WS_URL`: WebSocket server URL (default: `ws://localhost:65432/ws`)
- `OPEN_IMAGES`: Open images in browser (default: `0`, set to `1` to enable)

## Example Session

```
Kryptonim: DetektywA
Session ID (np. demo-1): demo-1
WS URL [ws://localhost:65432/ws]: 
Łączenie z ws://localhost:65432/ws ...
Zalogowano. Wpisuj akcje pełnym zdaniem (np. 'Przesłuchuję świadka').

Twoja akcja: Przesłuchuję świadka
Info: Akcja przyjęta. Czekamy na drugiego gracza.

[Turn 1] Narrator: Deszcz pada nad miastem. Dwóch detektywów stoi przed opuszczonym budynkiem. To miejsce zbrodni.
[Obraz] http://localhost:8004/assets/images/case_zero/turn1.png
[Audio] http://localhost:8001/audio/demo-1_1_abc123.mp3 (playing in background)
```

## Game Flow

1. **Login**: Enter player name and session ID
2. **Actions**: Type full sentences describing your actions
3. **Validation**: Supervisor service validates and maps actions
4. **Turn Completion**: Game proceeds when both players act
5. **Narrative**: Receive story updates with images and audio
6. **Logging**: All actions are logged to Admin service

## Supported Actions

- **Investigate**: "Sprawdzam miejsce zbrodni", "Badam nóż"
- **Interrogate**: "Przesłuchuję świadka", "Pytam komendanta"
- **Move**: "Idę na posterunek", "Wracam do komisariatu"
- **Report**: "Raportuję znaleziska", "Zgłaszam meldunek"

## Audio Support

- Supports WAV files for playback
- Non-blocking audio playback
- Automatic download and temporary file management
- Graceful fallback for unsupported formats
