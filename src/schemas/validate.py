'''
Validates the dict the user will send. Lists the 
required values and acceptable inputs. Validates
each category and the input overall
'''

'''
Validates the dict the user will send. Lists the
required values and acceptable inputs. Validates
each category and the input overall.

These fields must match the model's training columns exactly
(every column in deals.csv + accounts.csv except the DROP list in predict_deal_status.py).
'''

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

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
    # Deal fields
    amount: float = Field(..., gt=0, description="Deal amount in USD (Observed range: ~2,200 to 234,200)")
    lead_source: LeadSource = Field(..., description="Source channel of the lead")

    # Account fields (required)
    industry: Industry = Field(..., description="Industry sector of the company")
    employee_count: int = Field(..., gt=0, description="Number of employees (Observed range: 5 to 23,885)")
    region: Region = Field(..., description="Geographical operating region")
    funding_stage: FundingStage = Field(..., description="Current corporate funding stage")
    tech_stack_score: float = Field(..., ge=0.0, le=1.0, description="Normalized tech stack sophistication score (0.0 to 1.0)")
    founded_year: int = Field(..., ge=1985, le=2026, description="Company founding year (Observed: 1985 to 2023)")

    # Account fields (optional: blank is allowed; the tree model handles missing values)
    annual_revenue_musd: Optional[float] = Field(None, ge=0, description="Annual revenue in millions USD (Observed max: ~3,703)")
    growth_rate_yoy: Optional[float] = Field(None, ge=-1.0, le=2.0, description="Year-over-year growth rate as a fraction, 0.129 = 12.9% (Observed: -0.55 to 0.695)")
    hiring_velocity: Optional[float] = Field(None, ge=0.0, le=1.0, description="Hiring velocity index (Observed: 0.0 to 0.391)")
