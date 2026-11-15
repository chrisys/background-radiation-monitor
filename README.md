# Background Radiation Monitor

**A simple balenaCloud application to measure and record background radiation in your area. Radiation is detected with a cheaply available board, and connected to a Raspberry Pi to provide InfluxDB for datalogging and Grafana for pretty charts.**

![grafana-dashboard](https://raw.githubusercontent.com/balenalabs-incubator/background-radiation-monitor/master/assets/grafana-dashboard.png)

## Hardware required

* A Raspberry Pi (any model should be good for this, but I’d recommend a 3 or above just for performance reasons)
* An 8GB (or larger) SD card (we recommend SanDisk Extreme Pro SD cards)
* A power supply (PSU)
* A radiation detector [Amazon UK](https://www.amazon.co.uk/KKmoon-Assembled-Counter-Radiation-Detector/dp/B07S86Q5X8) or [AliExpress](https://www.aliexpress.com/item/32884861168.html?spm=a2g0o.productlist.0.0.5faf6aa9OuQXsc)
* Some [Dupont cables/jumper jerky](https://shop.pimoroni.com/products/jumper-jerky?variant=348491271) (you’ll need 3 female-female cables)


## Hardware connection

There are 3 connections we need to make from the radiation detector board to the Raspberry Pi. They are +5V and Ground (GND) for power, and the output pulse line to detect the count. Note that this is called `VIN` which can be a bit confusing as this usually means ‘voltage input’ or something similar, but on this board, it’s the output.

![pi-geiger-simple](https://raw.githubusercontent.com/balenalabs-incubator/background-radiation-monitor/master/assets/pi-geiger-simple.png)

In this configuration you only need to provide 5 volt power to one of the two boards; if you’re powering the Pi with a standard micro-USB power supply, that will power the detector board via the connections we’ve just made, as well.


### GPIO signal safety and diagnostics

The Raspberry Pi GPIO is a **3.3 V input**. A software pull-up does not convert a 5 V detector output to 3.3 V. Before connecting a detector output directly to the Pi, verify the logic-level voltage with respect to the common GND and use a suitable divider/level shifter if required. Do not probe the detector high-voltage section with ordinary GPIO equipment.

The counter defaults to no internal pull resistor and falling-edge detection. This preserves the original input behavior that was known to count correctly with the project hardware. Enable an internal pull-up only after confirming that the detector output is compatible with it:

```text
PULSE_PIN=7
GPIO_PULL=off
GPIO_EDGE=falling
```

If the detector output uses a different interface, these values can be changed as balenaCloud service variables after confirming the board's electrical behavior.

The counter does **not** silently discard unusual pulses. Instead it records diagnostic fields so electrical noise can be distinguished from a genuine count-rate increase:

- `cps`: pulses observed during the most recent one-second window.
- `gpio_level`: sampled GPIO logic level.
- `pattern_hz`: estimated repetition frequency from recent pulse intervals.
- `pattern_cv`: coefficient of variation of the recent pulse intervals.
- `signal_anomaly`: `0` when no software warning is active, otherwise `1`.
- `signal_warning`: diagnostic text such as `NO_PULSES`, `HIGH_CPM`, or `POSSIBLE_MAINS_INTERFERENCE`.

A low-variation periodic signal around 45–65 Hz is flagged as possible mains-frequency interference. This is a diagnostic warning only; the raw CPM is still stored.


### GPIO compatibility note for v1.3.1

Version 1.3.0 introduced an internal pull-up as the default GPIO input configuration. On some detector boards this can suppress or alter the pulse signal. Version 1.3.1 restores the original neutral input configuration by making `GPIO_PULL=off` the default while keeping all signal diagnostics available.

If a board is known to expose an open-collector/active-low output and requires a pull-up, set `GPIO_PULL=up` explicitly as a balenaCloud service variable after verifying that the signal voltage is safe for a 3.3 V Raspberry Pi GPIO.


## Monitoring and diagnostics in v1.4.0

Version 1.4.0 keeps the known-working GPIO defaults from v1.3.1 and adds monitoring intended to make wiring/contact faults visible much sooner.

The counter now records:

- `last_pulse_age_s`: seconds since the most recent pulse.
- `pulse_total`: total pulses detected since the counter process started.
- `uptime_s`: counter-process uptime.
- `counter_ready`: `0` during the initial warm-up window and `1` afterwards.
- `detector_status`: textual state such as `WARMUP`, `OK`, `NO_PULSES`, `HIGH_CPM`, or `POSSIBLE_MAINS_INTERFERENCE`.
- `write_failures_total`: cumulative failed InfluxDB write attempts since startup.
- `calibration_status`: defaults to `UNCALIBRATED`.

A 60-second warm-up avoids interpreting the partially filled rolling CPM window immediately after a restart as a stable one-minute count. Unusual pulses are still preserved; the diagnostics do not silently remove them.

InfluxDB writes now use a small, bounded retry loop. GPIO pulse collection continues independently while the main loop retries a failed database write.

The Grafana dashboard is renamed **Background Radiation Monitor — J305** and now shows raw plus 5-minute mean trends, textual detector status, last-pulse age, calibration status, the current CPM-to-µSv/h factor, total pulses, and counter uptime.


## Statistical quality and testability in v1.5.0

Version 1.5.0 keeps the working GPIO behavior and adds statistical context, clearer status codes, device identification, and automated tests.

For a 60-second CPM window, the counter stores an approximate Poisson 1σ counting uncertainty:

```text
cpm_sigma = sqrt(CPM)
relative_uncertainty = sqrt(CPM) / CPM
usvh_sigma = cpm_sigma × USVH_RATIO
```

These fields describe **counting statistics only**. They do not include uncertainty in the J305 energy response, high-voltage operating point, geometry, or the CPM-to-µSv/h calibration factor. During the first 60 seconds after startup the rolling CPM window is still filling, so use `counter_ready` to distinguish warm-up data.

New measurement fields include `cpm_sigma`, `cpm_relative_uncertainty`, `cpm_relative_uncertainty_pct`, `usvh_sigma`, `sensor_id`, `detector_status_code`, and `calibration_status_code`.

`SENSOR_ID` can be set explicitly as a balenaCloud service variable. If it is not set, the counter uses `BALENA_DEVICE_UUID` when available, otherwise `geiger-j305`.

The default no-pulse warning is now 180 seconds, making a disconnected or bad signal contact visible sooner while remaining conservative for normal background counting.

Pure diagnostic/statistical functions live in `counter/metrics.py` and are covered by unit tests. A GitHub Actions workflow compiles the Python sources and tests Poisson uncertainty, warm-up/OK/no-pulse status handling, calibration status codes, and 50 Hz interference detection.

The Grafana status panels now use numeric status codes with value mappings, avoiding the previous `No data` behavior seen with text-only fields on some Grafana/InfluxDB combinations.

## Software setup

Running this project is as simple as deploying it to a balenaCloud application, then downloading the OS image from the dashboard and flashing your SD card.

[![](https://balena.io/deploy.png)](https://dashboard.balena-cloud.com/deploy)

We recommend this button as the de-facto method for deploying new apps on balenaCloud, but as an alternative, you can set this project up with the repo and balenaCLI if you choose. Get the code from this repo, and set up [balenaCLI](https://github.com/balena-io/balena-cli) on your computer to push the code to balenaCloud and your devices. [Read more](https://www.balena.io/docs/learn/deploy/deployment/).


## J305 calibration and dose-rate estimate

The measured value produced directly by the detector is **CPM (counts per minute)**. The `usvh` field is an **estimated dose rate**, calculated as:

```text
estimated µSv/h = CPM × USVH_RATIO
```

For modern J305 glass tubes specified at **44 CPS per mR/h with Co-60**, the project now defaults to:

```text
USVH_RATIO=0.00332
```

That factor is derived from the 44 CPS/(mR/h) specification and the air-kerma conversion described in the J305 technical note below. The same note explains that the frequently copied legacy value `0.00812` corresponds to a different 18 CPS/(mR/h) assumption and should not automatically be applied to every J305 tube.

A J305-based monitoring study published in 2026 reports an operating range of **380–450 V** and used approximately **420 V** in the central plateau region. The same study also shows that uncompensated GM tubes have energy-dependent response and supports condition-specific calibration rather than one universal CPM-to-dose conversion factor. For that reason, CPM should be treated as the primary measurement and the µSv/h value as an estimate unless the complete detector has been calibrated against a suitable reference instrument under the intended radiation field.

The software keeps `USVH_RATIO` configurable so a measured calibration factor can replace the default without rebuilding the image. Each InfluxDB point also records `usvh_ratio` and `tube_model` as fields so the calibration context is retained with the data.

### Calibration references

- IoT-devices, **“Geiger tube J305: How to calculate the conversion factor of CPM to µSv/h”**: https://iot-devices.com.ua/en/geiger-tube-j305-how-to-calculate-the-conversion-factor-of-cpm-technical-note-en/
- Choi et al. (2026), **“Application of a low-cost Geiger–Müller monitoring system for clinical radiation environments”**, Journal of Applied Clinical Medical Physics: https://pmc.ncbi.nlm.nih.gov/articles/PMC13473700/
- InfluxData Python client documentation for synchronous writes: https://docs.influxdata.com/influxdb/cloud/api-guide/client-libraries/python/


## External access and reverse proxy in v1.6.0

Version 1.6.0 places a small Nginx reverse proxy in front of Grafana:

```text
balena Public Device URL / local port 80
                 |
                 v
             Nginx :80
              |   |
      /healthz    +--> Grafana :3000
                         |
                         v
                    InfluxDB :8086
```

Grafana no longer binds directly to host port 80. Nginx owns port 80 and proxies normal HTTP traffic and Grafana Live WebSocket traffic to the internal `grafana:3000` service. This gives the device a lightweight web listener that can remain available while Grafana is restarting.

Two health endpoints are available:

- `/healthz`: served directly by Nginx and returns HTTP 200 when the front-end proxy is alive.
- `/grafana-health`: proxies Grafana's `/api/health` endpoint and verifies the application itself is responding.

If Grafana is temporarily unavailable, Nginx returns HTTP 503 with a short retry message instead of dropping the connection. Docker/balena healthchecks are also configured for both the Nginx and Grafana services.

The public dashboard remains available at the device's normal balena Public Device URL or local IP address. No router port-forwarding is required for the balena Public Device URL.


### External-access diagnostics in v1.6.1

Version 1.6.1 adds device-aware diagnostics to the Nginx front end without changing Grafana, InfluxDB, GPIO, or radiation measurements.

- `/healthz` still returns `ok`.
- `/grafana-health` still checks Grafana itself.
- `/device-info` now returns JSON containing the running application version and the balena device UUID seen by the container.
- Every Nginx response includes `X-BRM-Version` and `X-BRM-Device-UUID` response headers.
- `/api/ds/query` disables Nginx response buffering, avoiding large Grafana/Influx query responses being written to temporary proxy files on the SD card.
- `X-Forwarded-Host` is now forwarded explicitly to Grafana.

The device UUID shown by `/device-info` can be compared with the UUID in the balena Public Device URL. This is useful when an old or different device URL is being used.



## NOAA planetary Kp space-weather context in v1.9.0

Version 1.9.0 adds official NOAA / NWS Space Weather Prediction Center planetary K-index data to the Grafana dashboard. This is contextual environmental data; it does not alter the Geiger counter measurements or the CPM-to-dose estimate.

The new `spaceweather` service fetches:

- observed planetary Kp from `https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json`;
- observed/estimated/predicted 3-day Kp data from `https://services.swpc.noaa.gov/products/noaa-planetary-k-index-forecast.json`.

The collector refreshes every five minutes by default and stores valid 0–9 Kp values in the existing InfluxDB bucket. NOAA's Kp products are three-hour indices/forecasts, so the five-minute fetch interval is intentionally more frequent than the source cadence while remaining lightweight.

The dashboard adds, in English:

- **Current observed planetary Kp**;
- **3-day forecast peak Kp**;
- **Planetary Kp — observed, estimated and 3-day forecast**;
- **NOAA 3-day Kp forecast data**;
- an English NOAA Kp/G-scale reference.

Kp 5 or greater is the NOAA geomagnetic-storm threshold. The dashboard keeps observed, estimated, and predicted values visibly distinct so forecasts are not presented as measurements.

The collector accepts both the current NOAA object-array JSON format and the older header-row array format. If NOAA is temporarily unavailable, existing data remain in InfluxDB and no synthetic values are generated.



## Environmental and space-weather correlation context in v1.10.0

Version 1.10.0 extends the external-context collector so the radiation measurements can be compared with local weather and additional space-weather indicators without changing the J305 counter logic.

### Automatic weather location by default

Weather geolocation is **automatic by default**. If `WEATHER_LATITUDE` and `WEATHER_LONGITUDE` are not set, the Raspberry Pi requests an approximate public-IP location from `ipwho.is`. The resulting latitude and longitude are then used with Open-Meteo.

The stored weather point includes `location_source=ip`, latitude, longitude, and the returned city/region/country when available. IP geolocation is approximate and is suitable for general environmental context, but local rain can vary substantially over short distances.

For a known fixed installation, manual coordinates can override automatic IP geolocation:

```text
WEATHER_LATITUDE=...
WEATHER_LONGITUDE=...
```

When both values are present the stored location source becomes `manual`.

Set `WEATHER_LOCATION_MODE=manual` only when automatic IP geolocation must be disabled; in that mode both coordinates are required.

### Local weather context

Open-Meteo provides current:

- temperature;
- relative humidity;
- surface pressure;
- precipitation;
- rain.

### Additional NOAA SWPC context

The collector also stores the latest available:

- solar-wind speed;
- solar-wind proton density;
- IMF Bz in GSM coordinates;
- total IMF magnitude;
- Kyoto Dst index distributed by NOAA SWPC;
- GOES integral proton flux for the >=10 MeV channel.

Only valid source values are stored. External-source failures do not alter CPM, GPIO, calibration, or the estimated dose-rate calculation.

The dashboard keeps the external variables in separate panels with a common time axis and adds a 15-minute CPM reference panel, making temporal comparison easier without implying causation.



## Runtime maintenance and image optimization in v1.11.0

Version 1.11.0 refreshes the runtime stack while preserving the existing InfluxDB and Grafana persistent volumes and all J305 measurement behavior.

Pinned runtime components:

- Python `3.11.18-slim-bookworm` for `counter` and `spaceweather`;
- `influxdb-client==1.50.0`;
- `rpi-lgpio==0.6`;
- InfluxDB `2.7.12`;
- Grafana `12.4.15`;
- Nginx `1.30.6-alpine`.

The Python services now use the official slim Python image instead of the deprecated balenalib Python build image. Direct Python dependencies are pinned in per-service `requirements.txt` files so rebuilding the same Git revision does not silently select newer library releases.

Grafana now builds directly from the official multi-architecture Grafana image instead of downloading and installing a Debian package during every build. The existing provisioning directory and persistent `grafana-data` volume are retained.

The GitHub Actions workflow now uses Python 3.11 and additionally builds the counter, external-context, Grafana, and Nginx images. This catches dependency and container-build regressions before deployment.

No database migration is introduced. The existing `sense-data` and `grafana-data` volumes keep the same paths and must not be deleted during the update.


## Access the dashboard

Once the software has been deployed and downloaded to your device, Nginx listens on port 80 and proxies the dashboard to Grafana on its internal port 3000. The dashboard is accessible on the local IP address of the device, or via the balenaCloud public URL feature.

![public-url](https://raw.githubusercontent.com/balenalabs-incubator/background-radiation-monitor/master/assets/public-url.png)

## Raspberry Pi 3 64-bit / balenaCloud

The current release targets **Raspberry Pi 3 (using 64bit OS)** on balenaCloud.

Before deploying, configure the following balenaCloud **Service Variables**:

### influxdb service
- `DOCKER_INFLUXDB_INIT_PASSWORD`: choose a strong password.
- `DOCKER_INFLUXDB_INIT_ADMIN_TOKEN`: choose a long random token.

### counter service
- `INFLUX_TOKEN`: set this to the same value as `DOCKER_INFLUXDB_INIT_ADMIN_TOKEN`.
- `USVH_RATIO` (optional): conversion factor from CPM to estimated µSv/h. Defaults to `0.00332` for the modern J305 glass-tube specification discussed below.
- `GEIGER_TUBE_MODEL` (optional): tube model stored with each measurement. Defaults to `J305`.
- `PULSE_PIN` (optional): physical BOARD pin used for the pulse input. Defaults to `7`.
- `GPIO_PULL` (optional): `up`, `down`, or `off`. Defaults to `off` to preserve the original working input behavior.
- `GPIO_EDGE` (optional): `falling` or `rising`. Defaults to `falling`.
- `NO_PULSE_WARNING_SECONDS` (optional): time with no pulses before a diagnostic warning. Defaults to `180`.
- `HIGH_CPM_WARNING` (optional): CPM threshold for a high-count diagnostic warning. Defaults to `1000`.
- `WARMUP_SECONDS` (optional): startup warm-up before the rolling CPM window is considered ready. Defaults to `60`.
- `WRITE_INTERVAL_SECONDS` (optional): interval between stored measurements. Defaults to `10`.
- `INFLUX_WRITE_RETRIES` (optional): bounded write attempts per measurement. Defaults to `3`.
- `INFLUX_RETRY_DELAY_SECONDS` (optional): base retry delay in seconds. Defaults to `1.0`.
- `CALIBRATION_STATUS` (optional): text stored with the measurements. Defaults to `UNCALIBRATED`.
- `SENSOR_ID` (optional): logical sensor/device identifier stored with each measurement. Defaults to the balena device UUID when available.

### grafana service
- `INFLUX_TOKEN`: set this to the same value as `DOCKER_INFLUXDB_INIT_ADMIN_TOKEN`.

### spaceweather service
- `INFLUX_TOKEN`: set this to the same value as `DOCKER_INFLUXDB_INIT_ADMIN_TOKEN`.
- `NOAA_FETCH_INTERVAL_SECONDS` (optional): NOAA refresh interval. Defaults to `300` seconds.
- `NOAA_HTTP_TIMEOUT_SECONDS` (optional): HTTP timeout for external requests. Defaults to `20` seconds.
- `WEATHER_LOCATION_MODE` (optional): defaults to `auto`, which uses public-IP geolocation when manual coordinates are absent.
- `WEATHER_LATITUDE` and `WEATHER_LONGITUDE` (optional): fixed installation coordinates. When both are provided they override automatic IP geolocation.

The InfluxDB token and password are intentionally not stored in this repository.

To deploy a new release with the balena CLI:

```sh
balena login
balena push g_jo_o_antunes/background-radiation-monitor
```

The `counter` container reads its InfluxDB connection settings from environment variables. Writes are synchronous and use a bounded retry loop, so a success message is printed only after InfluxDB accepts the write. Failed attempts are logged and counted without silently changing the pulse data.

