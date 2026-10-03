"""Validate sample prediction responses and error responses against official JSON Schemas."""

import json
from pathlib import Path
import jsonschema
from jsonschema.validators import validator_for

SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"


def load_schema(schema_filename: str) -> dict:
    filepath = SCHEMAS_DIR / schema_filename
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_payload(schema_dict: dict, payload: dict) -> bool:
    validator_cls = validator_for(schema_dict)
    validator_cls.check_schema(schema_dict)
    validator = validator_cls(schema_dict)
    validator.validate(payload)
    return True


def main():
    print("=" * 60)
    print("TensorForge 2.0 -- Schema Compliance Verification")
    print("=" * 60)

    # 1. Health Response Schema
    print("\n[1] Testing HealthResponse against health_response.schema.json...")
    health_schema = load_schema("health_response.schema.json")
    health_sample = {"status": "ok", "model_version": "v1.0", "model_loaded": True}
    validate_payload(health_schema, health_sample)
    print("  [OK] HealthResponse valid!")

    # 2. Predict Request Schema
    print("\n[2] Testing PredictRequest against predict_request.schema.json...")
    req_schema = load_schema("predict_request.schema.json")
    req_sample = {
        "ticket_id": "TF-TE-000001",
        "channel": "chat",
        "subject": "",
        "text": "late delivery and refund"
    }
    validate_payload(req_schema, req_sample)
    print("  [OK] PredictRequest valid!")

    # 3. Predict Response Schema
    print("\n[3] Testing PredictResponse against predict_response.schema.json...")
    res_schema = load_schema("predict_response.schema.json")
    res_sample = {
        "ticket_id": "TF-TE-000001",
        "category": "delivery_delay",
        "secondary_category": "payment_refund",
        "team": "Delivery Operations",
        "is_urgent": False,
        "confidence": 0.88,
        "model_version": "v1.0"
    }
    validate_payload(res_schema, res_sample)
    print("  [OK] PredictResponse valid!")

    # 4. Error Response Schema
    print("\n[4] Testing ErrorResponse against error_response.schema.json...")
    err_schema = load_schema("error_response.schema.json")
    err_sample = {
        "error": {
            "code": "validation_error",
            "message": "Field 'text' must not be empty.",
            "details": [{"index": 0, "field": "text", "issue": "must not be empty"}]
        }
    }
    validate_payload(err_schema, err_sample)
    print("  [OK] ErrorResponse valid!")

    print("\nAll JSON Schema validations PASSED successfully!")


if __name__ == "__main__":
    main()
