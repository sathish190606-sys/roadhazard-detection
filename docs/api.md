# Cloud Backend REST & WebSocket API Specification

The Road Hazard Robot Cloud Backend provides high-throughput ingestion for edge robots, real-time live push via WebSockets, and management REST endpoints for the operations dashboard.

---

## 1. Authentication

### A. Robot / Gateway Authentication
Edge robots and IoT gateways authenticate using the `X-Robot-Key` HTTP header.
```http
X-Robot-Key: robot-sec-key-771ac-roadbot-edge-2026
```

### B. User / Operator Authentication
Web dashboard users authenticate using OAuth2 Bearer JWT tokens.
```http
Authorization: Bearer <access_token>
```

---

## 2. REST Endpoints

### `POST /api/hazards`
Ingests a new road hazard record. Triggers severity scoring, spatial clustering evaluation, database persistence, WebSocket broadcast, and high-severity alerting.

- **Auth**: `X-Robot-Key` or Bearer Token
- **Request Body**:
```json
{
  "robot_id": "robot-01",
  "hazard_class": "pothole",
  "confidence": 0.89,
  "latitude": 12.971598,
  "longitude": 77.594562,
  "bbox": {
    "x1": 120.5,
    "y1": 240.0,
    "x2": 310.2,
    "y2": 390.5
  },
  "snapshot_base64": "data:image/jpeg;base64,/9j/4AAQSkZJRgABA..."
}
```
- **Response `201 Created`**:
```json
{
  "id": 42,
  "robot_id": "robot-01",
  "hazard_class": "pothole",
  "confidence": 0.89,
  "latitude": 12.971598,
  "longitude": 77.594562,
  "bbox": { "x1": 120.5, "y1": 240.0, "x2": 310.2, "y2": 390.5 },
  "snapshot_url": "/api/hazards/42/snapshot",
  "severity_score": 85.4,
  "cluster_count": 2,
  "status": "new",
  "created_at": "2026-10-12T13:45:00Z"
}
```

---

### `GET /api/hazards`
Query and filter recorded hazards with sorting and pagination.

- **Query Parameters**:
  - `hazard_class` *(optional)*: `pothole`, `crack`, `animal`
  - `status` *(optional)*: `new`, `acknowledged`, `repaired`
  - `min_confidence` *(optional)*: float between `0.0` and `1.0`
  - `min_severity` *(optional)*: float between `0.0` and `100.0`
  - `robot_id` *(optional)*: string
  - `skip` *(optional)*: integer (default `0`)
  - `limit` *(optional)*: integer (default `100`)
- **Response `200 OK`**:
```json
[
  {
    "id": 42,
    "robot_id": "robot-01",
    "hazard_class": "pothole",
    "confidence": 0.89,
    "latitude": 12.971598,
    "longitude": 77.594562,
    "severity_score": 85.4,
    "status": "new",
    "created_at": "2026-10-12T13:45:00Z"
  }
]
```

---

### `PATCH /api/hazards/{id}`
Update triage or repair status of an existing hazard.

- **Request Body**:
```json
{
  "status": "repaired"
}
```
- **Response `200 OK`**:
```json
{
  "id": 42,
  "status": "repaired",
  "updated_at": "2026-10-12T14:10:00Z"
}
```

---

### `GET /api/stats`
Returns system-wide aggregated telemetry and fleet analytics.

- **Response `200 OK`**:
```json
{
  "total_hazards": 128,
  "active_hazards": 45,
  "repaired_hazards": 83,
  "high_severity_count": 14,
  "by_class": {
    "pothole": 62,
    "crack": 48,
    "animal": 18
  },
  "by_status": {
    "new": 32,
    "acknowledged": 13,
    "repaired": 83
  },
  "online_robots": 2
}
```

---

### `GET /api/robots/status`
Returns fleet health, battery levels, and last-seen timestamps.

- **Response `200 OK`**:
```json
[
  {
    "robot_id": "robot-01",
    "status": "patrol",
    "battery_percentage": 88.5,
    "current_latitude": 12.97210,
    "current_longitude": 77.59480,
    "speed": 1.2,
    "last_seen": "2026-10-12T14:15:32Z"
  }
]
```

---

## 3. Real-Time WebSocket Interface

### `WebSocket /ws/live`
Operators connect to this endpoint for real-time live map updates, fleet location breadcrumbs, and high-severity flash alerts.

- **Handshake URL**: `ws://<HOST>:8000/ws/live`
- **Incoming Messages**:

#### 1. Live Hazard Ingest Event
```json
{
  "event": "NEW_HAZARD",
  "data": {
    "id": 43,
    "robot_id": "robot-01",
    "hazard_class": "crack",
    "confidence": 0.81,
    "latitude": 12.973412,
    "longitude": 77.595120,
    "severity_score": 64.0,
    "status": "new",
    "created_at": "2026-10-12T14:16:02Z"
  }
}
```

#### 2. Fleet Telemetry & GPS Move Event
```json
{
  "event": "ROBOT_UPDATE",
  "data": {
    "robot_id": "robot-01",
    "status": "patrol",
    "battery": 87.2,
    "latitude": 12.973450,
    "longitude": 77.595180,
    "speed": 1.15
  }
}
```
