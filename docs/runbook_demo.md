# Partnerzy w Zbrodni — Szybki przelot (demo w 5 krokach)

Wymagania:
- uruchomiony Docker (docker-compose),
- (.opcjonalnie) lokalny SD (MPS) jeśli `IMAGE_PROVIDER=local` (Mac),
- WEB_CLIENT_ORIGIN ustawione na `http://localhost:5173`.

## Krok 1. Uruchom backendy
```bash
docker-compose up -d
```

Jeśli używasz lokalnego SD (Mac, IMAGE_PROVIDER=local):
```bash
uvicorn fastapi_mps_sd:app --host 0.0.0.0 --port 8501
```

## Krok 2. Zasiej demo asety (paczka pod pokaz)
Wszystko:
```bash
make demo-all
```

Albo selektywnie:
```bash
make demo-images       # obrazy z MPS (Mac)
make demo-tts          # próbki głosu narratora
make demo-music        # muzyka przez Orchestrator/Suno + cache
make demo-orchestrate  # pełna orchestracja (narracja+obraz+muzyka)
```

## Krok 3. Zautomatyzowane demo (bez klikania)
```bash
python tools/run_demo_automated.py
```

Skrypt zrobi:
- Single Player turę (bot automatycznie domyka),
- Multi Player turę (dwóch graczy),
- Admin override (live),
- Pobierze PDF raport do: `Runbook_Demo_Report.pdf`.

## Krok 4. Web Client (na żywo)
```bash
cd web_client
npm i
npm run dev
# otwórz:
http://localhost:5173
```

Pokaż galerię (Generated + Case Zero),
Zagraj 1 turę SP (single_player:true), sprawdź obraz i dźwięk (po pierwszym kliknięciu w UI audio gra).

## Krok 5. Panel Admina
```
http://localhost:8002
```

Podgląd logów; wygeneruj PDF (przycisk),
Zrób Override (1‑klik) → natychmiast zobaczysz [OVERRIDE] u klienta.

## Szybka checklista (powinno być OK)
- Vision: `http://localhost:8004/list?collection=generated` → lista > 0.
- Single Player: jedna akcja → bot domyka turę w < 5 s (narracja + obraz + audio).
- Multi Player: dwie akcje → obaj klienci mają narrative_update (tekst + media).
- Admin: PDF 200/OK, Override działa (live broadcast).
- Web: brak CORS (WEB_CLIENT_ORIGIN=http://localhost:5173), audio gra po pierwszej interakcji.

## Diagnostyka
- **Brak obrazu (IMAGE_PROVIDER=local)**: uruchom fastapi_mps_sd (8501); na Linux dodaj extra_hosts: host.docker.internal:host-gateway w ai_orchestrator.
- **Pusty Generated**: `make demo-images` lub `make demo-orchestrate`; sprawdź `/list?collection=generated`.
- **CORS**: ustaw WEB_CLIENT_ORIGIN we wszystkich serwisach + restart compose.
- **Audio**: kliknij w UI (autoplay policy).
- **LLM/Suno**: bez kluczy → fallback (deterministyczne narracje / track_X.mp3); z kluczami → ustaw je w .env i zrób docker-compose up -d.
