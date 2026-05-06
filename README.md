# metarrepo
Creating generic Weather tracking App

A Flask web app that fetches live METAR observations from the [Aviation Weather Center](https://aviationweather.gov/) and presents them as plain-English bullet points alongside the raw METAR string.

Enter any ICAO airport code (e.g. `KIAD`, `KJFK`, `EGLL`) to get the current:

- Sky conditions and cloud layers
- Temperature and dewpoint (°F and °C)
- Wind speed, direction, and gusts
- Visibility
- Weather phenomena (rain, snow, fog, thunderstorms, etc.)
- Barometric pressure (inHg and hPa)

## Requirements

- Python 3.8+
- pip

## Installation

```bash
git clone https://github.com/your-username/metarrepo.git
cd metarrepo
pip install -r requirements.txt
```

## Running

```bash
python app.py
```

Then open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

## Docker

### Build and run

```bash
docker build -t metarrepo .
docker run -p 5000:5000 metarrepo
```

Then open [http://localhost:5000](http://localhost:5000) in your browser.

### Run a specific version

Tag your builds to make rollbacks easy:

```bash
docker build -t metarrepo:1.0 .
docker run -p 5000:5000 metarrepo:1.0
```

### Run in the background

```bash
docker run -d -p 5000:5000 --name metar metarrepo
docker logs metar        # view logs
docker stop metar        # stop the container
docker rm metar          # remove the container
```

### Docker Compose (optional)

Create a `docker-compose.yml` file:

```yaml
services:
  web:
    build: .
    ports:
      - "5000:5000"
    restart: unless-stopped
```

Then start with:

```bash
docker compose up -d
```

## Testing

Install dev dependencies (pytest is included in `requirements.txt`) and run:

```bash
python -m pytest test_app.py -v
```

The test suite has 68 tests covering:

| Class | What's tested |
|---|---|
| `TestDegreesToCompass` | Cardinal/intercardinal directions, 360° wrap, `None` → `'variable'` |
| `TestCToF` | Freezing, boiling, −40 crossover, body temp, `None` passthrough |
| `TestKnotsToMph` | Zero, 10 kt, 100 kt conversions, `None` passthrough |
| `TestParseWxString` | Intensity prefixes (`-`/`+`), descriptors (FZ, BL, SH), phenomena (rain, snow, fog, TS), multi-token strings, unknown tokens skipped |
| `TestBuildSummary` | Temperature/dewpoint, wind (calm/variable/gusty), visibility levels, altimeter, cloud layers (CLR→OVC, CB), missing fields don't crash |
| `TestWeatherIcon` | All 10 weather emojis (⛈️ 🌧️ ❄️ 🌫️ 😶‍🌫️ ☀️ ☁️ 🌥️ ⛅ 🌤️) |
| `TestIndexRoute` | GET 200, empty code validation, valid/unknown airport (mocked API), timeout/connection errors, lowercase code uppercased |

## Usage

Type a 4-letter ICAO airport code into the search box and press **Get Weather**. ICAO codes differ from the 3-letter FAA codes used in the US — prefix a `K` to most US airport identifiers (e.g. LAX → `KLAX`, JFK → `KJFK`). International examples: London Heathrow (`EGLL`), Tokyo Haneda (`RJTT`), Sydney (`YSSY`).

## Data source

Live METAR data is retrieved from the public Aviation Weather Center API:

```
https://aviationweather.gov/api/data/metar?ids={ICAO}&format=json
```

No API key is required.
