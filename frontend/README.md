# TensorForge 2.0 — Frontend Demo & Operations Dashboard

This directory houses the complete frontend application for the **RideEat Support Ticket Intelligence** platform (Deliverable #1).

## 🚀 Features

- **Single Ticket Workbench**: Interactive testbed for multilingual classification (`en`, `si`, `ta`, `singlish`, `tanglish`, `mixed`).
- **Synchronous Batch Tester (1-100 tickets)**: Instant evaluation table with response latency indicators.
- **Async Bulk Job Operations (up to 5,000 tickets)**: Live progress monitoring, real-time polling, and result viewer with cancellation support.
- **Dynamic Routing Visualizer**: Reference map for the 11 categories and their corresponding support departments.
- **Direct Backend Integration**: Seamlessly served by FastAPI when running the container, or runnable independently with Vite.

## 📁 Structure

```
frontend/
├── index.html               # Main dashboard web application
├── package.json             # NPM package scripts (optional Vite dev server)
├── public/                  # Static assets & test fixtures
│   └── sample_tickets.json  # Multilingual sample tickets
├── src/
│   ├── assets/              # Stylesheets & font styling
│   │   └── style.css
│   ├── components/          # Reusable UI component modules
│   └── services/            # API client service
│       └── api.js           # Fetch wrapper for all backend routes
└── README.md
```

## 🛠 Running the Frontend

### Option 1: Directly via the FastAPI Backend (Recommended for Docker & Submissions)
When the FastAPI backend starts (`uvicorn src.api.app:app --port 8000` or `docker run`), it automatically mounts and serves this frontend at:
```
http://localhost:8000/
```

### Option 2: Independent Development Server
If developing frontend components independently:
```bash
cd frontend
npm install
npm run dev
```
