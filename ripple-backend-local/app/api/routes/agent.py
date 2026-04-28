"""
/api/v1/agent — ADK agent endpoints with rate limit handling.
"""
import asyncio
import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.core.auth import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


class AnalyzeRequest(BaseModel):
    event_id: str


@router.get("/status")
def agent_status():
    from app.agents.adk_pipeline import pipeline, ADK_AVAILABLE, GEMINI_API_KEY
    return {
        "adk_installed":  ADK_AVAILABLE,
        "gemini_key_set": bool(GEMINI_API_KEY),
        "adk_ready":      pipeline._adk_ready,
        "mode":           "adk" if pipeline._adk_ready else "fallback",
        # ✅ FIX: was "gemini-1.5-flash" — updated to match actual agent model
        "model":          "gemini-2.0-flash",
        "agents": [
            "MonitorAgent    — validates events, enriches supplier context",
            "AnalystAgent    — runs GNN predictions, quantifies cascade risk",
            "RecommenderAgent— generates rerouting strategies, saves to DB",
        ],
    }


@router.post("/chat")
async def chat(req: ChatRequest, _=Depends(get_current_user)):
    from app.agents.adk_pipeline import chat_with_orchestrator, pipeline

    if not pipeline._adk_ready:
        return {
            "response": (
                "ADK agent not yet active.\n\n"
                "To enable:\n"
                "1. Get free Gemini key → https://aistudio.google.com/app/apikey\n"
                "2. Add to .env: GEMINI_API_KEY=your_key\n"
                "3. pip install google-adk google-genai\n"
                "4. Restart backend\n\n"
                "Current mode: manual pipeline (all predictions still work)"
            ),
            "mode": "fallback",
        }

    try:
        response = await chat_with_orchestrator(req.message, req.session_id)
        return {"response": response, "mode": "adk"}

    except Exception as e:
        err = str(e)

        # Handle rate limit gracefully — don't crash the server
        if "429" in err or "RESOURCE_EXHAUSTED" in err or "quota" in err.lower():
            logger.warning(f"Gemini rate limit hit: {err[:100]}")
            return {
                "response": (
                    "⚠️ Gemini API rate limit reached (free tier: 15 requests/minute).\n\n"
                    "**What to do:**\n"
                    "• Wait 60 seconds and try again\n"
                    "• Or use the Events page to trigger the full pipeline (doesn't use chat quota)\n\n"
                    "**To increase limits:**\n"
                    "Add billing to your Google AI Studio project for higher quotas.\n\n"
                    "**Current pipeline status:** All disruption predictions still work normally — "
                    "only the chat interface is rate-limited."
                ),
                "mode": "rate_limited",
                "retry_after_seconds": 60,
            }

        logger.error(f"Agent chat error: {err}", exc_info=True)
        return {
            "response": f"Agent error: {err[:200]}. The manual pipeline is still running normally.",
            "mode": "error",
        }


@router.post("/analyze")
async def analyze(req: AnalyzeRequest, _=Depends(get_current_user)):
    from app.services.database import Database
    from app.agents.adk_pipeline import pipeline

    event = Database.get_event(req.event_id)
    if not event:
        raise HTTPException(404, "Event not found")

    try:
        result = await pipeline.run(event)
        return result
    except Exception as e:
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            raise HTTPException(429, "Gemini rate limit — wait 60s and retry")
        raise HTTPException(500, str(e))