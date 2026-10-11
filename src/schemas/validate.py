'''
Validates the dict the user will send. Lists the 
required values and acceptable inputs. Validates
each category and the input overall
'''

from pydantic import BaseModel, Field
from typing import Literal

from datetime import date
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, conint, confloat


# --- Enums for Categorical Fields ---
class LeadSource(str, Enum):
    outbound = "outbound"
    inbound = "inbound"
    event = "event"
    referral = "referral"


class Industry(str, Enum):
    logistics = "logistics"
    healthcare = "healthcare"
    education = "education"
    manufacturing = "manufacturing"
    software = "software"
    media = "media"
    retail = "retail"
    fintech = "fintech"
    energy = "energy"


class Region(str, Enum):
    europe = "europe"
    north_america = "north_america"
    latam = "latam"
    apac = "apac"


class FundingStage(str, Enum):
    series_c_plus = "series_c_plus"
    series_b = "series_b"
    seed = "seed"
    bootstrapped = "bootstrapped"
    public = "public"
    series_a = "series_a"


# --- Main Pydantic Model ---
class UploadVerify(BaseModel):
    amount: float = Field(..., gt=0, description="Deal amount in USD (Observed range: ~2,200 to 234,200)")
    lead_source: LeadSource = Field(..., description="Source channel of the lead")

    # Account-specific fields
    name: Optional[str] = Field(None, description="Company name")
    industry: Industry = Field(..., description="Industry sector of the company")
    employee_count: int = Field(..., gt=0, description="Number of employees (Observed range: 5 to 23,885)")
    annual_revenue_musd: Optional[float] = Field(None, ge=0, description="Annual revenue in millions USD (Observed max: ~3,703)")
    region: Region = Field(..., description="Geographical operating region")
    funding_stage: FundingStage = Field(..., description="Current corporate funding stage")
    growth_rate_yoy: Optional[float] = Field(..., ge=-1.0, le=2.0, description="Year-over-year growth rate (Observed: -0.55 to 0.695)")
    hiring_velocity: Optional[float] = Field(..., ge=0.0, le=1.0, description="Hiring velocity index (Observed: 0.0 to 0.391)")
    tech_stack_score: float = Field(..., ge=0.0, le=1.0, description="Normalized tech stack sophistication score (0.0 to 1.0)")
    founded_year: int = Field(..., ge=1985, le=2026, description="Company founding year (Observed: 1985 to 2023)")
