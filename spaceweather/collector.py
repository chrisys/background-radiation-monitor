import datetime
import json
import os
import time
import urllib.request

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS


OBSERVED_URL = os.getenv(
    "NOAA_KP_OBSERVED_URL",
    "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json",
)
FORECAST_URL = os.getenv(
    "NOAA_KP_FORECAST_URL",
    "https://services.swpc.noaa.gov/products/noaa-planetary-k-index-forecast.json",
)
FETCH_INTERVAL_SECONDS = max(
    60,
    int(os.getenv("NOAA_FETCH_INTERVAL_SECONDS", "300")),
)
HTTP_TIMEOUT_SECONDS = max(
    5,
    int(os.getenv("NOAA_HTTP_TIMEOUT_SECONDS", "20")),
)

INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_ORG = os.getenv("INFLUX_ORG", "balena")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "balena-sense")


def normalize_rows(payload):
    if not isinstance(payload, list):
        raise ValueError("NOAA payload must be a JSON array")

    if not payload:
        return []

    if isinstance(payload[0], dict):
        return payload

    if isinstance(payload[0], list):
        header = payload[0]
        return [
            dict(zip(header, values))
            for values in payload[1:]
            if isinstance(values, list)
        ]

    raise ValueError("Unsupported NOAA JSON format")


def parse_timestamp(value):
    if not value:
        raise ValueError("Missing NOAA time_tag")

    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    parsed = datetime.datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.timezone.utc)

    return parsed.astimezone(datetime.timezone.utc)


def parse_kp(row):
    raw = row.get("Kp", row.get("kp"))
    if raw is None:
        raise ValueError("Missing Kp value")

    kp = float(raw)
    if kp < 0.0 or kp > 9.0:
        raise ValueError(f"Kp out of range: {kp}")

    return kp


def forecast_status(row):
    raw = (
        row.get("observed")
        or row.get("status")
        or row.get("type")
        or "predicted"
    )
    text = str(raw).strip().lower()

    aliases = {
        "observation": "observed",
        "observation/estimated": "estimated",
        "estimate": "estimated",
        "forecast": "predicted",
        "prediction": "predicted",
    }
    text = aliases.get(text, text)

    if text not in ("observed", "estimated", "predicted"):
        return "predicted"

    return text


def fetch_json(url):
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "background-radiation-monitor/1.9.0",
        },
    )
    with urllib.request.urlopen(
        request,
        timeout=HTTP_TIMEOUT_SECONDS,
    ) as response:
        return json.load(response)


def observed_points(payload):
    points = []
    for row in normalize_rows(payload):
        try:
            timestamp = parse_timestamp(row.get("time_tag"))
            kp = parse_kp(row)
        except (TypeError, ValueError):
            continue

        point = (
            Point("space-weather-kp")
            .tag("provider", "NOAA_SWPC")
            .tag("feed", "observed")
            .tag("status", "observed")
            .field("kp", kp)
        )

        station_count = row.get("station_count")
        if station_count is not None:
            try:
                point = point.field("station_count", int(station_count))
            except (TypeError, ValueError):
                pass

        points.append(point.time(timestamp))

    return points


def forecast_points(payload):
    points = []
    for row in normalize_rows(payload):
        try:
            timestamp = parse_timestamp(row.get("time_tag"))
            kp = parse_kp(row)
        except (TypeError, ValueError):
            continue

        status = forecast_status(row)
        point = (
            Point("space-weather-kp")
            .tag("provider", "NOAA_SWPC")
            .tag("feed", "forecast")
            .tag("status", status)
            .field("kp", kp)
        )

        noaa_scale = row.get("noaa_scale")
        if noaa_scale not in (None, ""):
            point = point.field("noaa_scale", str(noaa_scale))

        points.append(point.time(timestamp))

    return points


def run_once(write_api):
    observed = observed_points(fetch_json(OBSERVED_URL))
    forecast = forecast_points(fetch_json(FORECAST_URL))
    points = observed + forecast

    if not points:
        raise RuntimeError("NOAA returned no valid planetary Kp rows")

    write_api.write(
        bucket=INFLUX_BUCKET,
        org=INFLUX_ORG,
        record=points,
    )

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    print(
        f"[{now}] NOAA SWPC planetary Kp update: "
        f"{len(observed)} observed rows, {len(forecast)} forecast rows",
        flush=True,
    )


def main():
    if not INFLUX_TOKEN:
        raise RuntimeError(
            "INFLUX_TOKEN is required to write NOAA data to InfluxDB"
        )

    client = InfluxDBClient(
        url=INFLUX_URL,
        token=INFLUX_TOKEN,
        org=INFLUX_ORG,
        timeout=10000,
    )
    write_api = client.write_api(write_options=SYNCHRONOUS)

    try:
        while True:
            try:
                run_once(write_api)
            except Exception as exc:
                now = datetime.datetime.now(
                    datetime.timezone.utc
                ).isoformat()
                print(
                    f"[{now}] NOAA SWPC update failed: {exc}",
                    flush=True,
                )

            time.sleep(FETCH_INTERVAL_SECONDS)
    finally:
        write_api.close()
        client.close()


if __name__ == "__main__":
    main()
