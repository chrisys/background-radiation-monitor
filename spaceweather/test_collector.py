import unittest

from collector import (
    forecast_status,
    normalize_rows,
    parse_kp,
    proton_point,
    resolve_location,
    solar_wind_point,
    weather_point,
)


class ExternalContextParsingTests(unittest.TestCase):
    def test_normalize_current_object_format(self):
        payload = [{"time_tag": "2026-11-15T00:00:00", "Kp": 2.0}]
        self.assertEqual(normalize_rows(payload), payload)

    def test_normalize_legacy_table_format(self):
        payload = [
            ["time_tag", "Kp"],
            ["2026-11-15T00:00:00", "2.0"],
        ]
        rows = normalize_rows(payload)
        self.assertEqual(rows[0]["Kp"], "2.0")

    def test_parse_kp_accepts_upper_and_lowercase(self):
        self.assertEqual(parse_kp({"Kp": 3.33}), 3.33)
        self.assertEqual(parse_kp({"kp": 4.0}), 4.0)

    def test_parse_kp_rejects_out_of_range(self):
        with self.assertRaises(ValueError):
            parse_kp({"kp": 10})

    def test_forecast_status(self):
        self.assertEqual(
            forecast_status({"observed": "observed"}),
            "observed",
        )
        self.assertEqual(
            forecast_status({"observed": "estimated"}),
            "estimated",
        )
        self.assertEqual(
            forecast_status({"observed": "predicted"}),
            "predicted",
        )

    def test_solar_wind_parses_table_feeds(self):
        plasma = [
            ["time_tag", "density", "speed", "temperature"],
            ["2026-11-15 20:00:00.000", "5.0", "410.2", "90000"],
        ]
        magnetic = [
            ["time_tag", "bx_gsm", "by_gsm", "bz_gsm", "lon_gsm", "lat_gsm", "bt"],
            ["2026-11-15 20:00:00.000", "1", "2", "-3.5", "0", "0", "5.2"],
        ]
        self.assertIsNotNone(solar_wind_point(plasma, magnetic))

    def test_proton_selects_10_mev_channel(self):
        payload = [
            {
                "time_tag": "2026-11-15T20:00:00Z",
                "energy": ">=10 MeV",
                "flux": 1.25,
            }
        ]
        self.assertIsNotNone(proton_point(payload))

    def test_weather_point_accepts_current_payload(self):
        payload = {
            "current": {
                "time": "2026-11-15T20:00",
                "temperature_2m": 17.2,
                "relative_humidity_2m": 81,
                "surface_pressure": 1008.5,
                "precipitation": 0.1,
                "rain": 0.1,
            }
        }
        location = {
            "latitude": 38.7,
            "longitude": -9.1,
            "source": "ip",
            "city": "Example",
            "region": "",
            "country": "Example",
        }
        self.assertIsNotNone(weather_point(payload, location))


if __name__ == "__main__":
    unittest.main()
