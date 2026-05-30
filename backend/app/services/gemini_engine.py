import json
from google import genai
from app.config import settings


client = genai.Client(api_key=settings.gemini_api_key)
MODEL = "gemini-2.0-flash"


async def generate_master_verdict(prompt: str) -> dict:
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "temperature": 0.7,
        },
    )
    text = response.text.strip()
    return json.loads(text)


async def generate_report_section(prompt: str) -> dict:
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "temperature": 0.5,
        },
    )
    text = response.text.strip()
    return json.loads(text)
