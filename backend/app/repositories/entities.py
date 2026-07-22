"""Entity resolution repository: canonical companies/products/technologies.

Resolution strategy: slugified-name identity. Deliberately simple — a
dedicated entity-resolution stage (aliases, domains, embeddings) can replace
this behind the same get-or-create interface.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.text import slugify
from app.models import Company, EntityMention, Product, Technology
from app.models.enums import EntityType


class EntityRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _get_or_create(
        self, model: type[Company] | type[Product] | type[Technology], name: str
    ) -> uuid.UUID:
        slug = slugify(name)
        stmt = (
            pg_insert(model)
            .values(id=uuid.uuid4(), slug=slug, name=name)
            .on_conflict_do_nothing(index_elements=[model.slug])
            .returning(model.id)
        )
        created = self.session.execute(stmt).scalar_one_or_none()
        if created is not None:
            return created
        existing = self.session.scalar(select(model.id).where(model.slug == slug))
        assert existing is not None
        return existing

    def resolve(self, entity_type: EntityType, name: str) -> uuid.UUID | None:
        """Get-or-create the canonical entity; people are never persisted."""
        match entity_type:
            case EntityType.COMPANY:
                return self._get_or_create(Company, name)
            case EntityType.PRODUCT:
                return self._get_or_create(Product, name)
            case EntityType.TECHNOLOGY:
                return self._get_or_create(Technology, name)
            case EntityType.PERSON:
                return None

    def add_mention(
        self,
        post_id: uuid.UUID,
        entity_type: EntityType,
        entity_id: uuid.UUID | None,
        surface_text: str,
        sentiment: float | None,
        context_quote: str | None,
    ) -> None:
        self.session.add(
            EntityMention(
                post_id=post_id,
                entity_type=entity_type,
                entity_id=entity_id,
                surface_text=surface_text,
                sentiment=sentiment,
                context_quote=context_quote,
            )
        )
