"""All models imported here so Base.metadata is complete for Alembic."""

from app.models.content import Author, Comment, Enrichment, Post, SourceCursor
from app.models.entities import Company, EntityMention, Product, Technology
from app.models.graph import GraphEdge, GraphNode
from app.models.intelligence import (
    FeatureRequest,
    Opportunity,
    OpportunityReport,
    OpportunityScore,
    PainCluster,
    Problem,
    TrendSnapshot,
)
from app.models.polls import TechPoll, TechPollOption, TechSurvey
from app.models.taxonomy import Industry, PostIndustry, PostTopic, Topic

__all__ = [
    "Author",
    "Comment",
    "Company",
    "Enrichment",
    "EntityMention",
    "FeatureRequest",
    "GraphEdge",
    "GraphNode",
    "Industry",
    "Opportunity",
    "OpportunityReport",
    "OpportunityScore",
    "PainCluster",
    "Post",
    "PostIndustry",
    "PostTopic",
    "Problem",
    "Product",
    "SourceCursor",
    "Technology",
    "TechPoll",
    "TechPollOption",
    "TechSurvey",
    "Topic",
    "TrendSnapshot",
]
