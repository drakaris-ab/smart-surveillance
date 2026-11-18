# 📦 Smart Unattended Object Detection

> **Specialized microservice** for detecting abandoned/left-behind objects in surveillance zones with configurable dwell-time logic and zone-based alerting.

## 🏗️ Architecture

```
smart-unattended-object/
├── backend/                 # FastAPI service
│   ├── ai/                 # YOLO models, custom heads
│   ├── config/             # Thresholds, zone rules
│   ├── core/               # Exceptions, utilities
│   ├── database/           # Event storage, track history
│   ├── routes/             # API endpoints
│   ├── services/           # Detection logic, alert generation
│   ├── shared/             # Shared schemas, constants
│   ├── util/               # Geometry, tracking helpers
│   ├── main.py             # Entry point
│   └── requirements.txt
│
├── scripts/                # Utility scripts (model export, benchmark)
├── weights/                # Model weights (YOLOv11, custom)
├── dist/                   # PyInstaller executable
├── logs/                   # Runtime logs
└── .env                    # Environment config
```

## 🚀 Quick Start

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Configure: DATABASE_URL, REDIS_URL, YOLO_MODEL_PATH, THRESHOLDS

uvicorn main:app --reload --port 8002
```

## 🧠 Detection Pipeline

```
Frame Input
     │
     ▼
┌─────────────┐
│  YOLOv11    │──▶ Object Detections (class, bbox, confidence)
│  Inference  │
└─────────────┘
     │
     ▼
┌─────────────┐
│  DeepSORT   │──▶ Persistent Track IDs + Kalman States
│  Tracking   │
└─────────────┘
     │
     ▼
┌─────────────┐
│  Zone Map   │──▶ Point-in-polygon check per track
│  Overlay    │
└─────────────┘
     │
     ▼
┌─────────────┐
│  Dwell      │──▶ Timer per (track_id, zone_id)
│  Timer      │
└─────────────┘
     │
     ▼
Threshold Exceeded?
     │
     ├── Yes ──▶ ALERT EVENT (WebSocket + DB + Notification)
     │
     └── No ──▶ Continue Tracking
```

## 📡 API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/detect` | POST | Single-frame detection (image → detections + tracks) |
| `/stream/start` | POST | Start continuous stream processing (RTSP/WebRTC) |
| `/stream/stop` | POST | Stop stream processing |
| `/zones` | GET/POST | Zone configuration (polygons + rules) |
| `/zones/{id}` | PUT/DELETE | Update/delete zone |
| `/events` | GET | Unattended object events (paginated, filterable) |
| `/events/{id}/clip` | GET | Download video clip of event |
| `/tracks/active` | GET | Currently tracked objects in zones |
| `/config` | GET/PUT | Global thresholds, model settings |
| `/health` | GET | Service health + GPU status |

## 🔧 Configuration

```bash
# .env
DATABASE_URL=postgresql://user:pass@localhost:5432/object_db
REDIS_URL=redis://localhost:6379/2

# Model
YOLO_MODEL_PATH=../weights/yolo11m.pt
USE_TENSORRT=false
DEVICE=cuda:0

# Detection thresholds
OBJ_CONF_THRESH=0.45
IOU_THRESH=0.5
MAX_DET=100

# Tracking
TRACK_BUFFER=30
MATCH_THRESH=0.8
MIN_BOX_AREA=100

# Dwell-time rules (per zone, configurable via API)
DEFAULT_DWELL_SECONDS=30
HIGH_SECURITY_DWELL_SECONDS=10

# Alert cooldown
ALERT_COOLDOWN_SECONDS=60

# Classes of interest (COCO indices)
TARGET_CLASSES=[24,26,28,32,39,41,63,66,67]  # backpack, handbag, suitcase, etc.
```

## 🎯 Zone Rules Engine

Each zone can have independent rules:

```json
{
  "zone_id": "zone_secure_1",
  "name": "Server Room Entry",
  "polygon": [[100,200],[400,200],[400,500],[100,500]],
  "rules": {
    "unattended_object": {
      "enabled": true,
      "dwell_seconds": 10,
      "target_classes": [24,26,28,32,39,41,63,66,67],
      "min_confidence": 0.5
    },
    "loitering": {
      "enabled": false,
      "max_duration_seconds": 120
    }
  },
  "alert_channels": ["websocket", "email", "sms", "siren"]
}
```

## 📊 Event Schema

```json
{
  "event_id": "evt_abc123",
  "timestamp": "2024-01-15T10:30:45Z",
  "camera_id": "cam_001",
  "zone_id": "zone_secure_1",
  "track_id": 42,
  "object_class": "backpack",
  "confidence": 0.87,
  "bbox": [245, 312, 89, 67],
  "dwell_seconds": 35.2,
  "alert_triggered": true,
  "clip_url": "/api/v1/events/evt_abc123/clip",
  "snapshot_url": "/api/v1/events/evt_abc123/snapshot"
}
```

## ⚡ Performance

| Metric | Value |
|--------|-------|
| Inference (640x640, FP16, GPU) | ~12ms |
| Tracking overhead | ~2ms/frame |
| End-to-end latency (stream) | ~150ms |
| False positive rate (tuned) | <2% |
| Multi-stream (4x 1080p, single GPU) | ~60 fps total |

## 🐳 Docker

```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y libgl1 libglib2.0-0 ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 📄 License

MIT — see root [LICENSE](../LICENSE)