"""
Canonical Pydantic Schemas for FrontierAtlas / GraphOne Data Pipeline.
Strictly implements the schemas defined in Assessment Specification:
- StartupEntity
- ProductEntity
- ResearchPaperEntity
- JobEntity
- NewsEntity
- EntityMappingEntry
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, HttpUrl


class PricingModelEnum(str, Enum):
    FREE = "FREE"
    FREEMIUM = "FREEMIUM"
    PAID = "PAID"
    ENTERPRISE = "ENTERPRISE"


class SourceMeta(BaseModel):
    name: str = Field(description="Name of the source site")
    url: str = Field(description="Original source URL")


# =====================================================================
# STARTUP ENTITY
# =====================================================================

class StartupContentData(BaseModel):
    employeeCount: Optional[int] = Field(default=None, description="Number of employees if available")
    industry: Optional[str] = None
    subindustry: Optional[str] = None
    location: Optional[str] = None
    batch: Optional[str] = None
    website: Optional[str] = None
    one_liner: Optional[str] = None


class StartupContent(BaseModel):
    entityName: str = Field(description="Canonical startup name")
    data: StartupContentData = Field(default_factory=StartupContentData)


class StartupEntity(BaseModel):
    schemaVersion: str = Field(default="1.0", description="Versioning for the schema")
    recordType: str = Field(default="STARTUP", description="Fixed to STARTUP")
    source: SourceMeta
    content: StartupContent
    collectedAt: str = Field(description="ISO-8601 format timestamp")


# =====================================================================
# PRODUCT ENTITY
# =====================================================================

class ProductContent(BaseModel):
    productName: str = Field(default="", description="Name of the product")
    description: Optional[str] = None
    startupName: str = Field(description="Canonical startup name")
    pricingModel: PricingModelEnum = Field(description="Pricing model enum")


class ProductEntity(BaseModel):
    schemaVersion: str = Field(default="1.0", description="Versioning for the schema")
    recordType: str = Field(default="PRODUCT", description="Fixed to PRODUCT")
    source: SourceMeta
    content: ProductContent
    collectedAt: str = Field(description="ISO-8601 format timestamp")


# =====================================================================
# RESEARCH PAPER ENTITY
# =====================================================================

class ResearchPaperContent(BaseModel):
    title: str = Field(description="Title of the research paper")
    authors: List[str] = Field(default_factory=list, description="List of author names")
    paper_url: str = Field(description="Link to the Arxiv/PDF page")
    github_url: Optional[str] = Field(default=None, description="Link to the associated code repository")
    github_stars: int = Field(default=0, description="Current number of stars on the GitHub repository")
    published_date: str = Field(description="ISO-8601 publication date")
    summary: Optional[str] = None


class ResearchPaperEntity(BaseModel):
    schemaVersion: str = Field(default="1.0", description="Versioning for the schema")
    recordType: str = Field(default="RESEARCH_PAPER", description="Fixed to RESEARCH_PAPER")
    content: ResearchPaperContent
    collectedAt: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


# =====================================================================
# JOB ENTITY
# =====================================================================

class JobContent(BaseModel):
    company: str = Field(description="Canonical company name")
    title: str = Field(default="", description="Job title")
    date: str = Field(description="ISO-8601 publication date")
    is_remote: bool = Field(default=True, description="Remote eligibility")
    role_family: str = Field(default="Engineering", description="Functional category (e.g., Engineering)")


class JobEntity(BaseModel):
    schemaVersion: str = Field(default="1.0", description="Versioning for the schema")
    recordType: str = Field(default="JOB", description="Fixed to JOB")
    source: SourceMeta
    content: JobContent
    collectedAt: str = Field(description="ISO-8601 format timestamp")


# =====================================================================
# NEWS ENTITY
# =====================================================================

class NewsContent(BaseModel):
    title: str = Field(description="Headline of the article")
    published_date: str = Field(description="ISO-8601 publication date")
    summary: str = Field(default="", description="Summary of article content")
    full_text: Optional[str] = None


class NewsEntity(BaseModel):
    schemaVersion: str = Field(default="1.0", description="Versioning for the schema")
    recordType: str = Field(default="NEWS", description="Fixed to NEWS")
    source: SourceMeta
    content: NewsContent
    collectedAt: str = Field(description="ISO-8601 format timestamp")


# =====================================================================
# ENTITY MAPPING LOG ENTRY
# =====================================================================

class EntityMappingEntry(BaseModel):
    raw_name: str
    canonical_name: str
    entity_type: str
    resolution_method: str
    confidence_score: float
    is_seed_match: bool
    matched_seed_id: Optional[str] = None
    resolved_at: str
