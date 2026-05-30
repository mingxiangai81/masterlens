from datetime import datetime, timezone
from app.services.financial_data import get_financial_data
from app.services.gemini_engine import generate_master_verdict, generate_report_section
from app.services.master_prompts import (
    MASTER_FRAMEWORKS,
    WALL_STREET_REPORT_PROMPT,
    TRADE_PLAN_PROMPT,
    build_financial_summary,
)
from app.models.schemas import (
    FullReport, MasterVerdict, Consensus, WallStreetReport, TradePlan,
)


async def build_full_report(ticker: str, lang: str = "zh") -> dict:
    data = get_financial_data(ticker)
    financial_summary = build_financial_summary(data)

    language = "Chinese (简体中文)" if lang == "zh" else "English"
    language_instruction = "Write all text in Chinese (简体中文)." if lang == "zh" else "Write all text in English."

    verdicts = []
    for master in MASTER_FRAMEWORKS:
        prompt = master["prompt"].format(
            ticker=ticker,
            company_name=data.quote.company_name,
            financial_summary=financial_summary,
        )
        result = await generate_master_verdict(prompt)
        verdicts.append(MasterVerdict(
            master_name=master["name"],
            master_name_zh=master["name_zh"],
            framework=master["framework"],
            framework_zh=master["framework_zh"],
            verdict=result.get("verdict", "hold"),
            score=float(result.get("score", 5)),
            reasoning_en=result.get("reasoning_en", ""),
            reasoning_zh=result.get("reasoning_zh", ""),
            key_metric=result.get("key_metric", ""),
        ))

    buy_count = sum(1 for v in verdicts if v.verdict == "buy")
    hold_count = sum(1 for v in verdicts if v.verdict == "hold")
    pass_count = sum(1 for v in verdicts if v.verdict == "pass")
    avg_score = sum(v.score for v in verdicts) / len(verdicts) if verdicts else 5.0

    verdicts_summary = "\n".join(
        f"- {v.master_name}: {v.verdict.upper()} ({v.score}/10) - {v.key_metric}"
        for v in verdicts
    )

    ws_prompt = WALL_STREET_REPORT_PROMPT.format(
        ticker=ticker,
        company_name=data.quote.company_name,
        financial_summary=financial_summary,
        verdicts_summary=verdicts_summary,
        language=language,
        language_instruction=language_instruction,
    )
    ws_result = await generate_report_section(ws_prompt)

    tp_prompt = TRADE_PLAN_PROMPT.format(
        ticker=ticker,
        company_name=data.quote.company_name,
        price=data.quote.price,
        high_52=data.quote.fifty_two_week_high or data.quote.price * 1.2,
        low_52=data.quote.fifty_two_week_low or data.quote.price * 0.8,
        consensus_score=round(avg_score, 1),
        financial_summary=financial_summary,
        language=language,
        language_instruction=language_instruction,
    )
    tp_result = await generate_report_section(tp_prompt)

    report = FullReport(
        ticker=ticker.upper(),
        company_name=data.quote.company_name,
        price=data.quote.price,
        currency=data.quote.currency,
        exchange=data.quote.exchange,
        generated_at=datetime.now(timezone.utc),
        language=lang,
        master_verdicts=verdicts,
        consensus=Consensus(
            score=round(avg_score, 1),
            buy_count=buy_count,
            hold_count=hold_count,
            pass_count=pass_count,
            summary_en=f"{buy_count} masters say Buy, {hold_count} say Hold, {pass_count} say Pass.",
            summary_zh=f"{buy_count} 位大师建议买入，{hold_count} 位建议观察，{pass_count} 位建议放弃。",
        ),
        wall_street_report=WallStreetReport(**ws_result),
        trade_plan=TradePlan(**tp_result),
        data_sources=[
            {"label": "yfinance real-time data", "field": "price, financials"},
            {"label": f"{data.quote.company_name} public filings", "field": "fundamentals"},
        ],
    )
    return report.model_dump()
