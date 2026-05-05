# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the app

```bash
pip install -r requirements.txt
python app.py
# Open http://127.0.0.1:5000
```

## Architecture

Single-file Flask app (`app.py`) with one Jinja2 template (`templates/index.html`).

- **Route `POST /`** — receives a 4-letter ICAO airport code, calls the Aviation Weather Center JSON API, decodes the result, and re-renders the same template with the decoded weather.
- **API** — `https://aviationweather.gov/api/data/metar?ids={CODE}&format=json` returns a JSON array; element `[0]` contains the observation. Key fields: `temp`/`dewp` (°C), `wspd`/`wdir`/`wgst` (knots/degrees), `visib` (statute miles, may end with `+`), `altim` (**hPa**, not inHg — convert with `× 0.02953`), `wxString` (raw phenomenon codes), `clouds` (list of `{cover, base}` dicts), `rawOb` (original METAR string).
- **`build_summary(m)`** — converts the JSON record into a list of plain-English sentences shown as bullet points.
- **`parse_wx_string(wx_string)`** — tokenizes a wxString like `-RA BR` using the METAR phenomenon code tables (`WEATHER_CODES`, `DESCRIPTOR_CODES`) and returns human-readable phrases.
- **`weather_icon(m)`** — picks an emoji from the wx/cloud conditions.
- The template is self-contained (inline CSS, no JS frameworks). The raw METAR is shown inside a `<details>` element.
