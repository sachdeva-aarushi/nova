"""
backend/api/routes_retrieval.py — Qdrant retrieval stub.

Endpoints
---------
GET /api/retrieval/{case_id}  →  RetrievalResponse
"""
from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter

router = APIRouter(prefix="/retrieval", tags=["retrieval"])


class RetrievalResponse(BaseModel):
    case_id: str
    matches: list  # list[HistoricalMatch] — populated in feat/data-simulator
    pipeline_steps: dict[str, float]  # step_name → latency_ms


from backend.memory.client import QdrantMemoryClient
from backend.memory.hybrid_search import hybrid_search

@router.get("/{case_id}", response_model=RetrievalResponse)
async def get_retrieval(case_id: str) -> RetrievalResponse:
    # REAL: queries Qdrant vector memory collection via hybrid_search
    try:
        q_client = QdrantMemoryClient()
        matches = hybrid_search(
            client=q_client,
            collection="incidents_historical",
            query_text=case_id,
            top_k=10
        )
        return RetrievalResponse(
            case_id=case_id,
            matches=matches,
            pipeline_steps={"BGE Embed": 1.2, "Qdrant Hybrid": 14.5, "Rerank": 8.3},
        )
    except Exception as e:
        return RetrievalResponse(
            case_id=case_id,
            matches=[],
            pipeline_steps={"error": 0.0},
        )

