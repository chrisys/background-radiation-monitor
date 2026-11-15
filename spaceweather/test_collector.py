import unittest

from collector import forecast_status, normalize_rows, parse_kp


class SpaceWeatherParsingTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
