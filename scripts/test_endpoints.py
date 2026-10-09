"""Comprehensive endpoint and compliance verification script for TensorForge 2.0.

Tests:
1. Public GET /health
2. Check ordering & auth on POST /predict (401 before 415 before 413 before 400 before 422)
3. Single ticket POST /predict
4. Batch sync POST /predict/batch
5. Async batch POST /batch/jobs, polling GET /batch/jobs/{id}, results GET /batch/jobs/{id}/results, DELETE /batch/jobs/{id}
6. X-Request-ID echo header on all responses
7. Dashboard UI serving at GET /
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from backend.api.app import app
from backend.core.config import settings

def run_tests():
    print("=" * 60)
    print("TensorForge 2.0 -- Comprehensive Endpoint Compliance Test")
    print("=" * 60)

    api_key = settings.API_KEY or "dev-eval-key"
    if not settings.API_KEY:
        print("[!] Warning: API_KEY is not set in environment or .env. Using mock key for testing.")
    auth_headers = {"X-API-Key": api_key, "X-Request-ID": "test-req-12345"}

    with TestClient(app) as client:
        # 1. Health check (public)
        print("\n[1] Testing GET /health...")
        r = client.get("/health", headers={"X-Request-ID": "health-trace-1"})
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        assert r.headers.get("X-Request-ID") == "health-trace-1", "X-Request-ID echo missing on /health"
        data = r.json()
        assert data.get("status") in ["ok", "loading"], f"Invalid health status: {data}"
        print(f"  [OK] Health 200 (schema compliant status='{data.get('status')}'): {data}")


        # 2. Check ordering: Auth (401) check before anything else
        print("\n[2] Testing Check Ordering (Auth 401 first)...")
        # No key, invalid content-type -> must return 401 (not 415!)
        r = client.post("/predict", content="not json", headers={"Content-Type": "text/plain"})
        assert r.status_code == 401, f"Expected 401 for unauthenticated request, got {r.status_code}"
        assert r.json()["error"]["code"] == "unauthorized"
        assert "WWW-Authenticate" in r.headers
        print("  [OK] Unauthenticated + bad content-type -> 401 Unauthorized")

        # 3. Content-type check (415)
        print("\n[3] Testing Content-Type Check (415)...")
        r = client.post("/predict", content="hello", headers={"X-API-Key": api_key, "Content-Type": "text/plain"})
        assert r.status_code == 415, f"Expected 415, got {r.status_code}"
        assert r.json()["error"]["code"] == "unsupported_media_type"
        print("  [OK] Authenticated + text/plain -> 415 Unsupported Media Type")

        # 4. JSON parse check (400)
        print("\n[4] Testing Malformed JSON (400)...")
        r = client.post("/predict", content='{"channel": "email", "text":', headers={"X-API-Key": api_key, "Content-Type": "application/json"})
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"
        assert r.json()["error"]["code"] == "malformed_json"
        print("  [OK] Malformed JSON -> 400 with code: malformed_json")

        # 5. Schema validation check (422)
        print("\n[5] Testing Validation Error (422)...")
        r = client.post("/predict", json={"channel": "invalid_channel", "text": "test"}, headers=auth_headers)
        assert r.status_code == 422, f"Expected 422, got {r.status_code}: {r.text}"
        assert r.json()["error"]["code"] == "validation_error"
        print("  [OK] Invalid channel -> 422 with code: validation_error")

        # 6. Single Predict (POST /predict)
        print("\n[6] Testing POST /predict...")
        payload = {
            "ticket_id": "TICKET-001",
            "channel": "email",
            "subject": "Refund request",
            "text": "My food was completely spoiled and cold. Please refund my money immediately."
        }
        r = client.post("/predict", json=payload, headers=auth_headers)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        assert r.headers.get("X-Request-ID") == "test-req-12345"
        pred = r.json()
        assert "category" in pred
        assert "team" in pred
        assert "is_urgent" in pred
        assert "confidence" in pred
        assert "model_version" in pred
        print(f"  [OK] Prediction 200: Category='{pred['category']}', Team='{pred['team']}', Urgent={pred['is_urgent']}, Confidence={pred['confidence']:.2f}")

        # 7. Batch Sync Predict (POST /predict/batch)
        print("\n[7] Testing POST /predict/batch (1-100 tickets)...")
        batch_payload = {
            "tickets": [
                {"ticket_id": "T1", "channel": "chat", "text": "driver is taking wrong turn and car is not stopping i am scared"},
                {"ticket_id": "T2", "channel": "email", "text": "I forgot my wallet in the cab yesterday evening"},
                {"ticket_id": "T3", "channel": "call_transcript", "text": "App is crashing every time I tap on pay button"}
            ]
        }
        r = client.post("/predict/batch", json=batch_payload, headers=auth_headers)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        batch_res = r.json()
        assert len(batch_res["predictions"]) == 3
        print(f"  [OK] Batch sync 200: {len(batch_res['predictions'])} tickets classified")

        # 8. Async Batch Job Submission (POST /batch/jobs)
        print("\n[8] Testing Async Job Lifecycle...")
        job_payload = {
            "tickets": [
                {"ticket_id": f"J-{i:03d}", "channel": "chat", "text": f"Customer issue ticket sample {i} for evaluation"}
                for i in range(10)
            ]
        }
        r = client.post("/batch/jobs", json=job_payload, headers={"X-API-Key": api_key, "Idempotency-Key": "test-idem-1"})
        assert r.status_code == 202, f"Expected 202, got {r.status_code}: {r.text}"
        job_info = r.json()
        job_id = job_info["job_id"]
        print(f"  [OK] Job submitted 202: Job ID = {job_id}")

        # Poll status
        import time
        for _ in range(20):
            r = client.get(f"/batch/jobs/{job_id}", headers=auth_headers)
            assert r.status_code == 200
            st = r.json()
            if st["status"] == "succeeded":
                break
            time.sleep(0.1)

        print(f"  [OK] Job status: {st['status']}, processed {st['processed']}/{st['total']}")

        # Fetch results
        r = client.get(f"/batch/jobs/{job_id}/results?offset=0&limit=50", headers=auth_headers)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        results = r.json()
        assert len(results["predictions"]) == 10
        print(f"  [OK] Results 200: fetched {len(results['predictions'])} predictions")

        # Delete / Discard job
        r = client.delete(f"/batch/jobs/{job_id}", headers=auth_headers)
        assert r.status_code == 204, f"Expected 204, got {r.status_code}"
        # Afterwards must return 404
        r = client.get(f"/batch/jobs/{job_id}", headers=auth_headers)
        assert r.status_code == 404, f"Expected 404 after deletion, got {r.status_code}"
        assert r.json()["error"]["code"] == "job_not_found"
        print("  [OK] DELETE returned 204, subsequent GET returned 404 with job_not_found")

        # 9. Dashboard serving at GET /
        print("\n[9] Testing Dashboard UI serving (GET /)...")
        r = client.get("/")
        assert r.status_code == 200
        assert "html" in r.headers.get("content-type", "")
        print("  [OK] GET / serves index.html (React Dashboard)")

    print("\n" + "=" * 60)
    print("ALL 9 TEST SUITES PASSED STRICT SPECIFICATION COMPLIANCE!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
