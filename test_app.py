"""Unit tests for the METAR weather decoder app."""

import pytest
from unittest.mock import patch, MagicMock
import requests

from app import (
    app as flask_app,
    degrees_to_compass,
    c_to_f,
    knots_to_mph,
    parse_wx_string,
    build_summary,
    weather_icon,
)

# ── Mock METAR records ─────────────────────────────────────────────────────────
# These dicts mirror the structure returned by the Aviation Weather Center API.

CLEAR_DAY = {
    'icaoId': 'KIAD', 'name': 'Washington Dulles', 'reportTime': '2024-01-15 14:00:00',
    'rawOb': 'KIAD 151400Z 27015KT 10SM CLR 22/08 A2992',
    'temp': 22, 'dewp': 8, 'wspd': 15, 'wdir': 270, 'wgst': None,
    'visib': '10+', 'wxString': None,
    'clouds': [{'cover': 'CLR', 'base': None}],
    'altim': 1013.2,
}

STORMY = {
    'icaoId': 'KJFK', 'name': 'New York JFK', 'reportTime': '2024-01-15 18:00:00',
    'rawOb': 'KJFK 151800Z 18025G40KT 1/2SM +TSRA OVC008CB 18/17 A2950',
    'temp': 18, 'dewp': 17, 'wspd': 25, 'wdir': 180, 'wgst': 40,
    'visib': 0.5, 'wxString': '+TSRA',
    'clouds': [{'cover': 'OVC', 'base': 800, 'cbmam': 'CB'}],
    'altim': 998.6,
}

FOGGY = {
    'icaoId': 'KSFO', 'name': 'San Francisco Intl', 'reportTime': '2024-01-15 06:00:00',
    'rawOb': 'KSFO 150600Z 00000KT 1/4SM FG OVC002 14/13 A3005',
    'temp': 14, 'dewp': 13, 'wspd': 0, 'wdir': 0, 'wgst': None,
    'visib': 0.25, 'wxString': 'FG',
    'clouds': [{'cover': 'OVC', 'base': 200}],
    'altim': 1017.5,
}

SNOWY = {
    'icaoId': 'KDEN', 'name': 'Denver Intl', 'reportTime': '2024-01-15 12:00:00',
    'rawOb': 'KDEN 151200Z 32020KT 2SM -SN BKN015 OVC030 M05/M10 A2980',
    'temp': -5, 'dewp': -10, 'wspd': 20, 'wdir': 320, 'wgst': None,
    'visib': 2, 'wxString': '-SN',
    'clouds': [{'cover': 'BKN', 'base': 1500}, {'cover': 'OVC', 'base': 3000}],
    'altim': 1009.5,
}

VARIABLE_WINDS = {
    'icaoId': 'KBOS', 'name': 'Boston Logan', 'reportTime': '2024-01-15 09:00:00',
    'rawOb': 'KBOS 150900Z VRB05KT 10SM SCT025 20/15 A3010',
    'temp': 20, 'dewp': 15, 'wspd': 5, 'wdir': 0, 'wgst': None,
    'visib': '10+', 'wxString': None,
    'clouds': [{'cover': 'SCT', 'base': 2500}],
    'altim': 1019.4,
}

WINDY_GUSTY = {
    'icaoId': 'KORD', 'name': 'Chicago O\'Hare', 'reportTime': '2024-01-15 15:00:00',
    'rawOb': 'KORD 151500Z 29030G50KT 10SM FEW050 10/2 A2975',
    'temp': 10, 'dewp': 2, 'wspd': 30, 'wdir': 290, 'wgst': 50,
    'visib': '10+', 'wxString': None,
    'clouds': [{'cover': 'FEW', 'base': 5000}],
    'altim': 1007.8,
}


# ── Flask test client fixture ──────────────────────────────────────────────────

@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as c:
        yield c


# ── degrees_to_compass ─────────────────────────────────────────────────────────

class TestDegreesToCompass:
    def test_cardinal_north(self):
        assert degrees_to_compass(0) == 'N'

    def test_cardinal_east(self):
        assert degrees_to_compass(90) == 'E'

    def test_cardinal_south(self):
        assert degrees_to_compass(180) == 'S'

    def test_cardinal_west(self):
        assert degrees_to_compass(270) == 'W'

    def test_northeast(self):
        assert degrees_to_compass(45) == 'NE'

    def test_northwest(self):
        assert degrees_to_compass(315) == 'NW'

    def test_360_wraps_to_north(self):
        assert degrees_to_compass(360) == 'N'

    def test_none_returns_variable(self):
        assert degrees_to_compass(None) == 'variable'


# ── c_to_f ────────────────────────────────────────────────────────────────────

class TestCToF:
    def test_freezing_point(self):
        assert c_to_f(0) == 32

    def test_boiling_point(self):
        assert c_to_f(100) == 212

    def test_negative_forty_is_same(self):
        assert c_to_f(-40) == -40

    def test_body_temp(self):
        assert c_to_f(37) == 99

    def test_none_returns_none(self):
        assert c_to_f(None) is None


# ── knots_to_mph ──────────────────────────────────────────────────────────────

class TestKnotsToMph:
    def test_zero(self):
        assert knots_to_mph(0) == 0

    def test_ten_knots(self):
        assert knots_to_mph(10) == 12

    def test_hundred_knots(self):
        assert knots_to_mph(100) == 115

    def test_none_returns_none(self):
        assert knots_to_mph(None) is None


# ── parse_wx_string ───────────────────────────────────────────────────────────

class TestParseWxString:
    def test_empty_string(self):
        assert parse_wx_string('') == []

    def test_none(self):
        assert parse_wx_string(None) == []

    def test_light_rain(self):
        assert parse_wx_string('-RA') == ['light rain']

    def test_heavy_rain(self):
        assert parse_wx_string('+RA') == ['heavy rain']

    def test_light_snow(self):
        assert parse_wx_string('-SN') == ['light snow']

    def test_thunderstorm_with_heavy_rain(self):
        assert parse_wx_string('+TSRA') == ['heavy thunderstorm with rain']

    def test_freezing_rain(self):
        assert parse_wx_string('FZRA') == ['freezing rain']

    def test_blowing_snow(self):
        assert parse_wx_string('BLSN') == ['blowing snow']

    def test_mist(self):
        assert parse_wx_string('BR') == ['mist']

    def test_fog(self):
        assert parse_wx_string('FG') == ['fog']

    def test_nearby_fog(self):
        assert parse_wx_string('VCFG') == ['nearby fog']

    def test_multiple_tokens(self):
        result = parse_wx_string('-RA BR')
        assert result == ['light rain', 'mist']

    def test_shower_snow(self):
        assert parse_wx_string('SHSN') == ['showers snow']

    def test_haze(self):
        assert parse_wx_string('HZ') == ['haze']

    def test_unknown_token_is_skipped(self):
        assert parse_wx_string('ZZZZ') == []


# ── build_summary ─────────────────────────────────────────────────────────────

class TestBuildSummary:
    def test_clear_day_has_clear_skies(self):
        result = build_summary(CLEAR_DAY)
        assert 'Skies are clear.' in result

    def test_clear_day_temperature(self):
        result = build_summary(CLEAR_DAY)
        assert any('72°F' in s and '22°C' in s for s in result)

    def test_clear_day_dewpoint(self):
        result = build_summary(CLEAR_DAY)
        assert any('dewpoint' in s for s in result)

    def test_clear_day_wind_direction(self):
        result = build_summary(CLEAR_DAY)
        assert any('W (270°)' in s for s in result)

    def test_clear_day_visibility_ten_plus(self):
        result = build_summary(CLEAR_DAY)
        assert 'Visibility is 10 miles or more.' in result

    def test_clear_day_altimeter(self):
        result = build_summary(CLEAR_DAY)
        assert any('inHg' in s and 'hPa' in s for s in result)

    def test_stormy_thunderstorm_clouds(self):
        result = build_summary(STORMY)
        assert any('cumulonimbus' in s for s in result)

    def test_stormy_gusts(self):
        result = build_summary(STORMY)
        assert any('gusting' in s for s in result)

    def test_stormy_weather_phenomena(self):
        result = build_summary(STORMY)
        assert any('thunderstorm' in s for s in result)

    def test_stormy_very_poor_visibility(self):
        result = build_summary(STORMY)
        assert any('very poor' in s for s in result)

    def test_foggy_calm_winds(self):
        result = build_summary(FOGGY)
        assert 'Winds are calm.' in result

    def test_foggy_very_poor_visibility(self):
        result = build_summary(FOGGY)
        assert any('very poor' in s for s in result)

    def test_foggy_phenomena_includes_fog(self):
        result = build_summary(FOGGY)
        assert any('fog' in s for s in result)

    def test_snowy_multiple_cloud_layers(self):
        result = build_summary(SNOWY)
        cloud_sentence = next(s for s in result if 'ft' in s)
        assert '1,500 ft' in cloud_sentence
        assert '3,000 ft' in cloud_sentence

    def test_snowy_reduced_visibility(self):
        result = build_summary(SNOWY)
        assert any('reduced' in s for s in result)

    def test_snowy_light_snow_phenomenon(self):
        result = build_summary(SNOWY)
        assert any('light snow' in s for s in result)

    def test_variable_winds(self):
        result = build_summary(VARIABLE_WINDS)
        assert any('variable' in s for s in result)

    def test_gusty_winds(self):
        result = build_summary(WINDY_GUSTY)
        assert any('gusting' in s for s in result)

    def test_missing_temp_no_crash(self):
        result = build_summary({'clouds': [], 'wxString': None})
        assert isinstance(result, list)


# ── weather_icon ──────────────────────────────────────────────────────────────

class TestWeatherIcon:
    def test_thunderstorm(self):
        assert weather_icon(STORMY) == '⛈️'

    def test_snow(self):
        assert weather_icon(SNOWY) == '❄️'

    def test_rain(self):
        m = {**CLEAR_DAY, 'wxString': 'RA', 'clouds': []}
        assert weather_icon(m) == '🌧️'

    def test_fog(self):
        assert weather_icon(FOGGY) == '🌫️'

    def test_haze(self):
        m = {**CLEAR_DAY, 'wxString': 'HZ', 'clouds': []}
        assert weather_icon(m) == '😶‍🌫️'

    def test_clear(self):
        assert weather_icon(CLEAR_DAY) == '☀️'

    def test_overcast(self):
        m = {**CLEAR_DAY, 'wxString': None, 'clouds': [{'cover': 'OVC'}]}
        assert weather_icon(m) == '☁️'

    def test_broken(self):
        m = {**CLEAR_DAY, 'wxString': None, 'clouds': [{'cover': 'BKN'}]}
        assert weather_icon(m) == '🌥️'

    def test_few_clouds(self):
        m = {**CLEAR_DAY, 'wxString': None, 'clouds': [{'cover': 'FEW'}]}
        assert weather_icon(m) == '⛅'

    def test_no_clouds_no_wx(self):
        m = {'wxString': None, 'clouds': []}
        assert weather_icon(m) == '🌤️'


# ── Flask route ───────────────────────────────────────────────────────────────

class TestIndexRoute:
    def test_get_returns_200(self, client):
        resp = client.get('/')
        assert resp.status_code == 200

    def test_post_empty_airport_shows_error(self, client):
        resp = client.post('/', data={'airport': ''})
        assert b'Please enter an airport code' in resp.data

    @patch('app.requests.get')
    def test_post_valid_airport_returns_weather(self, mock_get, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [CLEAR_DAY]
        mock_get.return_value = mock_resp

        resp = client.post('/', data={'airport': 'KIAD'})
        assert resp.status_code == 200
        assert b'Washington Dulles' in resp.data

    @patch('app.requests.get')
    def test_post_unknown_airport_shows_error(self, mock_get, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = []
        mock_get.return_value = mock_resp

        resp = client.post('/', data={'airport': 'ZZZZ'})
        assert b'No METAR data found' in resp.data

    @patch('app.requests.get', side_effect=requests.exceptions.Timeout)
    def test_post_timeout_shows_error(self, mock_get, client):
        resp = client.post('/', data={'airport': 'KIAD'})
        assert b'timed out' in resp.data

    @patch('app.requests.get', side_effect=requests.exceptions.ConnectionError)
    def test_post_connection_error_shows_error(self, mock_get, client):
        resp = client.post('/', data={'airport': 'KIAD'})
        assert b'connect' in resp.data

    def test_post_airport_code_uppercased(self, client):
        with patch('app.requests.get') as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = [CLEAR_DAY]
            mock_get.return_value = mock_resp

            client.post('/', data={'airport': 'kiad'})
            called_url = mock_get.call_args[0][0]
            assert 'KIAD' in called_url
