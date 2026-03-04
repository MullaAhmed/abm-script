from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from config import get_settings
from abm.engine import get_engine
from abm.identity.rb2b import parse_rb2b_webhook, store_webhook_visitor
from abm.models import (
    IdentifyRequest,
    IdentifyResponse,
)

settings = get_settings()

print(f"[Server] Identity provider: {settings.identity_provider}")
print(f"[Server] AI model: {settings.abm_ai_model}")
print(f"[Server] Storage: {settings.storage_type}")
print(f"[Server] RB2B Account Key: {settings.rb2b_account_key[:4]}..." if settings.rb2b_account_key else "[Server] RB2B Account Key: not set")

app = FastAPI(title="ABM Backend", version="0.4.0", debug=settings.debug)

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


# --- Primary endpoint: thin client calls this ---


@app.post("/api/identify", response_model=IdentifyResponse)
async def identify_and_personalize(req: IdentifyRequest, request: Request) -> IdentifyResponse:
    """Single entry point for the thin client.
    Receives visitor identity payload + page elements, returns personalized text."""
    print(f"[API] /api/identify called with {len(req.elements)} elements")
    print(f"[API] Payload keys: {list(req.payload.keys())}")

    # Inject client IP so ip-based providers can resolve it
    if "ip" not in req.payload and request.client:
        req.payload["ip"] = request.client.host

    # Inject page_url so RB2B provider can match against webhook Captured URL
    if req.page_url:
        req.payload["page_url"] = req.page_url
        print(f"[API] Page URL: {req.page_url}")

    engine = get_engine(req.site_id)
    response = await engine.identify_and_personalize(req.payload, req.elements, req.site_id)

    print(f"[API] Response: visitor={response.visitor.name if response.visitor else 'unknown'}, "
          f"components={len(response.components)}, cached={response.cached}")
    return response


# --- RB2B Webhook endpoint ---


@app.post("/api/webhook/rb2b")
async def rb2b_webhook(request: Request) -> dict:
    """Receive visitor data pushed from RB2B webhook.
    Configure this URL in RB2B's custom integration settings."""
    body = await request.json()
    print(f"[Webhook] RB2B data received: {list(body.keys())}")

    # Validate integration key if provided in header
    auth = request.headers.get("x-integration-key") or request.headers.get("authorization")
    if settings.rb2b_integration_key and auth:
        expected = settings.rb2b_integration_key
        token = auth.replace("Bearer ", "") if auth.startswith("Bearer ") else auth
        if token != expected:
            print("[Webhook] Invalid integration key")
            raise HTTPException(status_code=401, detail="Invalid integration key")

    visitor = parse_rb2b_webhook(body)
    captured_url = body.get("Captured URL")
    print(f"[Webhook] Parsed visitor: {visitor.name} ({visitor.email}) @ {visitor.company}")
    print(f"[Webhook] Captured URL: {captured_url}")

    if not visitor.email and not visitor.company:
        print("[Webhook] No email or company in payload, cannot store")
        raise HTTPException(status_code=400, detail="Business Email or Company Name is required")

    store_webhook_visitor(visitor, captured_url=captured_url)
    print(f"[Webhook] Visitor stored successfully")

    return {"status": "ok", "visitor_email": visitor.email, "captured_url": captured_url}


# --- Serve thin client JS ---


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
        "rb2b_account_key": settings.rb2b_account_key,
        "cache_ttl": settings.cache_ttl,
        "debug": settings.debug,
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


# --- Mount static demo files ---

if _demo_dir.exists():
    app.mount("/demo", StaticFiles(directory=str(_demo_dir), html=True), name="demo")
