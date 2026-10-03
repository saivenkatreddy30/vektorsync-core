from fastapi import FastAPI
from vektorsync.api.sync_router import router as sync_router
from vektorsync.api.lineage_router import router as lineage_router

app = FastAPI(
    title="VektorSync Distributed Engine",
    description="Offline-first distributed synchronization engine with Vector Clocks, Tripartite Merging, and Latent Semantic ML Arbitration.",
    version="1.0.0"
)

app.include_router(sync_router)
app.include_router(lineage_router)

@app.get("/health", tags=["Diagnostic"])
def diagnostic_probe():
    return {
        "status": "OPERATIONAL",
        "engine": "VektorSync Causal Horizon Arbiter v1.0",
        "supported_outcomes": [
            "Change accepted",
            "Change rejected",
            "Changes merged",
            "Conflict requiring resolution"
        ]
    }