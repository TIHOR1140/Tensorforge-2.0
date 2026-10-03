# TensorForge 2.0 — Phase 2: Customer Support Ticket Classification and Routing System

[![API](https://img.shields.io/badge/API-FastAPI-009688.svg)](https://fastapi.tiangolo.com)
[![Specification](https://img.shields.io/badge/OpenAPI-3.0.3-6BA539.svg)](https://swagger.io/specification/)
[![JSON Schema](https://img.shields.io/badge/Schema-Draft%202020--12-blue.svg)](https://json-schema.org/)
[![Status](https://img.shields.io/badge/Build-Passing-brightgreen.svg)]()

This repository contains the complete end-to-end MVP solution for **TensorForge 2.0 Phase 2**, organized by IEEE Computer Society KDU. The system implements an intelligent customer support ticket classification and automated routing engine for the fictional **RideEat** ride-hailing and food delivery platform.

---

## 📂 Project Architecture & Directory Structure

The repository is modularly structured for maintainability, offline container execution, and collaborative development:

```
Tensorforge-2.0/
├── data/
│   ├── raw/                 # Official training and validation datasets (train.csv, validation.csv, DATA_NOTES.md)
│   └── processed/           # Processed and augmented dataset splits
│
├── frontend/                # [DELIVERABLE #1] Interactive Demo Site & Dashboard
│   ├── index.html           # Main interactive dashboard entrypoint
│   ├── package.json         # Optional Vite development toolchain
│   ├── public/              # Static sample files (sample_tickets.json)
│   └── src/
│       ├── assets/          # Stylesheets and branding
│       └── services/        # Frontend API client (api.js)
│
├── schemas/                 # Official competition OpenAPI spec & JSON schemas
│   ├── tensorforge-phase2-openapi-v2.yaml
│   ├── tensorforge-schemas.json
│   └── *.schema.json        # Strict draft 2020-12 validation schemas
│
├── src/                     # Production backend source code
│   ├── api/                 # FastAPI application, routing, and error handlers
│   │   ├── app.py           # App initialization, middleware, static mounts
│   │   ├── dependencies.py  # Constant-time API Key auth & X-Request-ID echo
│   │   ├── error_handlers.py# Strict 400/401/413/415/422 JSON error formatters
│   │   └── routes/          # Core & bulk evaluation endpoints (/health, /predict, /batch/jobs)
│   ├── core/                # Configuration, constants, and category mappings
│   ├── models/              # ML inference pipeline, preprocessors, consistency rules
│   ├── schemas/             # Pydantic data models mirroring OpenAPI & JSON schemas
│   ├── services/            # Async batch job manager & prediction orchestrator
│   └── ui/                  # Fallback UI templates
│
├── ml/                      # Machine learning experiments, training, and evaluation
│   ├── training/            # Model training pipelines (train.py)
│   ├── evaluation/          # F1 metrics, validation routines, error analysis
│   ├── notebooks/           # Jupyter exploratory notebooks
│   └── artifacts/           # Exported offline model checkpoints and tokenizers
│
├── docker/                  # Docker containerization & deployment
│   ├── Dockerfile           # Multi-stage offline Dockerfile (starts < 120s, offline runtime)
│   ├── docker-compose.yml   # Local container orchestration
│   └── .dockerignore        # Lean image build filters
│
├── docs/                    # Competition deliverables documentation
│   ├── architecture.md      # Detailed system architecture and design choices
│   ├── report_template.md   # Structure for the 5-page submission report
│   └── video_outline.md     # 15-minute video presentation outline
│
├── scripts/                 # Automation and utility scripts
│   ├── validate_schemas.py  # Local JSON Schema compliance test
│   └── benchmark.py         # Latency and throughput benchmark
│
├── tests/                   # Automated pytest test suite
│   ├── unit/                # Preprocessor and consistency rules tests
│   ├── integration/         # Endpoint and auth tests
│   └── schema/              # Schema validation test suite
│
├── .gitignore               # Comprehensive Git ignore rules
└── requirements.txt         # Production pinned dependencies
```

---

## ⚡ Quickstart

### 1. Prerequisites
- Python 3.11+
- Git

### 2. Environment Setup
```bash
# Clone the repository
git clone https://github.com/your-team/Tensorforge-2.0.git
cd Tensorforge-2.0

# Install dependencies
pip install -r requirements.txt
```

### 3. Running the Service Locally
Set your team's `API_KEY` environment variable and launch the server:

**Windows (PowerShell):**
```powershell
$env:API_KEY="your-secret-api-key"
uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload
```

**Linux / macOS:**
```bash
export API_KEY="your-secret-api-key"
uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Accessing the Services
- **Interactive Dashboard (Frontend)**: [http://localhost:8000/](http://localhost:8000/)
- **Interactive OpenAPI Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Public Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

---

## 🐳 Docker Deployment (Competition Contract)

Per the competition guidelines, the container runs offline with a single command:

```bash
# Build the image
docker build -t tensorforge-mvp -f docker/Dockerfile .

# Run the container
docker run -p 8000:8000 -e API_KEY="your-secret-api-key" tensorforge-mvp
```

The container starts and satisfies all conditions:
- Listens on `0.0.0.0:8000`
- Model weights are bundled inside the image — **no runtime internet access required**
- `/health` responds with HTTP `200` within 120 seconds of start.

---

## 🧠 Model Training

To train the multilingual classifier and export model artifacts:
```bash
python ml/training/train.py
```
This trains:
1. **Primary Category Classifier** (11 categories)
2. **Secondary Category Classifier** (with null handling)
3. **Urgency Flag Classifier** (binary)

Artifacts are saved to `ml/artifacts/` and automatically picked up by the API service at startup.

---

## 🛡️ Consistency Rules Enforced

The pipeline strictly guarantees the competition consistency rules:
1. **Category to Team Mapping**:
   | Category | Team |
   |---|---|
   | `payment_refund` | `Payments & Refunds` |
   | `ride_trip_issue` | `Ride Operations` |
   | `lost_item` | `Lost & Found` |
   | `order_missing_wrong` | `Food Operations` |
   | `delivery_delay` | `Delivery Operations` |
   | `food_quality` | `Restaurant Quality` |
   | `account_promo` | `Account Services` |
   | `safety_conduct` | `Trust & Safety` |
   | `app_technical` | `Tech Support` |
   | `general_inquiry` | `Front-line Support` |
   | `spam_irrelevant` | `Auto-close / Spam Filter` |
2. `secondary_category` strictly differs from `category` (or evaluates to `null`).
3. If `category == spam_irrelevant`, `is_urgent` is guaranteed `false` and `secondary_category` is guaranteed `null`.
4. Authorization is enforced before request parsing; invalid credentials immediately return `401`.
5. Non-blocking asynchronous job queue supports up to 5,000 tickets per job with real-time polling and pagination.
