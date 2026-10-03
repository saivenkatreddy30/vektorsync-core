import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from vektorsync.core.database import get_db, DocumentLedger, MutationJournal, SnapshotLedger
from vektorsync.core.schemas import SyncEnvelopeRequest, SyncEnvelopeResponse, SynchronizationResult, CausalRelation
from vektorsync.engine.causal_horizon import CausalHorizonArbiter
from vektorsync.engine.tripartite_differ import TripartiteStructuralDiffer

router = APIRouter(prefix="/api/v1/sync", tags=["VektorSync Engine"])

@router.post("/push", response_model=SyncEnvelopeResponse)
def push_synchronization_envelope(request: SyncEnvelopeRequest, db: Session = Depends(get_db)):
    # 1. Idempotency Guard
    prior_entry = db.query(MutationJournal).filter_by(idempotency_key=request.idempotency_key).first()
    if prior_entry:
        active_doc = db.query(DocumentLedger).filter_by(id=request.document_id).first()
        return SyncEnvelopeResponse(
            result=SynchronizationResult(prior_entry.sync_result),
            document_id=request.document_id,
            current_version=active_doc.version,
            current_vector_clock=json.loads(active_doc.vector_clock),
            current_data=json.loads(active_doc.data_payload),
            details="Idempotent replay: transaction previously committed."
        )

    doc = db.query(DocumentLedger).filter_by(id=request.document_id).first()

    # 2. Genesis Ingestion
    if not doc:
        origin_clock = {request.client_id: 1}
        doc = DocumentLedger(
            id=request.document_id,
            version=1,
            vector_clock=json.dumps(origin_clock),
            data_payload=json.dumps(request.payload),
            last_modified_by=request.client_id
        )
        db.add(doc)
        db.add(SnapshotLedger(document_id=doc.id, version=1, data_payload=doc.data_payload, vector_clock=doc.vector_clock))
        db.add(MutationJournal(document_id=doc.id, client_id=request.client_id, idempotency_key=request.idempotency_key, sync_result=SynchronizationResult.CHANGE_ACCEPTED.value, payload_snapshot=doc.data_payload))
        db.commit()
        db.refresh(doc)
        return SyncEnvelopeResponse(
            result=SynchronizationResult.CHANGE_ACCEPTED,
            document_id=doc.id,
            current_version=doc.version,
            current_vector_clock=origin_clock,
            current_data=request.payload,
            details="Genesis document established."
        )

    server_clock = json.loads(doc.vector_clock)
    server_data = json.loads(doc.data_payload)

    # 3. Vector Clock Causality Analysis
    causal_relation = CausalHorizonArbiter.inspect_causality(request.base_vector_clock, server_clock)

    # 4. Fast-Forward: Linear Descendant
    if causal_relation in (CausalRelation.COINCIDENT, CausalRelation.CAUSAL_DESCENDANT):
        updated_clock = CausalHorizonArbiter.reconcile_vector_clocks(server_clock, request.client_vector_clock, request.client_id)
        doc.version += 1
        doc.vector_clock = json.dumps(updated_clock)
        doc.data_payload = json.dumps(request.payload)
        doc.last_modified_by = request.client_id

        db.add(SnapshotLedger(document_id=doc.id, version=doc.version, data_payload=doc.data_payload, vector_clock=doc.vector_clock))
        db.add(MutationJournal(document_id=doc.id, client_id=request.client_id, idempotency_key=request.idempotency_key, sync_result=SynchronizationResult.CHANGE_ACCEPTED.value, payload_snapshot=doc.data_payload))
        db.commit()

        return SyncEnvelopeResponse(
            result=SynchronizationResult.CHANGE_ACCEPTED,
            document_id=doc.id,
            current_version=doc.version,
            current_vector_clock=updated_clock,
            current_data=request.payload,
            details="Linear causal mutation accepted."
        )

    # 5. Concurrent Divergence -> 3-Way Reconciler
    ancestor_snapshot = db.query(SnapshotLedger).filter_by(document_id=doc.id, version=request.base_version).first()
    base_data = json.loads(ancestor_snapshot.data_payload) if ancestor_snapshot else {}

    clean_merge, unified_data, conflict_manifest, ai_invoked = TripartiteStructuralDiffer.execute_3way_reconciliation(
        base_data, server_data, request.payload
    )

    if clean_merge:
        updated_clock = CausalHorizonArbiter.reconcile_vector_clocks(server_clock, request.client_vector_clock, request.client_id)
        doc.version += 1
        doc.vector_clock = json.dumps(updated_clock)
        doc.data_payload = json.dumps(unified_data)
        doc.last_modified_by = request.client_id

        db.add(SnapshotLedger(document_id=doc.id, version=doc.version, data_payload=doc.data_payload, vector_clock=doc.vector_clock))
        db.add(MutationJournal(document_id=doc.id, client_id=request.client_id, idempotency_key=request.idempotency_key, sync_result=SynchronizationResult.CHANGES_MERGED.value, payload_snapshot=doc.data_payload))
        db.commit()

        return SyncEnvelopeResponse(
            result=SynchronizationResult.CHANGES_MERGED,
            document_id=doc.id,
            current_version=doc.version,
            current_vector_clock=updated_clock,
            current_data=unified_data,
            details="Non-conflicting orthogonal fields merged without data loss.",
            ai_reconciled=ai_invoked
        )
    else:
        db.add(MutationJournal(document_id=doc.id, client_id=request.client_id, idempotency_key=request.idempotency_key, sync_result=SynchronizationResult.CONFLICT_REQUIRING_RESOLUTION.value, payload_snapshot=json.dumps(request.payload)))
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "result": SynchronizationResult.CONFLICT_REQUIRING_RESOLUTION.value,
                "document_id": doc.id,
                "current_version": doc.version,
                "current_data": server_data,
                "conflicts": conflict_manifest,
                "message": "Concurrent mutations diverged semantically. Safe automated merge halted."
            }
        )

@router.get("/pull/{document_id}")
def pull_latest_state(document_id: str, db: Session = Depends(get_db)):
    doc = db.query(DocumentLedger).filter_by(id=document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Specified document corpus does not exist.")
    return {
        "document_id": doc.id,
        "version": doc.version,
        "vector_clock": json.loads(doc.vector_clock),
        "data": json.loads(doc.data_payload),
        "last_modified_by": doc.last_modified_by,
        "updated_at": doc.updated_at
    }