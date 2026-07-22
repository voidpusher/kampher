"""Seed the taxonomy (industries, topics).

Idempotent: upserts by slug. Run with ``python -m app.db.seed``.
The taxonomy constrains LLM classification stages — models pick from these
lists instead of inventing labels, which keeps the data queryable.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import configure_logging, get_logger
from app.db.session import get_sync_sessionmaker
from app.models import Industry, Topic

log = get_logger(__name__)

INDUSTRIES: list[tuple[str, str]] = [
    ("saas", "SaaS"),
    ("devtools", "Developer Tools"),
    ("fintech", "Fintech"),
    ("healthtech", "Healthtech"),
    ("edtech", "Edtech"),
    ("ecommerce", "E-commerce"),
    ("cybersecurity", "Cybersecurity"),
    ("ai-ml", "AI / Machine Learning"),
    ("martech", "Marketing Technology"),
    ("hrtech", "HR Technology"),
    ("legaltech", "Legal Technology"),
    ("proptech", "Real Estate Technology"),
    ("logistics", "Logistics & Supply Chain"),
    ("gaming", "Gaming"),
    ("media", "Media & Content"),
    ("climate", "Climate & Energy"),
    ("hardware", "Hardware & IoT"),
    ("consumer", "Consumer Apps"),
]

TOPICS: list[tuple[str, str]] = [
    ("authentication", "Authentication & Identity"),
    ("payments", "Payments & Billing"),
    ("observability", "Monitoring & Observability"),
    ("data-pipelines", "Data Pipelines & ETL"),
    ("apis", "APIs & Integrations"),
    ("deployment", "Deployment & Infrastructure"),
    ("testing", "Testing & QA"),
    ("documentation", "Documentation"),
    ("onboarding", "User Onboarding"),
    ("pricing", "Pricing & Packaging"),
    ("customer-support", "Customer Support"),
    ("analytics", "Analytics & Reporting"),
    ("collaboration", "Collaboration & Workflow"),
    ("automation", "Automation"),
    ("search", "Search & Discovery"),
    ("notifications", "Notifications & Messaging"),
    ("performance", "Performance & Scaling"),
    ("compliance", "Compliance & Privacy"),
    ("ai-agents", "AI Agents & LLM Apps"),
    ("mobile", "Mobile Development"),
]


def _upsert(
    session: Session, model: type[Industry] | type[Topic], rows: list[tuple[str, str]]
) -> int:
    created = 0
    for slug, name in rows:
        exists = session.scalar(select(model).where(model.slug == slug))
        if exists is None:
            session.add(model(slug=slug, name=name))
            created += 1
    return created


def seed() -> None:
    with get_sync_sessionmaker()() as session:
        industries = _upsert(session, Industry, INDUSTRIES)
        topics = _upsert(session, Topic, TOPICS)
        session.commit()
    log.info("seed complete", industries_created=industries, topics_created=topics)


if __name__ == "__main__":
    configure_logging()
    seed()
