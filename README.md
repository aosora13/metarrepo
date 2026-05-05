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

## Usage

Type a 4-letter ICAO airport code into the search box and press **Get Weather**. ICAO codes differ from the 3-letter FAA codes used in the US — prefix a `K` to most US airport identifiers (e.g. LAX → `KLAX`, JFK → `KJFK`). International examples: London Heathrow (`EGLL`), Tokyo Haneda (`RJTT`), Sydney (`YSSY`).

## Data source

Live METAR data is retrieved from the public Aviation Weather Center API:

```
https://aviationweather.gov/api/data/metar?ids={ICAO}&format=json
```

No API key is required.
