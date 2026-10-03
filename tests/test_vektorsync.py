import pytest
from fastapi.testclient import TestClient
from vektorsync.main import app
from vektorsync.core.database import Base, engine

client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_ledger():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield

def test_genesis_document_accepted():
    payload = {
        "client_id": "node_station_orion",
        "document_id": "corpus_system_manifest",
        "base_version": 1,
        "base_vector_clock": {},
        "client_vector_clock": {"node_station_orion": 1},
        "payload": {"protocol": "TLS_1_3", "telemetry": "Active", "notes": "Nominal"},
        "idempotency_key": "idemp-genesis-01"
    }
    response = client.post("/api/v1/sync/push", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["result"] == "Change accepted"
    assert data["current_version"] == 1

def test_non_conflicting_field_level_merge():
    # 1. Establish base state
    client.post("/api/v1/sync/push", json={
        "client_id": "node_station_orion", "document_id": "corpus_system_manifest", "base_version": 1,
        "base_vector_clock": {}, "client_vector_clock": {"node_station_orion": 1},
        "payload": {"protocol": "TLS_1_3", "status": "Staging", "lead": "Dr. Sarah"},
        "idempotency_key": "idemp-01"
    })

    # 2. Node Orion changes 'status' offline
    client.post("/api/v1/sync/push", json={
        "client_id": "node_station_orion", "document_id": "corpus_system_manifest", "base_version": 1,
        "base_vector_clock": {"node_station_orion": 1}, "client_vector_clock": {"node_station_orion": 2},
        "payload": {"protocol": "TLS_1_3", "status": "Production", "lead": "Dr. Sarah"},
        "idempotency_key": "idemp-02"
    })

    # 3. Node Aquila independently modified 'lead' from base v1 (concurrent, non-overlapping)
    res = client.post("/api/v1/sync/push", json={
        "client_id": "node_terminal_aquila", "document_id": "corpus_system_manifest", "base_version": 1,
        "base_vector_clock": {"node_station_orion": 1}, "client_vector_clock": {"node_terminal_aquila": 1},
        "payload": {"protocol": "TLS_1_3", "status": "Staging", "lead": "Dr. Miller"},
        "idempotency_key": "idemp-03"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["result"] == "Changes merged"
    assert data["current_data"]["status"] == "Production"
    assert data["current_data"]["lead"] == "Dr. Miller"

def test_latent_semantic_ai_convergence():
    client.post("/api/v1/sync/push", json={
        "client_id": "node_field_vanguard", "document_id": "corpus_telemetry_report", "base_version": 1,
        "base_vector_clock": {}, "client_vector_clock": {"node_field_vanguard": 1},
        "payload": {"assessment": "Telemetry data rate has stabilized"},
        "idempotency_key": "idemp-ai-01"
    })

    client.post("/api/v1/sync/push", json={
        "client_id": "node_field_vanguard", "document_id": "corpus_telemetry_report", "base_version": 1,
        "base_vector_clock": {"node_field_vanguard": 1}, "client_vector_clock": {"node_field_vanguard": 2},
        "payload": {"assessment": "Telemetry data rate has stabilized completely"},
        "idempotency_key": "idemp-ai-02"
    })

    res = client.post("/api/v1/sync/push", json={
        "client_id": "node_terminal_aquila", "document_id": "corpus_telemetry_report", "base_version": 1,
        "base_vector_clock": {"node_field_vanguard": 1}, "client_vector_clock": {"node_terminal_aquila": 1},
        "payload": {"assessment": "Telemetry data rate is stabilized completely"},
        "idempotency_key": "idemp-ai-03"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["result"] == "Changes merged"
    assert data["ai_reconciled"] is True

def test_divergent_semantic_conflict_returns_409():
    client.post("/api/v1/sync/push", json={
        "client_id": "node_station_orion", "document_id": "corpus_mission_orders", "base_version": 1,
        "base_vector_clock": {}, "client_vector_clock": {"node_station_orion": 1},
        "payload": {"directive": "Proceed with orbital injection"},
        "idempotency_key": "idemp-div-01"
    })

    client.post("/api/v1/sync/push", json={
        "client_id": "node_station_orion", "document_id": "corpus_mission_orders", "base_version": 1,
        "base_vector_clock": {"node_station_orion": 1}, "client_vector_clock": {"node_station_orion": 2},
        "payload": {"directive": "Proceed with orbital injection immediately"},
        "idempotency_key": "idemp-div-02"
    })

    res = client.post("/api/v1/sync/push", json={
        "client_id": "node_field_vanguard", "document_id": "corpus_mission_orders", "base_version": 1,
        "base_vector_clock": {"node_station_orion": 1}, "client_vector_clock": {"node_field_vanguard": 1},
        "payload": {"directive": "Abort orbital injection and vent fuel"},
        "idempotency_key": "idemp-div-03"
    })
    assert res.status_code == 409
    body = res.json()
    assert body["detail"]["result"] == "Conflict requiring resolution"
    assert "directive" in body["detail"]["conflicts"]