# sona-final-year-mini-it-aids-d-sathish-527
> **StartupFair Hackathon: Solo Participant 29 (Final year mini project (IT / AIDS Dept))**

---

# IoT-Enabled Self-Navigating Road Hazard Detection Robot

A production-ready, full-stack, autonomous road hazard inspection platform that couples edge computer vision inference on a robotic rover with an IoT gateway and a real-time fleet operations cloud dashboard.

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/Frontend-React%2018%20+%20Vite-61DAFB?logo=react)](https://react.dev/)
[![YOLOv8](https://img.shields.io/badge/Vision-YOLOv8-blue)](https://github.com/ultralytics/ultralytics)
[![ESP32](https://img.shields.io/badge/Firmware-ESP32%20PlatformIO-red?logo=espressif)](https://platformio.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🌟 Key Features

- **Autonomous Patrol & Obstacle Avoidance (Algorithm 1)**: Multithreaded navigation loop reacting to 3x ultrasonic distance sensors in under 20 ms with emergency reverse, steer, and clearance maneuvers.
- **Hardware Safety Watchdog**: Independent hardware thread monitoring navigation heartbeats; stops all motors within 500 ms if any thread freezes.
- **Edge Vision with YOLOv8**: Detects potholes, cracks, and animal hazards with bounding boxes and cropped snapshot generation.
- **Spatial-Temporal Deduplication**: Haversine distance-based deduplication prevents redundant alerts for the same physical hazard within 5 meters and 10 seconds.
- **Dual-Uplink IoT Gateway (ESP32)**: Relays telemetry and hazards via MQTT over Wi-Fi, automatically falling back to HTTP REST endpoints or internal offline queue buffers when network drops occur.
- **Cloud Backend & Live Streaming**: FastAPI server with Mosquitto MQTT worker, dynamic severity scoring engine, Twilio SMS / Email alert dispatcher, and WebSockets.
- **Real-Time Operations Dashboard**: Dark-mode React Leaflet UI with live animated hazard markers, density heatmap, real-time robot breadcrumbs, and one-click triage queue.

---

## 📂 Monorepo Architecture

```text
road-hazard-robot/
├── backend/          # FastAPI Cloud Server, MQTT worker, DB models, WebSockets
├── dashboard/        # React 18, TypeScript, Tailwind CSS, Leaflet live map
├── database/         # Oracle PL/SQL & PostgreSQL PL/pgSQL schemas, packages, triggers
├── robot/            # Raspberry Pi 4 app, HAL (Hardware & Mock), navigation, detector
├── ml/               # YOLOv8 dataset prep, training, eval, ONNX export, benchmark
├── firmware/         # ESP32 PlatformIO C++ firmware with UART and MQTT
├── simulator/        # GPS route & sensor simulator, 2D obstacle avoidance visualizer
├── mosquitto/        # Mosquitto MQTT broker configuration
├── scripts/          # Database migration to PL/SQL & maintenance utilities
├── docs/             # Architecture, PL/SQL guide, hardware wiring schematics, and API docs
├── docker-compose.yml# Container orchestration for cloud, Oracle/Postgres DB, simulation
├── Makefile          # One-touch developer automation targets
└── .env.example      # Configuration template
```

---

## 🚀 Quickstart Guide

### Option 1: Docker Compose (All-in-One Cloud & Simulation)

Start the entire cloud stack (Mosquitto, PostgreSQL, FastAPI Backend, React Dashboard, and Campus Route Simulator):

```bash
# 1. Clone & copy environment settings
cp .env.example .env

# 2. Spin up containers
docker compose up -d

# 3. Access interfaces:
# - Dashboard: http://localhost:3000
# - Backend Docs: http://localhost:8000/docs
# - MQTT Broker: localhost:1883
```

---

### Option 2: Local Developer Setup

#### 1. Backend Server
```bash
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 2. Operations Dashboard
```bash
cd dashboard
npm install
npm run dev
# Open http://localhost:5173
```

#### 3. Edge Robot (Mock Simulation Mode)
```bash
python robot/main.py --config robot/config.yaml
```

#### 4. Route & Hazard Simulator
```bash
python simulator/simulate_route.py --speed 1.0
```

---

## 🛠️ Makefile Commands

| Command | Description |
| :--- | :--- |
| `make setup` | Install Python and Node dependencies across all modules |
| `make test` | Run backend and robot test suites with `pytest` |
| `make run-backend` | Launch FastAPI cloud server with hot-reload |
| `make run-dashboard`| Launch Vite dev server for the operations dashboard |
| `make run-robot` | Launch robot application in simulation mode |
| `make run-sim` | Launch continuous campus loop route simulator |
| `make train` | Run YOLOv8 model training pipeline |

---

## 🤖 Hardware Bill of Materials (BOM)

- **Edge Computer**: Raspberry Pi 4 Model B (4GB or 8GB RAM)
- **IoT Gateway**: ESP32 DevKit v1 / NodeMCU-32S
- **Motor Driver**: L298N Dual H-Bridge Driver
- **Chassis**: 4WD Robot Smart Car Kit with 4x DC Geared Motors
- **Ultrasonic Rangefinders**: 3x HC-SR04 (Front, Left, Right) with voltage dividers
- **GPS Module**: NEO-6M UART GPS with ceramic patch antenna
- **Camera**: Raspberry Pi Camera Module v2 / v3 or USB HD Webcam
- **Power**: 7.4V / 11.1V LiPo Battery + 2x LM2596 DC-DC Buck Converters

Detailed pin connections and safety schematics are documented in [docs/wiring.md](docs/wiring.md).

---

## 🧠 Machine Learning Workflow (`ml/`)

```bash
# 1. Generate synthetic dataset (or prepare raw dataset)
python ml/prepare_dataset.py --generate-synthetic --synthetic-count 60

# 2. Train YOLOv8 with road surface augmentations
python ml/train.py --epochs 100 --batch 16 --imgsz 640

# 3. Evaluate precision, recall, and mAP@0.5
python ml/evaluate.py --weights ml/weights/best.pt

# 4. Export to ONNX & TFLite for edge acceleration
python ml/export.py --weights ml/weights/best.pt --format onnx

# 5. Measure edge inference latency (FPS)
python ml/benchmark.py --weights ml/weights/best.pt
```

For cloud training on free GPU hardware, open [ml/train_colab.ipynb](ml/train_colab.ipynb) directly in Google Colab.

---

## 🧪 Running the Test Suite

```bash
# Run all unit and integration tests:
python -m pytest backend/tests -v
python -m pytest robot/tests -v
```

All 23 test cases cover:
- Algorithm 1 obstacle avoidance state transitions
- Motor PWM controller states
- Safety Watchdog timeout motor shutdown
- Spatial-temporal hazard deduplication
- IoT client UART protocol with ACK/retry and offline SQLite caching
- Backend REST endpoints, filtering, and auth
- Real-time severity scoring with spatial clustering

---

## 📖 Documentation
- [System Architecture](docs/architecture.md)
- [Oracle PL/SQL Database Guide](docs/plsql_database_guide.md)
- [Hardware Wiring & Voltage Dividers](docs/wiring.md)
- [Cloud REST & WebSocket API](docs/api.md)
