from fastapi import APIRouter, HTTPException, Header
from datetime import datetime, timezone, timedelta
from app.services.financial_data import get_financial_data
from app.services.report_builder import build_full_report
from app.models.schemas import StockQuote
from app.models.database import supabase

router = APIRouter(prefix="/api", tags=["analysis"])

TRIAL_QUERY_LIMIT = 3
FREE_MONTHLY_LIMIT = 3


def get_user_from_token(authorization: str) -> dict | None:
    """Return profile dict if token valid, else None (anonymous)."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        token = authorization.split(" ")[1]
        user = supabase.auth.get_user(token)
        profile = supabase.table("profiles").select("*").eq("id", str(user.user.id)).single().execute()
        return {"user_id": str(user.user.id), **profile.data}
    except Exception:
        return None


def check_trial_quota(profile: dict) -> None:
    """Raise 403 if trial user has exceeded limits."""
    if not profile.get("is_trial"):
        return

    # Check trial expiry
    trial_expires = profile.get("trial_expires_at")
    if trial_expires:
        # Handle both string and datetime
        if isinstance(trial_expires, str):
            from dateutil import parser as dtparser
            expires_dt = dtparser.parse(trial_expires)
        else:
            expires_dt = trial_expires
        if expires_dt.tzinfo is None:
            expires_dt = expires_dt.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expires_dt:
            raise HTTPException(
                status_code=403,
                detail="TRIAL_EXPIRED|Your 7-day free trial has ended. Upgrade to continue.",
            )

    # Check query count
    used = profile.get("trial_reports_used", 0)
    if used >= TRIAL_QUERY_LIMIT:
        raise HTTPException(
            status_code=403,
            detail=f"TRIAL_LIMIT|You have used all {TRIAL_QUERY_LIMIT} free trial queries. Upgrade to continue.",
        )


def increment_trial_usage(user_id: str, profile: dict) -> None:
    """Increment the appropriate usage counter."""
    if profile.get("is_trial"):
        supabase.table("profiles").update(
            {"trial_reports_used": profile.get("trial_reports_used", 0) + 1}
        ).eq("id", user_id).execute()


@router.get("/quote/{ticker}", response_model=StockQuote)
async def get_quote(ticker: str):
    try:
        data = get_financial_data(ticker)
        return data.quote
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Could not fetch data for {ticker}: {str(e)}")


@router.get("/analyze/{ticker}")
async def analyze_stock(ticker: str, lang: str = "zh", authorization: str = Header(None)):
    profile = get_user_from_token(authorization)

    # Enforce quota for logged-in users
    if profile:
        check_trial_quota(profile)

    ticker_upper = ticker.upper()
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()

    # Check cache (skip user_id filter so all users share cached reports)
    cached = supabase.table("reports").select("report_data").eq(
        "ticker", ticker_upper
    ).eq("language", lang).gte("created_at", cutoff).order(
        "created_at", desc=True
    ).limit(1).execute()

    if cached.data:
        # Still increment usage even on cache hit
        if profile:
            increment_trial_usage(profile["user_id"], profile)
        return cached.data[0]["report_data"]

    try:
        report = await build_full_report(ticker_upper, lang)
        supabase.table("reports").insert({
            "ticker": ticker_upper,
            "language": lang,
            "report_data": report,
            "user_id": profile["user_id"] if profile else None,
        }).execute()
        if profile:
            increment_trial_usage(profile["user_id"], profile)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/trial-status")
async def trial_status(authorization: str = Header(None)):
    """Return trial status for the current user."""
    profile = get_user_from_token(authorization)
    if not profile:
        return {"authenticated": False}

    is_trial = profile.get("is_trial", False)
    trial_expires = profile.get("trial_expires_at")
    used = profile.get("trial_reports_used", 0)

    days_left = None
    if is_trial and trial_expires:
        if isinstance(trial_expires, str):
            from dateutil import parser as dtparser
            expires_dt = dtparser.parse(trial_expires)
        else:
            expires_dt = trial_expires
        if expires_dt.tzinfo is None:
            expires_dt = expires_dt.replace(tzinfo=timezone.utc)
        delta = expires_dt - datetime.now(timezone.utc)
        days_left = max(0, delta.days)

    return {
        "authenticated": True,
        "plan": profile.get("plan", "trial"),
        "is_trial": is_trial,
        "trial_queries_used": used,
        "trial_queries_remaining": max(0, TRIAL_QUERY_LIMIT - used),
        "trial_days_left": days_left,
        "trial_expires_at": str(trial_expires) if trial_expires else None,
    }
