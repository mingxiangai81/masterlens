from fastapi import APIRouter, HTTPException
from app.services.financial_data import get_financial_data
from app.models.schemas import StockQuote

router = APIRouter(prefix="/api", tags=["analysis"])


@router.get("/quote/{ticker}", response_model=StockQuote)
async def get_quote(ticker: str):
    try:
        data = get_financial_data(ticker)
        return data.quote
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Could not fetch data for {ticker}: {str(e)}")
