import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from vektorsync.core.database import get_db, DocumentLedger, SnapshotLedger
from vektorsync.core.schemas import RevisionRollbackRequest

router = APIRouter(prefix="/api/v1/lineage", tags=["Lineage & Version Recovery"])

@router.get("/{document_id}/history")
def inspect_revision_lineage(document_id: str, db: Session = Depends(get_db)):
    snapshots = db.query(SnapshotLedger).filter_by(document_id=document_id).order_by(SnapshotLedger.version.asc()).all()
    if not snapshots:
        raise HTTPException(status_code=404, detail="No revision lineage recorded.")
    
    return [
        {
            "version": s.version,
            "data": json.loads(s.data_payload),
            "vector_clock": json.loads(s.vector_clock),
            "timestamp": s.created_at
        }
        for s in snapshots
    ]

@router.post("/{document_id}/restore")
def restore_historical_version(document_id: str, request: RevisionRollbackRequest, db: Session = Depends(get_db)):
    target = db.query(SnapshotLedger).filter_by(document_id=document_id, version=request.target_version).first()
    if not target:
        raise HTTPException(status_code=404, detail="Requested version snapshot does not exist.")

    doc = db.query(DocumentLedger).filter_by(id=document_id).first()
    clock = json.loads(doc.vector_clock)
    clock[request.client_id] = clock.get(request.client_id, 0) + 1

    doc.version += 1
    doc.data_payload = target.data_payload
    doc.vector_clock = json.dumps(clock)
    doc.last_modified_by = f"{request.client_id} (Reverted to v{request.target_version})"

    db.add(SnapshotLedger(document_id=doc.id, version=doc.version, data_payload=doc.data_payload, vector_clock=doc.vector_clock))
    db.commit()

    return {
        "status": "RESTORED",
        "active_version": doc.version,
        "restored_from": request.target_version,
        "current_data": json.loads(doc.data_payload)
    }