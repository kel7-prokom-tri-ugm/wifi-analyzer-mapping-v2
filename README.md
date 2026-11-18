# WiFi-Radar ID 📡

**Public Wi-Fi Intelligence** – a Streamlit dashboard that measures the quality (speed, ping, jitter, throttling) and security (DNS-over-HTTPS consistency, HTTPS/TLS, captive portal) of public Wi-Fi directly from the user's browser, gives AI recommendations, and shares results on a community map.

Project Prokom Kelompok 7.

## Features

- **Overview (4-stage flow):**
  1. **Test-first landing:** clean start button (*Mulai Test Wi-Fi*) plus temporary Simulation mode for demos.
  2. **Live browser measurement:** real-time animated Download & Upload speedometer powered by Cloudflare (`speed.cloudflare.com`), showing live Ping, Jitter, Test Server, and ISP.
  3. **Full analysis:** Network Score, QoS metrics, Net Neutrality check, automated browser security audit, and AI Advisor summary.
  4. **Smart upload confirmation:** auto-fills coordinates from GPS or metadata, matches nearby existing locations to prevent duplicates, auto-fills name/area via OpenStreetMap reverse geocoding, and supports map pin picking (SSID is optional; raw IP is never stored).
- **Community Map:** interactive map with color-coded pins (green = Aman, yellow = Rawan, red = Bahaya). Hovering shows Download, Upload, and AI suitability; clicking a pin or using **Lihat Detail** shows the full breakdown and location scan history.
- **Scan History:** filterable table including ISP and Test Server columns with CSV export.

## Project structure

```
app.py                         # Streamlit UI (entry point)
components/speedtest/
  index.html                   # Client-side Cloudflare speedtest & probe component
modules/
  database.py                  # SQLite: schema, migration, seed data, save/read logs
  network_scanner.py           # Browser payload adapter, QoS scoring, simulation & CLI
  security_test.py             # Browser & local security scoring
  ai_advisor.py                # Gemini summary + rule-based fallback
  location.py                  # OpenStreetMap Nominatim search, reverse geocode, proximity
  visualizer.py                # UI cards, PyDeck map, Altair chart, history table
data/seed_data.json            # Initial location and security-rule data
.streamlit/config.toml         # Dark theme
.streamlit/secrets.toml.example
```

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt
python -m streamlit run app.py
```

The database `data/wifi_radar.db` is created (and automatically migrated if older) on first run from `data/seed_data.json`.

### AI Advisor (optional)

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill in `GEMINI_API_KEY`. Without a key, the AI Advisor uses its rule-based mode automatically.

## Notes

- Live tests run **client-side in the user's browser** against Cloudflare endpoints so deployed cloud instances measure the visitor's connection rather than the server's connection.
- Raw user IP addresses are stripped in the browser and **never stored** in SQLite.
- Browser security checks evaluate HTTPS context and DNS-over-HTTPS consistency (browsers cannot inspect Wi-Fi router WPA2/Open encryption directly unless running locally on Windows).
