FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV BACKEND_URL=http://backend:8000
ENV MQTT_BROKER_HOST=mosquitto
ENV MQTT_BROKER_PORT=1883
ENV ROBOT_API_KEY=robot-sec-key-771ac-roadbot-edge-2026

CMD ["python", "simulate_route.py", "--geojson", "campus_route.geojson", "--backend-url", "http://backend:8000", "--broker-host", "mosquitto", "--mode", "auto"]
