# 🎥 Smart Surveillance App — Main Platform

> **Core surveillance platform** with camera management, real-time WebRTC streaming, zone-based detection rules, alerting engine, and React dashboard.

## 🏗️ Architecture

```
smart-surveillance-app/
├── backend/                 # FastAPI backend
│   ├── auth/               # JWT authentication, RBAC
│   ├── config/             # Configuration management
│   ├── core/               # Core utilities, exceptions
│   ├── database/           # SQLAlchemy models, migrations
│   ├── detection/          # YOLO detection engine, trackers
│   ├── routers/            # API endpoints (cameras, zones, alerts, etc.)
│   ├── services/           # Business logic (alerts, archive, config)
│   ├── utils/              # Helpers, cache, shared state
│   ├── main.py             # FastAPI app entry point
│   ├── requirements.txt    # Python dependencies
│   └── .env                # Environment config
│
├── frontend/               # React 18 + Vite + Tailwind
│   ├── src/
│   │   ├── component/      # Reusable UI components
│   │   ├── constants/      # App constants, enums
│   │   ├── context/        # React context providers
│   │   ├── core/           # Core utilities, API client
│   │   ├── hooks/          # Custom React hooks
│   │   ├── layout/         # Page layouts
│   │   ├── modules/        # Feature modules (cameras, alerts, etc.)
│   │   ├── services/       # API services, WebSocket
│   │   ├── store/          # State management (Zustand/Redux)
│   │   ├── styles/         # Global styles, Tailwind config
│   │   ├── utils/          # Helpers
│   │   ├── App.js          # Root component
│   │   └── index.js        # Entry point
│   ├── package.json
│   └── vite.config.js
│
└── assets/                 # Static assets
```

## 🚀 Quick Start

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # Configure your settings
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```

## 🔧 Key Features

| Feature | Description |
|---------|-------------|
| **Camera Management** | RTSP/WebRTC streams, health monitoring, PTZ control |
| **Zone Configuration** | Canvas-based polygon drawing, rule assignment per zone |
| **Real-time Detection** | YOLOv11 inference, DeepSORT tracking, WebSocket push |
| **Alert Engine** | Rule-based alerts, cooldown, escalation, multi-channel notify |
| **WebRTC Streaming** | Sub-second latency, ICE/TURN support, adaptive bitrate |
| **Face Integration** | Calls Face Recognition service for 1:N matching |
| **Object Integration** | Calls Unattended Object service for abandonment detection |
| **Archive & Search** | Event storage, video clips, forensic search |
| **Multi-tenancy** | Organization/project isolation, RBAC |

## 📡 API Endpoints

| Module | Endpoints |
|--------|-----------|
| **Cameras** | `GET/POST /cameras`, `GET/PUT/DELETE /cameras/{id}`, `GET /cameras/{id}/stream` |
| **Zones** | `GET/POST /zones`, `GET/PUT/DELETE /zones/{id}` |
| **Alerts** | `GET /alerts`, `POST /alerts/{id}/acknowledge`, `GET /alerts/stats` |
| **Detections** | `WS /ws/detections`, `GET /detections/history` |
| **Faces** | `POST /faces/enroll`, `POST /faces/identify`, `GET /faces/gallery` |
| **Objects** | `GET /objects/unattended`, `GET /objects/timeline` |
| **Config** | `GET/PUT /config/global`, `GET/PUT /config/camera/{id}` |
| **Auth** | `POST /auth/login`, `POST /auth/refresh`, `GET /auth/me` |

## 🐳 Docker

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```dockerfile
# frontend/Dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## 🧪 Testing

```bash
# Backend
cd backend
pytest -v --cov=app --cov-report=html

# Frontend
cd frontend
npm run test        # Vitest
npm run test:coverage
npm run lint        # ESLint
```

## 📦 Deployment

See root [README.md](../README.md#-deployment) for Docker Compose and Kubernetes deployment.

---

## 📄 License

MIT — see root [LICENSE](../LICENSE)