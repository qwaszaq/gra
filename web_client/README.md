# Web Client - Partnerzy w Zbrodni

Lekki frontend SPA dla gry "Partnerzy w Zbrodni" z WebSocket, audio i noir UI.

## Funkcje

- 🌐 **WebSocket Connection**: Łączy się z Game Serverem przez WebSocket
- 🎭 **Noir UI**: Ciemny, stylowy interfejs w klimacie noir
- 🎵 **Audio Support**: Odtwarzanie głosu narratora (WAV/MP3) i muzyki w tle
- 🖼️ **Image Display**: Wyświetlanie obrazów scen
- 📝 **Real-time Updates**: Otrzymywanie narrative_update i override_update
- 🔄 **Live Override**: Obsługa override_update z Admin UI

## Uruchomienie (Development)

1. Upewnij się, że serwisy back-endowe działają:
   ```bash
   docker-compose up -d
   ```

2. Zainstaluj zależności:
   ```bash
   cd web_client
   npm install
   ```

3. Uruchom serwer deweloperski:
   ```bash
   npm run dev
   ```

4. Otwórz http://localhost:5173 w przeglądarce

## Konfiguracja

### Zmienne środowiskowe (.env.development)

```env
VITE_WS_URL=ws://localhost:65432/ws
VITE_TITLE=Partnerzy w Zbrodni – Web
```

### Połączenie z grą

1. **WS URL**: `ws://localhost:65432/ws` (domyślnie)
2. **Kryptonim**: Nazwa gracza (np. "Marlow", "Spade")
3. **Session ID**: ID sesji (np. "demo-1")
4. Kliknij **"Połącz"**

## Użytkowanie

### Podstawowy flow gry

1. **Logowanie**: Wpisz kryptonim i session ID, kliknij "Połącz"
2. **Akcja**: Wpisz swoją akcję (np. "Przesłuchuję świadka")
3. **Narracja**: Po wysłaniu akcji przez dwóch graczy otrzymasz narrative_update
4. **Media**: Zobaczysz obraz, usłyszysz głos narratora i muzykę

### Audio Controls

- ☑️ **Głos narratora**: Włącz/wyłącz odtwarzanie głosu
- ☑️ **Muzyka**: Włącz/wyłącz muzykę w tle

### Live Override

Administrator może wysłać override_update, które natychmiast zaktualizuje:
- Tekst narracji
- Obraz sceny
- Głos narratora
- Muzykę w tle

## Struktura projektu

```
web_client/
├── src/
│   ├── App.tsx          # Główny komponent aplikacji
│   ├── useWebSocket.ts  # Hook do obsługi WebSocket
│   ├── types.ts         # Definicje typów TypeScript
│   ├── main.tsx         # Punkt wejścia React
│   └── styles.css       # Stylowanie noir
├── index.html           # HTML template
├── vite.config.ts       # Konfiguracja Vite
├── package.json         # Zależności npm
└── Dockerfile          # Build dla produkcji
```

## Build dla produkcji

```bash
npm run build
```

Pliki zostaną zbudowane do katalogu `dist/`.

### Docker

```bash
docker build -t web-client .
docker run -p 80:80 web-client
```

## Technologie

- **React 18**: UI framework
- **TypeScript**: Type safety
- **Vite**: Build tool i dev server
- **WebSocket**: Real-time communication
- **HTML5 Audio**: Odtwarzanie dźwięku

## Troubleshooting

### CORS Issues

Upewnij się, że w `.env` serwerów jest ustawione:
```env
WEB_CLIENT_ORIGIN=http://localhost:5173
```

### WebSocket Connection Failed

1. Sprawdź czy Game Server działa na porcie 65432
2. Sprawdź czy URL WebSocket jest poprawny
3. Sprawdź logi Game Servera

### Audio Not Playing

1. Sprawdź czy TTS Gateway działa na porcie 8001
2. Sprawdź czy URL audio jest dostępny
3. Sprawdź czy przeglądarka pozwala na autoplay audio

## Development Notes

- WebSocket nie podlega CORS, ale HTTP media (audio, image) tak
- `<audio>` i `<img>` zwykle nie wymagają CORS do odtwarzania/wyświetlenia
- ElevenLabs (MP3) działa out-of-the-box z `<audio>`
- Dla produkcji ustaw `VITE_WS_URL` na publiczny adres WebSocket
