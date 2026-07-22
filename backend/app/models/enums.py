"""Domain enums, shared by models, schemas, and the AI pipeline."""

from __future__ import annotations

from enum import StrEnum


class Source(StrEnum):
    REDDIT = "reddit"
    X = "x"
    GITHUB_ISSUES = "github_issues"
    GITHUB_DISCUSSIONS = "github_discussions"
    HACKERNEWS = "hackernews"
    STACKOVERFLOW = "stackoverflow"
    LOBSTERS = "lobsters"
    DEVTO = "devto"
    # Future plugins register new members here; nothing else changes.
    DISCORD = "discord"
    PRODUCTHUNT = "producthunt"


class EnrichmentStatus(StrEnum):
    PENDING = "pending"  # collected, not yet through the pipeline
    GATED = "gated"  # rejected by a gate stage (language/spam/no-signal)
    ENRICHED = "enriched"  # full pipeline complete
    FAILED = "failed"  # pipeline error after retries


class Intent(StrEnum):
    BUYING = "buying"
    COMPLAINING = "complaining"
    COMPARING = "comparing"
    REQUESTING = "requesting"
    RECOMMENDING = "recommending"
    LEAVING = "leaving"
    NONE = "none"


class Emotion(StrEnum):
    FRUSTRATION = "frustration"
    ANGER = "anger"
    DESPERATION = "desperation"
    DISAPPOINTMENT = "disappointment"
    CURIOSITY = "curiosity"
    EXCITEMENT = "excitement"
    SATISFACTION = "satisfaction"
    NEUTRAL = "neutral"


class EntityType(StrEnum):
    COMPANY = "company"
    PRODUCT = "product"
    PERSON = "person"
    TECHNOLOGY = "technology"


class ScoreKind(StrEnum):
    PAIN = "pain"
    TREND = "trend"
    OPPORTUNITY = "opportunity"
    COMPETITION = "competition"
    NOVELTY = "novelty"
    REVENUE_POTENTIAL = "revenue_potential"
    VIRALITY_POTENTIAL = "virality_potential"
    MARKET_SIZE = "market_size"
    CONFIDENCE = "confidence"


class OpportunityStatus(StrEnum):
    CANDIDATE = "candidate"
    ACTIVE = "active"
    ARCHIVED = "archived"


class TrendSubject(StrEnum):
    TOPIC = "topic"
    INDUSTRY = "industry"
    PAIN_CLUSTER = "pain_cluster"
    TECHNOLOGY = "technology"


class NodeKind(StrEnum):
    PROBLEM = "problem"
    INDUSTRY = "industry"
    PRODUCT = "product"
    COMPANY = "company"
    AUTHOR = "author"
    TECHNOLOGY = "technology"
    FEATURE = "feature"
    PAIN_POINT = "pain_point"
    TREND = "trend"
    TOPIC = "topic"


class EdgeRelation(StrEnum):
    EXPERIENCES = "experiences"  # author -> pain_point
    BELONGS_TO = "belongs_to"  # problem -> industry, product -> company
    COMPETES_WITH = "competes_with"  # company <-> company
    MENTIONS = "mentions"  # post/author -> entity
    REQUESTS = "requests"  # author -> feature
    SOLVES = "solves"  # product -> problem
    BUILT_WITH = "built_with"  # product -> technology
    TRENDING_IN = "trending_in"  # trend -> industry
    COMPLAINS_ABOUT = "complains_about"  # author -> product/company
