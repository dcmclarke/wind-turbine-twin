# Build context is the repository root (see docker-compose.yml)
FROM python:3.12-slim

WORKDIR /edge
RUN pip install --no-cache-dir paho-mqtt==2.1.0

COPY edge/publisher.py .
COPY backend/app/data/av7_10min.csv .

RUN useradd -r edge
USER edge

CMD ["python", "publisher.py", "--csv", "av7_10min.csv"]
