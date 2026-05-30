from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routes.analysis import router as analysis_router

app = FastAPI(title="MasterLens API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(analysis_router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}
