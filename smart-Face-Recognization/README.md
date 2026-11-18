# 👤 Smart Face Recognition Service

> **Standalone face recognition microservice** for enrollment, 1:N identification, liveness detection, and privacy-compliant face processing.

## 🏗️ Architecture

```
smart-Face-Recognization/
├── backend/                 # FastAPI service
│   ├── ai/                 # InsightFace models, inference
│   ├── config/             # Model paths, thresholds
│   ├── core/               # Exceptions, utilities
│   ├── database/           # Face embeddings storage (PostgreSQL + pgvector / FAISS)
│   ├── models/             # Pydantic schemas
│   ├── routers/            # API endpoints
│   ├── services/           # Business logic (enrollment, search, liveness)
│   ├── util/               # Image preprocessing, alignment
│   ├── main.py             # Entry point
│   └── requirements.txt
│
├── dist/                   # PyInstaller executable (Windows)
├── logs/                   # Runtime logs
├── insightface-*.whl       # Pre-built wheel for offline install
└── logo.ico                # App icon
```

## 🚀 Quick Start

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# Or install InsightFace wheel offline:
# pip install ../insightface-0.7.3-cp311-cp311-win_amd64.whl

# Configure .env
cp .env.example .env
# Set: DATABASE_URL, REDIS_URL, MODEL_PATH, THRESHOLDS

uvicorn main:app --reload --port 8001
```

## 🧠 AI Models

| Model | Purpose | Backend |
|-------|---------|---------|
| **RetinaFace** | Face detection (boxes + 5 landmarks) | ONNX Runtime |
| **ArcFace (ResNet-100)** | 512-dim embedding extraction | ONNX Runtime |
| **Gender/Age** | Demographic estimation | ONNX Runtime |
| **Liveness (Silent)** | Anti-spoofing (texture + motion) | Custom CNN |

## 📡 API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/enroll` | POST | Enroll new identity (multipart: image + metadata) |
| `/identify` | POST | 1:N search (image → top-K matches with scores) |
| `/verify` | POST | 1:1 verification (two images → similarity score) |
| `/liveness` | POST | Liveness check (video frames or image sequence) |
| `/gallery` | GET | List enrolled identities with pagination |
| `/gallery/{id}` | DELETE | Remove identity (GDPR right-to-erasure) |
| `/health` | GET | Service health + model load status |

## 🔧 Configuration

```bash
# .env
DATABASE_URL=postgresql://user:pass@localhost:5432/face_db
REDIS_URL=redis://localhost:6379/1

# Model paths
INSIGHTFACE_ROOT=./models/insightface
DET_MODEL=retinaface_mnet025_v2.onnx
REC_MODEL=arcface_r100.onnx
LIVENESS_MODEL=silent_liveness.onnx

# Thresholds
DET_THRESH=0.6
REC_THRESH=0.45      # Cosine similarity threshold for match
LIVENESS_THRESH=0.7
MAX_FACES_PER_IMAGE=10

# FAISS Index (for large-scale search)
FAISS_INDEX_PATH=./data/faiss_index.bin
FAISS_INDEX_TYPE=HNSW32
```

## 🔒 Privacy & Compliance

- **Embeddings encrypted at rest** (AES-256-GCM, key from KMS/env)
- **No raw images stored** — only embeddings + metadata
- **GDPR endpoints**: `/gallery/{id}` (DELETE), `/export/{id}` (GET)
- **Audit logging**: Every enroll/identify/verify logged with user context
- **Configurable retention**: Auto-purge embeddings after N days

## 📊 Performance

| Metric | Value |
|--------|-------|
| Detection latency (640x480) | ~15ms (GPU) / ~80ms (CPU) |
| Embedding extraction | ~8ms (GPU) / ~45ms (CPU) |
| 1:N search (100K faces, FAISS HNSW) | <5ms |
| Throughput (batch=4, GPU) | ~120 fps |

## 🐳 Docker

```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 📄 License

MIT — see root [LICENSE](../LICENSE)