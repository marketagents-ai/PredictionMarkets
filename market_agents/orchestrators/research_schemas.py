from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field

class SearchQueries(BaseModel):
    """Schema for search query generation"""
    queries: List[str] = Field(
        description="List of search queries generated from the base query",
        examples=[
            ["latest cryptocurrency trends December 2024", 
             "top performing crypto assets Q4 2024"]
        ]
    )

class AnalysisType(str, Enum):
    ASSET = "asset"
    SECTOR = "sector"
    MACRO = "macro"
    GENERAL = "general"

class AssetAnalysis(BaseModel):
    ticker: str = Field(..., description="Asset ticker (e.g., stock symbol or crypto token).")
    rating: Optional[str] = Field(None, description="Analyst rating (e.g., Buy/Hold/Sell) and brief rationale.")
    target_price: Optional[str] = Field(None, description="Target price or price range from sources.")
    sentiment: Optional[str] = Field(None, description="Overall sentiment (Bullish, Bearish, Neutral).")
    catalysts: List[str] = Field(default_factory=list, description="Key qualitative catalysts for the asset.")
    kpis: List[str] = Field(default_factory=list, description="Key performance indicators (quantitative) for the asset.")
    action: Optional[str] = Field(None, description="Recommended portfolio action (e.g., Add Long, Close Short).")
    sources: List[str] = Field(default_factory=list, description="Information sources (e.g., brokers, analysts).")

class SectorInfo(BaseModel):
    name: str = Field(..., description="Name of the sector or industry.")
    sentiment: Optional[str] = Field(None, description="Overall sentiment for the sector.")
    catalysts: List[str] = Field(default_factory=list, description="Sector-wide catalysts.")
    kpis: List[str] = Field(default_factory=list, description="Sector-level KPIs or metrics.")
    top_assets: List[str] = Field(default_factory=list, description="Representative assets with brief notes.")
    recommendation: Optional[str] = Field(None, description="Recommended sector exposure (e.g., Overweight/Underweight).")
    sources: List[str] = Field(default_factory=list, description="Key sector-level sources.")

class MacroTrends(BaseModel):
    indicators: List[str] = Field(default_factory=list, description="Macro indicators (e.g., GDP, inflation, interest rates).")
    interest_rates: Optional[str] = Field(None, description="Interest rate outlook.")
    global_factors: Optional[str] = Field(None, description="Global geopolitical or economic factors.")
    sentiment: Optional[str] = Field(None, description="Overall macro-level sentiment (risk-on/off).")

class MarketResearch(BaseModel):
    analysis_type: AnalysisType = Field(..., description="Type of analysis: asset, sector, macro, or general.")
    assets: List[AssetAnalysis] = Field(default_factory=list, description="Asset-level insights if 'asset' type.")
    sector: Optional[SectorInfo] = Field(None, description="Sector-level details if 'sector' type.")
    macro: Optional[MacroTrends] = Field(None, description="Macro-level insights if 'macro' type.")

from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field

class FedStance(str, Enum):
    HAWKISH = "hawkish"
    DOVISH = "dovish"
    NEUTRAL = "neutral"

class EconomicIndicator(BaseModel):
    """Key economic indicators influencing Fed decisions"""
    name: str = Field(..., description="Name of the economic indicator")
    current_value: str = Field(..., description="Current value or range")
    trend: str = Field(..., description="Recent trend in the indicator")
    fed_impact: str = Field(..., description="How this indicator might influence Fed's decision")

class FedSpeaker(BaseModel):
    """Recent Fed official communications"""
    name: str = Field(..., description="Name of the Fed official")
    role: str = Field(..., description="Position at the Fed")
    stance: FedStance = Field(..., description="Speaker's monetary policy stance")
    key_quotes: List[str] = Field(default_factory=list, description="Notable quotes about monetary policy")
    date: str = Field(..., description="Date of the communication")

class MarketExpectation(BaseModel):
    """Market-based predictions and indicators"""
    source: str = Field(..., description="Source of the expectation (e.g., CME FedWatch, Wall Street Bank)")
    probability_no_change: float = Field(..., description="Probability of no rate change")
    probability_25_cut: float = Field(..., description="Probability of 25 bps cut")
    probability_50_plus_cut: float = Field(..., description="Probability of 50+ bps cut")
    probability_hike: float = Field(..., description="Probability of rate hike")
    rationale: str = Field(..., description="Reasoning behind the probabilities")

class FedRateAnalysis(BaseModel):
    """Comprehensive analysis for Fed rate decision prediction"""
    current_rate: Optional[str] = Field(
        default="5.25%-5.50%",
        description="Current Federal Funds Rate range"
    )
    
    economic_indicators: List[EconomicIndicator] = Field(
        default_factory=list,
        description="Key economic data influencing the decision"
    )
    
    inflation_outlook: Optional[str] = Field(
        default="Pending analysis",
        description="Analysis of inflation trends and expectations"
    )
    
    employment_outlook: Optional[str] = Field(
        default="Pending analysis",
        description="Analysis of labor market conditions"
    )
    
    recent_fed_communications: List[FedSpeaker] = Field(
        default_factory=list,
        description="Recent communications from Fed officials"
    )
    
    market_expectations: List[MarketExpectation] = Field(
        default_factory=list,
        description="Market-based predictions and probabilities"
    )
    
    global_factors: List[str] = Field(
        default_factory=list,
        description="International factors affecting Fed decision"
    )
    
    technical_analysis: Optional[str] = Field(
        None,
        description="Technical market analysis relevant to Fed decision"
    )
    
    risk_factors: List[str] = Field(
        default_factory=list,
        description="Key risks that could affect the Fed's decision"
    )
    
    predicted_outcome: Optional[str] = Field(
        default="Analysis in progress",
        description="Predicted March FOMC decision with confidence level"
    )
    
    reasoning: Optional[str] = Field(
        default="Gathering and analyzing data",
        description="Summary of key reasoning behind the prediction"
    )
    
    sources: List[str] = Field(
        default_factory=list,
        description="Sources consulted for this analysis"
    )

    class Config:
        schema_extra = {
            "example": {
                "current_rate": "5.25%-5.50%",
                "economic_indicators": [{
                    "name": "CPI",
                    "current_value": "3.4% YoY",
                    "trend": "Declining",
                    "fed_impact": "Supports potential rate cut"
                }],
                "inflation_outlook": "Inflation continuing to moderate towards 2% target",
                "employment_outlook": "Labor market remains resilient but showing signs of cooling",
                "recent_fed_communications": [{
                    "name": "Jerome Powell",
                    "role": "Fed Chair",
                    "stance": "NEUTRAL",
                    "key_quotes": ["We need to see more evidence that inflation is sustainably moving down"],
                    "date": "2024-01-31"
                }],
                "predicted_outcome": "No Change (80% confidence)",
                "reasoning": "Despite moderating inflation, Fed likely to remain cautious..."
            }
        }