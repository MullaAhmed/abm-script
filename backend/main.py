from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .abm.engine import get_engine
from .abm.models import (
    IdentifyRequest,
    IdentifyResponse,
    ResearchRequest,
    ResearchResponse,
)
from .abm.researcher import research_visitor

settings = get_settings()

app = FastAPI(title="ABM Backend", version="0.3.0", debug=settings.debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths relative to this file
_root = Path(__file__).resolve().parent.parent.parent
_client_dir = _root / "client"
_demo_dir = _root / "demo"


# --- Primary endpoint: thin client calls this ---


@app.post("/api/identify", response_model=IdentifyResponse)
async def identify_and_personalize(req: IdentifyRequest) -> IdentifyResponse:
    """Single entry point for the thin client.
    Receives visitor identity payload + page elements, returns personalized text."""
    engine = get_engine(req.site_id)
    return await engine.identify_and_personalize(req.payload, req.elements, req.site_id)


# --- Serve thin client JS ---


@app.get("/api/snippet.js")
async def serve_snippet() -> FileResponse:
    """Serve the thin client JavaScript snippet."""
    path = _client_dir / "abm.js"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Client snippet not found")
    return FileResponse(path, media_type="application/javascript")


# --- Direct AI endpoint (kept for programmatic use) ---


@app.post("/research", response_model=ResearchResponse)
async def research(req: ResearchRequest) -> ResearchResponse:
    """Research a visitor and return intelligence for personalization."""
    return await research_visitor(req.visitor, model=settings.abm_ai_model)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


# --- Mount static demo files ---

if _demo_dir.exists():
    app.mount("/demo", StaticFiles(directory=str(_demo_dir), html=True), name="demo")
