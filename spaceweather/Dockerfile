FROM balenalib/raspberrypi3-64-debian-python:3.10-bookworm-build

WORKDIR /usr/app/src

ENV PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir influxdb_client

COPY *.py ./

CMD ["python", "collector.py"]
