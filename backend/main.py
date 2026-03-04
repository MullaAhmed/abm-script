from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from config import get_settings
from abm.engine import get_engine
from abm.models import (
    IdentifyRequest,
    IdentifyResponse,
)

settings = get_settings()

print(f"[Server] AI model: {settings.abm_ai_model}")
print(f"[Server] Storage: {settings.storage_type}")
print(f"[Server] Tomba keys: {'set' if settings.tomba_api_key else 'not set'}")

app = FastAPI(title="ABM Backend", version="0.5.0", debug=settings.debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths relative to this file
_root = Path(__file__).resolve().parent.parent
_client_dir = _root / "client"
_demo_dir = _root / "demo"


@app.post("/api/identify", response_model=IdentifyResponse)
async def identify_and_personalize(req: IdentifyRequest, request: Request) -> IdentifyResponse:
    """Single entry point for the thin client.
    Receives visitor email + page elements, returns personalized text."""
    print(f"[API] /api/identify called with {len(req.elements)} elements")
    print(f"[API] Payload keys: {list(req.payload.keys())}")

    engine = get_engine(req.site_id)
    response = await engine.identify_and_personalize(req.payload, req.elements, req.site_id)

    print(f"[API] Response: visitor={response.visitor.name if response.visitor else 'unknown'}, "
          f"components={len(response.components)}, cached={response.cached}")
    return response


@app.get("/api/snippet.js")
async def serve_snippet() -> FileResponse:
    """Serve the thin client JavaScript snippet."""
    path = _client_dir / "abm.js"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Client snippet not found")
    return FileResponse(path, media_type="application/javascript")


@app.get("/api/config")
async def client_config() -> dict:
    """Return client-safe configuration for auto-init."""
    return {
        "cache_ttl": settings.cache_ttl,
        "debug": settings.debug,
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


# --- Mount static demo files ---

if _demo_dir.exists():
    app.mount("/demo", StaticFiles(directory=str(_demo_dir), html=True), name="demo")
