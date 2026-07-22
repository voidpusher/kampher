"""Knowledge graph service.

Storage-agnostic interface over the Postgres property graph. Sync sessions —
graph writes happen in workers; the API reads via small targeted queries.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models.enums import EdgeRelation, NodeKind
from app.models.graph import GraphEdge, GraphNode


class GraphService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert_node(
        self,
        kind: NodeKind,
        key: str,
        label: str,
        props: dict[str, Any] | None = None,
    ) -> uuid.UUID:
        stmt = (
            pg_insert(GraphNode)
            .values(id=uuid.uuid4(), kind=kind, key=key, label=label, props=props or {})
            .on_conflict_do_update(
                index_elements=[GraphNode.kind, GraphNode.key],
                set_={"label": label},
            )
            .returning(GraphNode.id)
        )
        node_id = self.session.execute(stmt).scalar_one()
        return node_id

    def upsert_edge(
        self,
        src_id: uuid.UUID,
        dst_id: uuid.UUID,
        relation: EdgeRelation,
        weight_delta: float = 1.0,
        props: dict[str, Any] | None = None,
    ) -> None:
        """Insert the edge or strengthen it — repeated observations add weight."""
        stmt = (
            pg_insert(GraphEdge)
            .values(
                id=uuid.uuid4(),
                src_id=src_id,
                dst_id=dst_id,
                relation=relation,
                weight=weight_delta,
                props=props or {},
            )
            .on_conflict_do_update(
                index_elements=[GraphEdge.src_id, GraphEdge.dst_id, GraphEdge.relation],
                set_={"weight": GraphEdge.weight + weight_delta},
            )
        )
        self.session.execute(stmt)

    def connect(
        self,
        src: tuple[NodeKind, str, str],
        relation: EdgeRelation,
        dst: tuple[NodeKind, str, str],
        weight_delta: float = 1.0,
    ) -> None:
        """Upsert both endpoints and the edge in one call: (kind, key, label)."""
        src_id = self.upsert_node(*src)
        dst_id = self.upsert_node(*dst)
        self.upsert_edge(src_id, dst_id, relation, weight_delta)

    def find_node(self, kind: NodeKind, key: str) -> GraphNode | None:
        return self.session.scalar(
            select(GraphNode).where(GraphNode.kind == kind, GraphNode.key == key)
        )

    def neighbors(
        self,
        node_id: uuid.UUID,
        relation: EdgeRelation | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Directly connected nodes (both directions), strongest edges first."""
        sql = text("""
            SELECT n.id, n.kind, n.key, n.label, e.relation, e.weight,
                   (e.src_id = :node_id) AS outgoing
            FROM graph_edges e
            JOIN graph_nodes n
              ON n.id = CASE WHEN e.src_id = :node_id THEN e.dst_id ELSE e.src_id END
            WHERE (e.src_id = :node_id OR e.dst_id = :node_id)
              AND (:relation IS NULL OR e.relation = :relation)
            ORDER BY e.weight DESC
            LIMIT :limit
        """)
        rows = self.session.execute(
            sql,
            {
                "node_id": str(node_id),
                "relation": relation.value if relation else None,
                "limit": limit,
            },
        )
        return [dict(row._mapping) for row in rows]

    def traverse(
        self,
        start_id: uuid.UUID,
        max_depth: int = 2,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """Breadth-limited traversal via recursive CTE (undirected)."""
        sql = text("""
            WITH RECURSIVE walk(node_id, depth, path) AS (
                SELECT CAST(:start_id AS uuid), 0, ARRAY[CAST(:start_id AS uuid)]
                UNION ALL
                SELECT CASE WHEN e.src_id = w.node_id THEN e.dst_id ELSE e.src_id END,
                       w.depth + 1,
                       w.path || CASE WHEN e.src_id = w.node_id THEN e.dst_id ELSE e.src_id END
                FROM graph_edges e
                JOIN walk w ON (e.src_id = w.node_id OR e.dst_id = w.node_id)
                WHERE w.depth < :max_depth
                  AND NOT (CASE WHEN e.src_id = w.node_id
                                THEN e.dst_id ELSE e.src_id END = ANY(w.path))
            )
            SELECT DISTINCT ON (n.id) n.id, n.kind, n.key, n.label, w.depth
            FROM walk w JOIN graph_nodes n ON n.id = w.node_id
            WHERE w.depth > 0
            ORDER BY n.id, w.depth
            LIMIT :limit
        """)
        rows = self.session.execute(
            sql,
            {
                "start_id": str(start_id),
                "max_depth": max_depth,
                "limit": limit,
            },
        )
        return [dict(row._mapping) for row in rows]
