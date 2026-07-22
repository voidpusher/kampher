"""Knowledge graph as a Postgres property graph.

Two tables, typed kinds/relations, JSONB props, recursive-CTE traversal via
GraphService. Storage-agnostic interface — swappable for Neo4j if scale
demands it (see docs/ARCHITECTURE.md §4).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Enum, Float, ForeignKey, Index, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import EdgeRelation, NodeKind


class GraphNode(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "graph_nodes"
    __table_args__ = (
        UniqueConstraint("kind", "key"),
        Index("ix_graph_nodes_kind", "kind"),
    )

    kind: Mapped[NodeKind] = mapped_column(
        Enum(NodeKind, name="node_kind", values_callable=lambda e: [m.value for m in e])
    )
    # Stable natural key within a kind, e.g. company slug or pain_cluster uuid.
    key: Mapped[str] = mapped_column(Text)
    label: Mapped[str] = mapped_column(Text)
    props: Mapped[dict[str, Any]] = mapped_column(default=dict)


class GraphEdge(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "graph_edges"
    __table_args__ = (
        UniqueConstraint("src_id", "dst_id", "relation"),
        Index("ix_graph_edges_src_id", "src_id"),
        Index("ix_graph_edges_dst_id", "dst_id"),
    )

    src_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("graph_nodes.id", ondelete="CASCADE")
    )
    dst_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("graph_nodes.id", ondelete="CASCADE")
    )
    relation: Mapped[EdgeRelation] = mapped_column(
        Enum(EdgeRelation, name="edge_relation", values_callable=lambda e: [m.value for m in e])
    )
    # Edges strengthen with repeated observation; weight feeds ranking.
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    props: Mapped[dict[str, Any]] = mapped_column(default=dict)
