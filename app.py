import re
from flask import Flask, render_template, request
import requests

app = Flask(__name__)

CLOUD_COVER = {
    'CLR': 'Clear skies',
    'SKC': 'Clear skies',
    'NSC': 'No significant clouds',
    'NCD': 'No clouds detected',
    'CAVOK': 'Clear skies, excellent visibility',
    'FEW': 'A few clouds',
    'SCT': 'Scattered clouds',
    'BKN': 'Mostly cloudy',
    'OVC': 'Overcast',
    'VV':  'Sky obscured (vertical visibility)',
}

WEATHER_CODES = {
    'DZ': 'drizzle', 'RA': 'rain', 'SN': 'snow', 'SG': 'snow grains',
    'IC': 'ice crystals', 'PL': 'ice pellets', 'GR': 'hail', 'GS': 'small hail',
    'UP': 'unknown precipitation', 'BR': 'mist', 'FG': 'fog', 'FU': 'smoke',
    'VA': 'volcanic ash', 'DU': 'dust', 'SA': 'sand', 'HZ': 'haze',
    'PO': 'dust devils', 'SQ': 'squall', 'FC': 'funnel cloud/tornado',
    'SS': 'sandstorm', 'DS': 'dust storm',
}

DESCRIPTOR_CODES = {
    'MI': 'shallow', 'PR': 'partial', 'BC': 'patches of', 'DR': 'low drifting',
    'BL': 'blowing', 'SH': 'showers', 'TS': 'thunderstorm with', 'FZ': 'freezing',
}


def degrees_to_compass(degrees):
    if degrees is None:
        return 'variable'
    dirs = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
            'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
    return dirs[round(degrees / 22.5) % 16]


def c_to_f(c):
    return round(c * 9 / 5 + 32) if c is not None else None


def knots_to_mph(kt):
    return round(kt * 1.15078) if kt is not None else None


def parse_wx_string(wx_string):
    """Convert a wxString like '-RA BR' into plain English phrases."""
    if not wx_string:
        return []

    results = []
    for token in wx_string.split():
        m = re.match(
            r'^(-|\+|VC)?'
            r'(MI|PR|BC|DR|BL|SH|TS|FZ)?'
            r'(DZ|RA|SN|SG|IC|PL|GR|GS|UP)?'
            r'(BR|FG|FU|VA|DU|SA|HZ|PY)?'
            r'(PO|SQ|FC|SS|DS)?$',
            token
        )
        if not m or not any(m.groups()):
            continue

        intensity, descriptor, precip, obscuration, other = m.groups()
        parts = []

        if intensity == '-':
            parts.append('light')
        elif intensity == '+':
            parts.append('heavy')
        elif intensity == 'VC':
            parts.append('nearby')

        if descriptor:
            parts.append(DESCRIPTOR_CODES.get(descriptor, descriptor.lower()))
        if precip:
            parts.append(WEATHER_CODES.get(precip, precip.lower()))
        if obscuration:
            parts.append(WEATHER_CODES.get(obscuration, obscuration.lower()))
        if other:
            parts.append(WEATHER_CODES.get(other, other.lower()))

        if parts:
            results.append(' '.join(parts))

    return results


def build_summary(m):
    """Produce a list of plain-English sentences from a METAR JSON record."""
    sentences = []
    clouds = m.get('clouds', []) or []
    wx_string = m.get('wxString') or ''

    # --- sky conditions ---
    clear_covers = {'CLR', 'SKC', 'NSC', 'NCD', 'CAVOK'}
    if clouds:
        if any(c.get('cover') in clear_covers for c in clouds):
            sentences.append('Skies are clear.')
        else:
            parts = []
            for layer in clouds:
                cover = layer.get('cover', '')
                base = layer.get('base')
                label = CLOUD_COVER.get(cover, cover)
                cb = layer.get('cbmam', '')
                if cb == 'CB':
                    label += ' (cumulonimbus/thunderstorm clouds)'
                elif cb == 'TCU':
                    label += ' (towering cumulus)'
                if base:
                    parts.append(f'{label} at {base:,} ft')
                else:
                    parts.append(label)
            sentences.append('. '.join(parts) + '.')

    # --- temperature ---
    temp_c = m.get('temp')
    dew_c = m.get('dewp')
    if temp_c is not None:
        line = f'Temperature is {c_to_f(temp_c)}°F ({temp_c}°C)'
        if dew_c is not None:
            line += f', dewpoint {c_to_f(dew_c)}°F ({dew_c}°C)'
        sentences.append(line + '.')

    # --- wind ---
    wspd = m.get('wspd')
    wdir = m.get('wdir')
    wgst = m.get('wgst')
    if wspd is not None:
        mph = knots_to_mph(wspd)
        if wspd == 0:
            sentences.append('Winds are calm.')
        elif wdir == 0 or wdir is None:
            sentences.append(f'Winds are variable at {mph} mph ({wspd} kt).')
        else:
            compass = degrees_to_compass(wdir)
            line = f'Winds from the {compass} ({wdir}°) at {mph} mph ({wspd} kt)'
            if wgst:
                line += f', gusting to {knots_to_mph(wgst)} mph ({wgst} kt)'
            sentences.append(line + '.')

    # --- visibility ---
    visib = m.get('visib')
    if visib is not None:
        try:
            vis_val = float(str(visib).replace('+', ''))
            is_plus = str(visib).endswith('+')
            if is_plus or vis_val >= 10:
                sentences.append('Visibility is 10 miles or more.')
            elif vis_val >= 3:
                sentences.append(f'Visibility is {vis_val:g} miles.')
            elif vis_val >= 1:
                sentences.append(f'Visibility is {vis_val:g} miles (reduced).')
            else:
                sentences.append(f'Visibility is very poor at {vis_val:g} miles.')
        except (ValueError, TypeError):
            pass

    # --- weather phenomena ---
    phenomena = parse_wx_string(wx_string)
    if phenomena:
        sentences.append(f'Current weather: {", ".join(phenomena)}.')

    # --- altimeter ---
    altim = m.get('altim')
    if altim is not None:
        inhg = altim * 0.02953
        sentences.append(f'Barometric pressure is {inhg:.2f} inHg ({altim:.1f} hPa).')

    return sentences


def weather_icon(m):
    wx = (m.get('wxString') or '').upper()
    clouds = [c.get('cover', '') for c in (m.get('clouds') or [])]

    if 'TS' in wx:
        return '⛈️'
    if any(c in wx for c in ('SN', 'SG', 'IC', 'PL')):
        return '❄️'
    if any(c in wx for c in ('RA', 'DZ')):
        return '🌧️'
    if 'FG' in wx or 'BR' in wx:
        return '🌫️'
    if 'HZ' in wx or 'FU' in wx or 'DU' in wx or 'SA' in wx:
        return '😶‍🌫️'

    clear = {'CLR', 'SKC', 'NSC', 'NCD', 'CAVOK'}
    if any(c in clear for c in clouds):
        return '☀️'
    if 'OVC' in clouds:
        return '☁️'
    if 'BKN' in clouds:
        return '🌥️'
    if clouds:
        return '⛅'
    return '🌤️'


@app.route('/', methods=['GET', 'POST'])
def index():
    weather = None
    error = None
    airport = ''

    if request.method == 'POST':
        airport = request.form.get('airport', '').strip().upper()
        if not airport:
            error = 'Please enter an airport code.'
        else:
            try:
                url = f'https://aviationweather.gov/api/data/metar?ids={airport}&format=json'
                resp = requests.get(url, timeout=10)
                resp.raise_for_status()
                try:
                    data = resp.json()
                except ValueError:
                    data = []

                if not data:
                    error = (
                        f"No METAR data found for \"{airport}\". "
                        "Double-check the ICAO code (e.g. KIAD, KJFK, EGLL)."
                    )
                else:
                    m = data[0]
                    weather = {
                        'station':     m.get('icaoId', airport),
                        'name':        m.get('name', ''),
                        'report_time': m.get('reportTime', ''),
                        'raw':         m.get('rawOb', ''),
                        'icon':        weather_icon(m),
                        'temp_f':      c_to_f(m.get('temp')),
                        'temp_c':      m.get('temp'),
                        'wind_mph':    knots_to_mph(m.get('wspd')),
                        'wind_dir':    degrees_to_compass(m.get('wdir')),
                        'visib':       m.get('visib'),
                        'summary':     build_summary(m),
                    }
            except requests.exceptions.Timeout:
                error = 'Request timed out. The weather service may be slow — try again.'
            except requests.exceptions.ConnectionError:
                error = 'Could not connect to the weather service. Check your internet connection.'
            except requests.exceptions.HTTPError as exc:
                error = f'Weather service error: {exc}'
            except Exception as exc:
                error = f'Unexpected error: {exc}'

    return render_template('index.html', weather=weather, error=error, airport=airport)


if __name__ == '__main__':
    app.run(debug=True)
