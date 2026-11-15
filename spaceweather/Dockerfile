FROM python:3.11.18-slim-bookworm

WORKDIR /usr/app/src

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY *.py ./

CMD ["python", "collector.py"]
