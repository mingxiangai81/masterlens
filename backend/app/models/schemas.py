from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class StockQuote(BaseModel):
    ticker: str
    company_name: str
    price: float
    currency: str
    exchange: str
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    peg_ratio: Optional[float] = None
    dividend_yield: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None
    change_percent: Optional[float] = None


class FinancialData(BaseModel):
    quote: StockQuote
    revenue: Optional[float] = None
    net_income: Optional[float] = None
    free_cash_flow: Optional[float] = None
    total_debt: Optional[float] = None
    total_assets: Optional[float] = None
    roe: Optional[float] = None
    debt_to_equity: Optional[float] = None
    revenue_growth: Optional[float] = None
    eps: Optional[float] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None


class MasterVerdict(BaseModel):
    master_name: str
    master_name_zh: str
    framework: str
    framework_zh: str
    verdict: str
    score: float
    reasoning_en: str
    reasoning_zh: str
    key_metric: str


class Consensus(BaseModel):
    score: float
    buy_count: int
    hold_count: int
    pass_count: int
    summary_en: str
    summary_zh: str


class WallStreetReport(BaseModel):
    business_model: str
    financial_health: dict
    moat: dict
    dcf_valuation: dict
    bull_case: str
    bear_case: str
    earnings_analysis: str


class TradePlan(BaseModel):
    disclaimer: str = "Educational content only, not investment advice"
    entry_range: dict
    stop_loss: dict
    take_profit: list
    position_size: str
    time_horizon: str


class FullReport(BaseModel):
    ticker: str
    company_name: str
    price: float
    currency: str
    exchange: str
    generated_at: datetime
    language: str
    master_verdicts: list[MasterVerdict]
    consensus: Consensus
    wall_street_report: WallStreetReport
    trade_plan: TradePlan
    data_sources: list[dict]
