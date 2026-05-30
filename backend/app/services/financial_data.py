import yfinance as yf
from app.models.schemas import StockQuote, FinancialData


def get_financial_data(ticker: str) -> FinancialData:
    stock = yf.Ticker(ticker)
    info = stock.info

    quote = StockQuote(
        ticker=ticker.upper(),
        company_name=info.get("longName", info.get("shortName", ticker)),
        price=info.get("currentPrice", info.get("regularMarketPrice", 0)),
        currency=info.get("currency", "USD"),
        exchange=info.get("exchange", ""),
        market_cap=info.get("marketCap"),
        pe_ratio=info.get("trailingPE"),
        pb_ratio=info.get("priceToBook"),
        peg_ratio=info.get("pegRatio"),
        dividend_yield=info.get("dividendYield"),
        fifty_two_week_high=info.get("fiftyTwoWeekHigh"),
        fifty_two_week_low=info.get("fiftyTwoWeekLow"),
        change_percent=info.get("regularMarketChangePercent"),
    )

    financials = stock.financials
    balance = stock.balance_sheet
    cashflow = stock.cashflow

    revenue = None
    net_income = None
    fcf = None
    total_debt = None
    total_assets = None

    if not financials.empty:
        col = financials.columns[0]
        revenue = financials.loc["Total Revenue", col] if "Total Revenue" in financials.index else None
        net_income = financials.loc["Net Income", col] if "Net Income" in financials.index else None

    if not cashflow.empty:
        col = cashflow.columns[0]
        fcf = cashflow.loc["Free Cash Flow", col] if "Free Cash Flow" in cashflow.index else None

    if not balance.empty:
        col = balance.columns[0]
        total_debt = balance.loc["Total Debt", col] if "Total Debt" in balance.index else None
        total_assets = balance.loc["Total Assets", col] if "Total Assets" in balance.index else None

    return FinancialData(
        quote=quote,
        revenue=float(revenue) if revenue is not None else None,
        net_income=float(net_income) if net_income is not None else None,
        free_cash_flow=float(fcf) if fcf is not None else None,
        total_debt=float(total_debt) if total_debt is not None else None,
        total_assets=float(total_assets) if total_assets is not None else None,
        roe=info.get("returnOnEquity"),
        debt_to_equity=info.get("debtToEquity"),
        revenue_growth=info.get("revenueGrowth"),
        eps=info.get("trailingEps"),
        sector=info.get("sector"),
        industry=info.get("industry"),
        description=info.get("longBusinessSummary", ""),
    )
