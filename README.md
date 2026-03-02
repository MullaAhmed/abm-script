# ABM Script

AI-powered landing page personalization. Identifies visitors (via RB2B, Clearbit, or ip-api.com), researches them with LiteLLM, and dynamically rewrites page content to match their company, role, and industry.

No component configuration needed — just add `dummy-ops-element` to any HTML element and the AI figures out what to personalize based on the tag and current text.

## Architecture

```
abm-script/
├── .env                  # All configuration lives here
├── backend/              # Python backend (FastAPI) — all heavy logic
│   ├── main.py           # API routes + app entry point
│   ├── config.py         # Settings (reads from .env)
│   └── abm/
│       ├── engine.py     # Orchestration pipeline
│       ├── cache.py      # Memory or file-based TTL cache
│       ├── researcher.py # AI visitor research
│       ├── personalizer.py # AI content generation
│       └── identity/     # Identity providers
│           ├── rb2b.py
│           ├── clearbit.py
│           └── ipapi.py
├── client/
│   └── abm.js           # Thin vanilla JS snippet (~160 lines)
├── demo/
│   └── index.html        # Interactive demo page
└── react/                # Optional React wrappers
    ├── Personalized.tsx
    └── useABM.ts
```

## Quick Start

```bash
cp .env.example .env      # Add your OPENAI_API_KEY
cd backend
uv sync
uv run uvicorn main:app --port 8001
```

Open [http://localhost:8001/demo](http://localhost:8001/demo) to test.

## Configuration

The entire application is configured via a single `.env` file in the project root.

### AI

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | — | OpenAI API key (used via LiteLLM) |
| `ABM_AI_MODEL` | No | `openai/gpt-5-nano` | Model for research and personalization |

### Identity Provider

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `IDENTITY_PROVIDER` | No | `rb2b` | Which provider: `rb2b`, `clearbit-reveal`, or `ip-api` |
| `RB2B_API_KEY` | No | — | API key for RB2B |
| `CLEARBIT_API_KEY` | No | — | API key for Clearbit Reveal |

> **Demo mode:** Set `IDENTITY_PROVIDER=ip-api` to use the free ip-api.com service (no API key needed). It resolves company/org and location from visitor IP.

### Storage / Cache

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `STORAGE_TYPE` | No | `memory` | Cache backend: `memory` or `file` |
| `CACHE_TTL` | No | `3600` | How long to cache results, in seconds |
| `CACHE_DIR` | No | `.abm-cache` | Directory for file cache (only when `STORAGE_TYPE=file`) |

### Server

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `HOST` | No | `0.0.0.0` | Bind address |
| `PORT` | No | `8001` | Listen port |
| `CORS_ORIGINS` | No | `*` | Comma-separated allowed origins, or `*` for all |
| `DEBUG` | No | `false` | Enable FastAPI debug mode |

## Embedding on Your Site

### 1. Add `dummy-ops-element` to anything you want personalized

```html
<h1 dummy-ops-element="headline">Accelerate Your Growth</h1>
<p dummy-ops-element="subtext">The all-in-one platform teams love.</p>
<button dummy-ops-element="cta">Get Started</button>
<p dummy-ops-element="proof">Trusted by 500+ companies worldwide</p>
```

The value (e.g. `"headline"`) is just a unique ID for that element. The AI infers what the element is from its tag and current text — no prompts or config needed.

### 2. Load the script and initialize

```html
<script src="https://your-backend.com/api/snippet.js"></script>
<script>
  initABM({
    backendURL: "https://your-backend.com",
    rb2bApiKey: "YOUR_RB2B_KEY",  // optional — auto-identifies visitors
    debug: false,                 // optional — enable console logging
  });
</script>
```

### 3. That's it

When a visitor is identified, the script collects all `dummy-ops-element` elements on the page, sends them + the visitor identity to the backend. The AI researches the visitor, rewrites each element's text to speak directly to them, and the script swaps it into the DOM.

## Manual Identification (No RB2B)

Add `data-abm-trigger` to any form. On submit, the form data is sent as the identity payload:

```html
<form data-abm-trigger>
  <input name="first_name" value="Jane">
  <input name="last_name" value="Smith">
  <input name="email" value="jane@acme.com">
  <input name="company_name" value="Acme Corp">
  <input name="title" value="VP of Marketing">
  <input name="company_industry" value="SaaS">
  <button type="submit">Personalize</button>
</form>
```

## React Integration

Copy the files from `react/` into your project.

### `<Personalized>` component

```tsx
import { Personalized } from "./Personalized";

export function Hero() {
  return (
    <Personalized elementId="headline" as="h1" className="text-4xl">
      Default Headline
    </Personalized>
  );
}
```

### `useABM` hook

```tsx
import { useABM } from "./useABM";

export function Dashboard() {
  const { components, visitor } = useABM();

  return (
    <h1>{components["headline"] ?? "Welcome"}</h1>
  );
}
```

Both listen for the `abm:personalized` event dispatched by `abm.js`.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/identify` | Identify visitor + personalize page elements |
| `GET` | `/api/snippet.js` | Serve the thin client JS |
| `POST` | `/research` | Research a visitor (direct AI access) |
| `GET` | `/health` | Health check |

### POST `/api/identify`

**Request:**
```json
{
  "payload": {
    "email": "jane@acme.com",
    "first_name": "Jane",
    "last_name": "Smith",
    "title": "VP of Marketing",
    "company_name": "Acme Corp",
    "company_industry": "SaaS"
  },
  "elements": [
    { "id": "headline", "tag": "h1", "current_text": "Accelerate Your Growth" },
    { "id": "subtext", "tag": "p", "current_text": "The all-in-one platform teams love." },
    { "id": "cta", "tag": "button", "current_text": "Get Started" }
  ],
  "page_url": "https://example.com"
}
```

**Response:**
```json
{
  "visitor": {
    "name": "Jane Smith",
    "company": "Acme Corp",
    "role": "VP of Marketing",
    "industry": "SaaS"
  },
  "components": {
    "headline": "Built for SaaS Marketing Leaders",
    "subtext": "See how Acme Corp can close deals 3x faster.",
    "cta": "Start Free Trial"
  },
  "cached": false
}
```

## How It Works

```
Visitor lands on page
    ↓
abm.js checks localStorage cache → applies if fresh
    ↓
RB2B identifies the visitor (or form submitted manually)
    ↓
abm.js collects all [dummy-ops-element] nodes from the DOM
    ↓
Sends visitor identity + elements to POST /api/identify
    ↓
Backend:
  1. Parse identity (RB2B, Clearbit, or ip-api provider)
  2. Check cache (memory or file, per STORAGE_TYPE)
  3. Research visitor via LiteLLM (role, company, pain points)
  4. AI rewrites each element's text for this specific visitor
  5. Cache result, return to client
    ↓
abm.js swaps DOM content via [dummy-ops-element] selectors
    ↓
Dispatches "abm:personalized" event (for React/framework hooks)
    ↓
Caches in localStorage for instant next-page-load
```
