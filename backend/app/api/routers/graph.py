"""Knowledge-graph exploration endpoints.

Read-only traversal runs on the async session via raw SQL mirroring
GraphService's queries (the service itself is sync, worker-side).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query
from sqlalchemy import text

from app.api.deps import SessionDep
from app.core.exceptions import NotFoundError
from app.schemas.api import GraphNeighborOut, GraphNodeOut

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/nodes", response_model=list[GraphNodeOut])
async def find_nodes(
    session: SessionDep,
    kind: str,
    q: str = Query(default="", max_length=200),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[GraphNodeOut]:
    rows = await session.execute(
        text("""
            SELECT id, kind, key, label FROM graph_nodes
            WHERE kind = :kind AND (:q = '' OR label ILIKE '%' || :q || '%')
            ORDER BY label LIMIT :limit
        """),
        {"kind": kind, "q": q, "limit": limit},
    )
    return [GraphNodeOut(**dict(row._mapping)) for row in rows]


@router.get("/nodes/{node_id}/neighbors", response_model=list[GraphNeighborOut])
async def neighbors(
    node_id: uuid.UUID,
    session: SessionDep,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[GraphNeighborOut]:
    exists = await session.scalar(
        text("SELECT 1 FROM graph_nodes WHERE id = :id"), {"id": str(node_id)}
    )
    if not exists:
        raise NotFoundError("graph node not found")

    rows = await session.execute(
        text("""
            SELECT n.id, n.kind, n.key, n.label, e.relation, e.weight,
                   (e.src_id = :node_id) AS outgoing
            FROM graph_edges e
            JOIN graph_nodes n
              ON n.id = CASE WHEN e.src_id = :node_id THEN e.dst_id ELSE e.src_id END
            WHERE e.src_id = :node_id OR e.dst_id = :node_id
            ORDER BY e.weight DESC
            LIMIT :limit
        """),
        {"node_id": str(node_id), "limit": limit},
    )
    return [GraphNeighborOut(**dict(row._mapping)) for row in rows]
