from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

# 1. Exact string outcomes mandated by GDG Section 6
class SynchronizationResult(str, Enum):
    CHANGE_ACCEPTED = "Change accepted"
    CHANGE_REJECTED = "Change rejected"
    CHANGES_MERGED = "Changes merged"
    CONFLICT_REQUIRING_RESOLUTION = "Conflict requiring resolution"

# 2. Causal relationship classifications derived from Vector Clocks
class CausalRelation(str, Enum):
    COINCIDENT = "COINCIDENT"
    CAUSAL_ANCESTOR = "CAUSAL_ANCESTOR"
    CAUSAL_DESCENDANT = "CAUSAL_DESCENDANT"
    CONCURRENT_BRANCH = "CONCURRENT_BRANCH"

# 3. Inbound request schema for offline sync mutations
class SyncEnvelopeRequest(BaseModel):
    client_id: str = Field(..., examples=["node_station_orion"])
    document_id: str = Field(..., examples=["corpus_system_manifest"])
    base_version: int = Field(..., description="Snapshot revision when client went offline", examples=[1])
    base_vector_clock: Dict[str, int] = Field(..., description="Causal horizon at edit start", examples=[{"node_station_orion": 1}])
    client_vector_clock: Dict[str, int] = Field(..., description="Client incremented clock vector", examples=[{"node_station_orion": 2}])
    payload: Dict[str, Any] = Field(..., description="Field-level document content dictionary", examples=[{"directive": "Maintain telemetry standard"}])
    idempotency_key: str = Field(..., description="Unique key to guarantee at-most-once processing", examples=["idemp-orion-9921-x7"])

# 4. Outbound response schema confirming synchronization status
class SyncEnvelopeResponse(BaseModel):
    result: SynchronizationResult
    document_id: str
    current_version: int
    current_vector_clock: Dict[str, int]
    current_data: Dict[str, Any]
    details: str
    conflicts: Optional[Dict[str, Any]] = None
    ai_reconciled: bool = False

# 5. Schema to rollback a document to an earlier historical version
class RevisionRollbackRequest(BaseModel):
    target_version: int
    client_id: str