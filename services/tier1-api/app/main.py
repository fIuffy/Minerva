"""Tier 1 — Federal data API (the final exfil target, §2.1 / §5.3 chain end).

A simulated federal data authority (benefits-eligibility / cross-check
repository). High-value, NOT externally reachable: it lives on net_federal with
no published ports. The only path to it is through the federation policy
checkpoint (fed-gateway), which enforces the broker-issued token. Reaching this
API completes the full cross-framework chain end to end.

The gateway is the single policy-enforcement point (§2.3): this service trusts
that anything able to reach it on net_federal has already passed the checkpoint.
That perimeter-trust assumption is itself part of the seam under study — if an
attacker rides the federation path (T1550), Tier 1 has no second line.

ALL RECORDS ARE FABRICATED. No real PII (§7). The "SSN" field is a synthetic
9-digit token in the reserved 900-xx-xxxx range that is never issued by the SSA.
"""
from fastapi import FastAPI, Header
from fastapi.responses import JSONResponse

app = FastAPI(title="Federal Data Authority (Tier 1)", docs_url=None, redoc_url=None)

# Synthetic federal cross-check records. 900-xx-xxxx is an invalid SSN range.
FEDERAL_RECORDS = {
    "F-100277": {
        "record_id": "F-100277", "full_name": "Dana R. Holloway",
        "ssn_synthetic": "900-41-7782", "federal_benefit_status": "ELIGIBLE",
        "tax_year_verified": 2025, "cross_check": "SSA+IRS match",
        "clearance_flag": False,
    },
    "F-100412": {
        "record_id": "F-100412", "full_name": "Marcus T. Bell",
        "ssn_synthetic": "900-55-1390", "federal_benefit_status": "UNDER_REVIEW",
        "tax_year_verified": 2024, "cross_check": "SSA match, IRS pending",
        "clearance_flag": True,
    },
    "F-100913": {
        "record_id": "F-100913", "full_name": "Priya N. Anand",
        "ssn_synthetic": "900-23-6651", "federal_benefit_status": "ELIGIBLE",
        "tax_year_verified": 2025, "cross_check": "SSA+IRS match",
        "clearance_flag": True,
    },
}


@app.get("/healthz")
def healthz():
    return {"status": "ok", "tier": 1, "role": "federal-data-authority"}


@app.get("/records/{record_id}")
def get_record(record_id: str, x_assurance: str | None = Header(default=None)):
    """Return a federal record. The gateway forwards the validated assurance
    tier in X-Assurance so Tier 1 can log the assurance level each access used
    (evidence for the federated-trust gap write-up)."""
    rec = FEDERAL_RECORDS.get(record_id)
    if not rec:
        return JSONResponse(status_code=404, content={"error": "no such federal record"})
    return {"served_by": "tier1-federal-api", "assurance_presented": x_assurance, "record": rec}


@app.get("/records")
def list_records(x_assurance: str | None = Header(default=None)):
    return {"count": len(FEDERAL_RECORDS), "record_ids": list(FEDERAL_RECORDS)}
