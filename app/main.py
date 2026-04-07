from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.logger import get_logger
from app.routes.voice import router as voice_router

log = get_logger("main")

app = FastAPI(
    title="Telephony AI Agent",
    description="Enterprise-grade voice automation platform utilizing Twilio, Deepgram, and Groq.",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(voice_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.on_event("startup")
async def startup() -> None:
    log.info("Voice Agent server started.")


@app.on_event("shutdown")
async def shutdown() -> None:
    log.info("Voice Agent server shutting down.")
