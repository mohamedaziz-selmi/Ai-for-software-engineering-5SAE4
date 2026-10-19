from typing import Any
from pydantic import BaseModel, Field, ConfigDict

class ListingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1, max_length=5000)
    skills: list[str] = Field(default_factory=list, max_length=20)

class DescriptionRequest(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    skills: list[str] = Field(default_factory=list, max_length=20)
    audience: str = Field(default="", max_length=1000)
    requirements: str = Field(default="", max_length=3000)

class CvRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=255)
    skills: list[str] = Field(default_factory=list, max_length=20)
    experience: str = Field(default="", max_length=5000)
    education: str = Field(default="", max_length=1000)

class DemandRequest(BaseModel):
    category: str
    price: float = Field(ge=0, le=1_000_000)
    description_length: int = Field(ge=1, le=10000)
    rating: float = Field(ge=0, le=5)
    response_time_hours: float = Field(ge=0, le=10000)
    delivery_days: int = Field(ge=1, le=365)
    skill_demand_index: float = Field(ge=0, le=1)

class M5ForecastRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    history: list[float] = Field(min_length=28, max_length=400)
    horizon: int = Field(default=7, ge=1, le=28)
    last_date: str | None = None
    sell_price: float = Field(default=0, ge=0, le=100000)

class FraudRequest(BaseModel):
    transaction: dict[str, Any] = Field(default_factory=dict)
    profile: dict[str, Any] = Field(default_factory=dict)

class JobDescriptionGenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=160)
    skills: list[str] = Field(default_factory=list, max_length=30)
    location: str = Field(default="", max_length=200)
    experience: str = Field(default="", max_length=500)
    responsibilities: list[str] = Field(default_factory=list, max_length=20)
    employment_type: str = Field(default="", max_length=100)
    salary: str = Field(default="", max_length=100)
    language: str = Field(default="en", pattern="^(en|fr)$")
    tone: str = Field(default="professional", max_length=40)

class ProductListingGenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=500)
    category: str = Field(default="", max_length=200)
    specifications: dict[str, str] = Field(default_factory=dict)
    language: str = Field(default="en", pattern="^(en|fr)$")
    top_k: int = Field(default=3, ge=1, le=5)
