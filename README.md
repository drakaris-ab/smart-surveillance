# 🛡️ Smart Surveillance System

> **A production-grade, AI-powered video surveillance platform** combining real-time object detection, face recognition, and unattended object monitoring — built with modern cloud-native architecture.

![Architecture](https://img.shields.io/badge/Architecture-Microservices-blue)
![Backend](https://img.shields.io/badge/Backend-FastAPI-green)
![Frontend](https://img.shields.io/badge/Frontend-React%2018-61dafb)
![AI](https://img.shields.io/badge/AI-YOLOv11%20%7C%20InsightFace-orange)
![Database](https://img.shields.io/badge/Database-PostgreSQL%20%7C%20SQLite-blueviolet)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 📐 System Overview

This is a **modular, multi-service surveillance platform** designed for enterprise-scale deployments. It consists of three independently deployable services that can operate standalone or as an integrated system:

```
┌─────────────────────────────────────────────────────────────────┐
│                    SMART SURVEILLANCE ECOSYSTEM                 │
├──────────────────┬──────────────────────┬──────────────────────┤
│  🎥 MAIN APP     │  👤 FACE RECOGNITION │  📦 UNATTENDED OBJECT │
│  (smart-surveillance-app)              │  (smart-unattended-object)          │
├──────────────────┼──────────────────────┼──────────────────────┤
│ • Camera mgmt    │ • Face enrollment    │ • Object detection  │
│ • Zone config    │ • 1:N identification │ • Abandonment alert │
│ • Alert engine   │ • Liveness check     │ • Dwell-time logic  │
│ • WebRTC streams │ • Privacy blur       │ • Zone-based rules  │
│ • Multi-tenant   │ • GDPR compliance    │ • Forensic search   │
└──────────────────┴──────────────────────┴──────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.11+** (backend services)
- **Node.js 18+** (frontend)
- **PostgreSQL 15+** (production) / SQLite (dev)
- **Redis 7+** (caching & pub/sub)
- **NVIDIA GPU** with CUDA 12.8 (recommended for inference)
- **Ollama** (optional, for local LLM integration)

### 1. Clone & Setup
```bash
git clone https://github.com/drakaris-ab/smart-surveillance.git
cd smart-surveillance
```

### 2. Backend Services (each service independently)
```bash
# Main Surveillance App
cd smart-surveillance-app/backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Configure DATABASE_URL, REDIS_URL, etc.
uvicorn main:app --reload --port 8000

# Face Recognition Service
cd ../smart-Face-Recognization/backend
pip install -r requirements.txt
python main.py

# Unattended Object Detection
cd ../smart-unattended-object/backend
pip install -r requirements.txt
python main.py
```

### 3. Frontend
```bash
cd smart-surveillance-app/frontend
npm install
npm run dev
# Open http://localhost:5173
```

---

## 🏗️ Architecture Deep Dive

### Core Services

| Service | Port | Description | Tech Stack |
|---------|------|-------------|------------|
| **Main API** | 8000 | Camera management, zones, alerts, WebRTC streaming | FastAPI, SQLAlchemy, WebRTC (aiortc) |
| **Face Recognition** | 8001 | Face enrollment, 1:N matching, liveness detection | InsightFace, ONNX Runtime, FastAPI |
| **Unattended Object** | 8002 | Object detection, abandonment alerts, dwell tracking | YOLOv11, OpenCV, FastAPI |
| **Frontend** | 5173 | React dashboard, live streams, config UI | React 18, Tailwind, WebRTC, Socket.io |

### Data Flow

```
┌─────────┐     ┌──────────────┐     ┌─────────────┐     ┌────────────┐
│ Cameras │────▶│  Ingestion   │────▶│  Detection  │────▶│  Alerting  │
│  (RTSP/ │     │  (FFmpeg/    │     │  (YOLO/     │     │  (Rules,   │
│   WebRTC)│     │   WebRTC)    │     │  InsightFace)│    │   Notify)  │
└─────────┘     └──────────────┘     └─────────────┘     └────────────┘
       │                │                    │                   │
       ▼                ▼                    ▼                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     EVENT BUS (Redis Pub/Sub)                       │
└─────────────────────────────────────────────────────────────────────┘
       │                │                    │                   │
       ▼                ▼                    ▼                   ▼
┌─────────┐     ┌──────────────┐     ┌─────────────┐     ┌────────────┐
│ Postgres│     │   Timescale  │     │   Redis     │     │  WebSocket │
│ (Meta)  │     │  (Metrics)   │     │  (Cache)    │     │  (UI Push) │
└─────────┘     └──────────────┘     └─────────────┘     └────────────┘
```

---

## 🧠 AI/ML Pipeline

### Object Detection (YOLOv11)
- **Model**: `yolo11m.pt` (medium, 38MB) — balanced speed/accuracy
- **Classes**: Person, Vehicle, Bag, Package, Laptop, Phone, etc. (80 COCO classes)
- **Inference**: ONNX Runtime + TensorRT optimization (optional)
- **Tracking**: DeepSORT + Kalman filter for persistent IDs

### Face Recognition (InsightFace)
- **Detection**: RetinaFace (mobileNet backbone)
- **Embedding**: ArcFace (ResNet-100) — 512-dim vectors
- **Search**: FAISS HNSW index for sub-millisecond 1:N lookup
- **Liveness**: Silent face anti-spoofing (texture + motion analysis)

### Unattended Object Logic
```
Object Detected
       │
       ▼
┌──────────────────┐
│  Track + Assign  │──▶ New Track? ──▶ Start Dwell Timer
│  Persistent ID   │
└──────────────────┘
       │
       ▼
┌──────────────────┐
│  Zone Rule Check │──▶ High-Security Zone?
│  (Configurable)  │
└──────────────────┘
       │
       ▼
Dwell Time > Threshold?
       │
       ├── Yes ──▶ ALERT (WebSocket + Email + SMS + Siren)
       │
       └── No ──▶ Continue Tracking
```

---

## 🔧 Configuration

### Environment Variables (per service)
```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/surveillance
# or for dev: sqlite:///./surveillance.db

# Redis
REDIS_URL=redis://localhost:6379/0

# AI Models
YOLO_MODEL_PATH=./yolo11m.pt
INSIGHTFACE_MODEL_PATH=./models/insightface

# External APIs
GEMINI_API_KEY=your_key_here        # Optional: LLM-powered alert summaries
TWILIO_SID=xxx                      # SMS alerts
TWILIO_TOKEN=xxx
SMTP_HOST=smtp.gmail.com            # Email alerts
SMTP_PORT=587
SMTP_USER=xxx
SMTP_PASS=xxx

# WebRTC
ICE_SERVERS=[{"urls":"stun:stun.l.google.com:19302"}]
TURN_URL=turn:your-turn-server.com
TURN_CREDENTIAL=xxx
```

### Camera Configuration (via API or UI)
```json
{
  "name": "Lobby Entrance",
  "rtsp_url": "rtsp://admin:pass@192.168.1.100:554/stream1",
  "webrtc_enabled": true,
  "zones": [
    {"id": "zone_1", "name": "Entry Door", "polygon": [[100,100],[500,100],[500,400],[100,400]], "rules": ["unattended_object", "face_recognition"]},
    {"id": "zone_2", "name": "Waiting Area", "polygon": [[500,100],[900,100],[900,400],[500,400]], "rules": ["crowd_density"]}
  ],
  "detection": {
    "object_confidence": 0.5,
    "face_confidence": 0.6,
    "tracking_enabled": true
  }
}
```

---

## 📡 API Reference (Main Service)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/cameras` | GET/POST | List/Create cameras |
| `/api/v1/cameras/{id}/stream` | GET | WebRTC offer/answer |
| `/api/v1/zones` | GET/POST | Zone management |
| `/api/v1/alerts` | GET | Paginated alert history |
| `/api/v1/alerts/{id}/acknowledge` | POST | Acknowledge alert |
| `/api/v1/detections` | GET | Real-time detection feed |
| `/api/v1/faces/enroll` | POST | Enroll new face |
| `/api/v1/faces/identify` | POST | 1:N face search |
| `/api/v1/objects/unattended` | GET | Unattended object events |
| `/api/v1/health` | GET | System health check |

---

## 🖥️ Frontend Features

- **Live Dashboard** — Multi-camera grid with WebRTC sub-second latency
- **Camera Manager** — Add/edit/delete cameras, test connections, zone drawing (canvas)
- **Alert Center** — Real-time notifications, filtering, acknowledgment, export
- **Face Gallery** — Enroll/manage known persons, view recognition logs
- **Object Timeline** — Unattended object events with video clips
- **Analytics** — Detection counts, heatmaps, occupancy trends
- **Settings** — Global thresholds, notification channels, user management

---

## 🔐 Security & Compliance

- **Authentication**: JWT (access + refresh tokens), bcrypt password hashing
- **Authorization**: Role-based (Admin, Operator, Viewer) + resource-level permissions
- **Data Protection**: Face embeddings encrypted at rest (AES-256), GDPR right-to-delete endpoint
- **Audit Logging**: All config changes, alert actions, face enrollments logged
- **Network**: TLS 1.3 for all external comms, mTLS for service-to-service (optional)

---

## 📦 Deployment

### Docker Compose (Development)
```yaml
# docker-compose.yml (root)
version: '3.8'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: surveillance
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: secure_pass
    volumes: [postgres_data:/var/lib/postgresql/data]
    ports: ["5432:5432"]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  main-api:
    build: ./smart-surveillance-app/backend
    ports: ["8000:8000"]
    depends_on: [postgres, redis]
    environment:
      DATABASE_URL: postgresql://admin:secure_pass@postgres:5432/surveillance
      REDIS_URL: redis://redis:6379/0
    deploy:
      resources:
        reservations:
          devices: [{driver: nvidia, count: 1, capabilities: [gpu]}]

  face-service:
    build: ./smart-Face-Recognization/backend
    ports: ["8001:8000"]
    depends_on: [postgres, redis]

  object-service:
    build: ./smart-unattended-object/backend
    ports: ["8002:8000"]
    depends_on: [postgres, redis]

  frontend:
    build: ./smart-surveillance-app/frontend
    ports: ["5173:80"]
    depends_on: [main-api]

volumes:
  postgres_data:
```

### Kubernetes (Production)
- Helm charts available in `/k8s` (coming soon)
- HorizontalPodAutoscaler for detection workers
- GPU node pool with NVIDIA device plugin
- Cert-manager for TLS, ExternalDNS for ingress

---

## 🧪 Testing

```bash
# Unit tests
cd smart-surveillance-app/backend && pytest -v

# Integration tests
pytest tests/integration -v --tb=short

# Load testing (locust)
locust -f tests/load/locustfile.py --host=http://localhost:8000
```

---

## 📊 Monitoring & Observability

- **Metrics**: Prometheus `/metrics` endpoint on each service
- **Logging**: Structured JSON logs (Loguru) → Loki/Grafana
- **Tracing**: OpenTelemetry → Jaeger (distributed traces)
- **Alerting**: AlertManager rules for system health + business alerts
- **Dashboards**: Grafana dashboards for detection rates, latency, GPU utilization

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feat/amazing-feature`
3. Commit changes: `git commit -m 'feat: add amazing feature'`
4. Push to branch: `git push origin feat/amazing-feature`
5. Open a Pull Request

### Code Style
- **Python**: Black (88 cols), Ruff, MyPy strict
- **JavaScript/React**: ESLint + Prettier, TypeScript strict mode
- **Commits**: Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`)

---

## 🗺️ Roadmap

- [ ] **v1.1** — Multi-language UI (i18n), ONNX Runtime Web for browser inference
- [ ] **v1.2** — Federation: multi-site management from single pane
- [ ] **v1.3** — LLM-powered incident summaries (Gemini/Ollama integration)
- [ ] **v1.4** — Edge deployment: Jetson Orin, Raspberry Pi 5 support
- [ ] **v2.0** — Behavior analysis: loitering, tailgating, violence detection

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 👨‍💻 Author

**Abhighayn Bakshi** — Systems Engineer (LLM Integration · Networking & Cloud Infrastructure)  
📍 Kolkata, West Bengal, India  
🔗 [GitHub](https://github.com/drakaris-ab) • [LinkedIn](https://linkedin.com/in/abhighayn-bakshi)

---

## 🙏 Acknowledgments

- [Ultralytics](https://github.com/ultralytics/ultralytics) for YOLOv11
- [InsightFace](https://github.com/deepinsight/insightface) for face recognition
- [aiortc](https://github.com/aiortc/aiortc) for WebRTC implementation
- [FastAPI](https://fastapi.tiangolo.com/) for the incredible framework