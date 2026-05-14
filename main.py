"""
main.py — Dreamcatcher API and UI.

- GET  /              -> Council submission form
- POST /evaluate      -> Runs the three-persona council, returns JSON verdict
- GET  /wishlist      -> Public view of the living wishlist + guardrails
- GET  /wishlist/edit -> Editor (HTTP basic auth)
- POST /wishlist      -> Save updated wishlist (HTTP basic auth)
- GET  /health        -> Health check
"""

import asyncio
import os
import secrets
from contextlib import asynccontextmanager

import markdown as md
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, HttpUrl, field_validator

load_dotenv()

from council import (
    COUNCIL_MODEL,
    baldwin,
    derive_verdict,
    extract_recommendation,
    fetch_page_content,
    murray,
    rivera,
    rustin,
)
from verdicts import (
    get_verdict,
    list_verdicts,
    save_verdict,
    verdict_counts,
)
from wishlist import Wishlist, load_wishlist, save_wishlist

templates = Jinja2Templates(directory="templates")

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Dreamcatcher is awake. The Council is ready.")
    yield
    print("Dreamcatcher is shutting down.")


app = FastAPI(
    title="Dreamcatcher",
    description=(
        "An AI council that evaluates tools and technologies against "
        "BLKOUT's values, digital strategy, and infrastructure constraints."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

security = HTTPBasic()

ADMIN_USERNAME = os.getenv("DREAMCATCHER_ADMIN_USERNAME", "board")


def require_admin(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    """HTTP basic auth for the wishlist editor.

    Board members share a single password set via DREAMCATCHER_ADMIN_PASSWORD
    in Coolify. Rotate it there at any time — no redeploy needed.
    """
    expected_password = os.getenv("DREAMCATCHER_ADMIN_PASSWORD")
    if not expected_password:
        raise HTTPException(
            status_code=503,
            detail="Dreamcatcher editor is disabled until DREAMCATCHER_ADMIN_PASSWORD is set.",
        )
    username_ok = secrets.compare_digest(credentials.username, ADMIN_USERNAME)
    password_ok = secrets.compare_digest(credentials.password, expected_password)
    if not (username_ok and password_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect credentials",
            headers={"WWW-Authenticate": 'Basic realm="Dreamcatcher editor"'},
        )
    return credentials.username


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------

MD = md.Markdown(extensions=["extra", "sane_lists"])


def render_wishlist(wishlist: Wishlist) -> str:
    MD.reset()
    return MD.convert(wishlist.content)


# ---------------------------------------------------------------------------
# UI routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def get_ui(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
    )


@app.get("/wishlist", response_class=HTMLResponse)
async def get_wishlist(request: Request):
    try:
        wishlist = load_wishlist()
    except Exception as exc:
        return HTMLResponse(
            f"<h1>Wishlist unavailable</h1><pre>{exc}</pre>",
            status_code=503,
        )
    return templates.TemplateResponse(
        request=request,
        name="wishlist.html",
        context={
            "wishlist_html": render_wishlist(wishlist),
            "updated_at": wishlist.updated_at_human,
            "updated_by": wishlist.updated_by,
        },
    )


@app.get("/wishlist/edit", response_class=HTMLResponse)
async def get_wishlist_edit(
    request: Request,
    _: str = Depends(require_admin),
):
    try:
        wishlist = load_wishlist()
    except Exception as exc:
        return HTMLResponse(
            f"<h1>Wishlist unavailable</h1><pre>{exc}</pre>",
            status_code=503,
        )
    return templates.TemplateResponse(
        request=request,
        name="wishlist_edit.html",
        context={
            "content": wishlist.content,
            "updated_at": wishlist.updated_at_human,
            "updated_by": wishlist.updated_by,
        },
    )


@app.post("/wishlist", response_class=HTMLResponse)
async def post_wishlist(
    content: str = Form(...),
    updated_by: str = Form(""),
    admin: str = Depends(require_admin),
):
    name = (updated_by or "").strip() or admin
    try:
        save_wishlist(content=content, updated_by=name)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Save failed: {exc}") from exc
    return RedirectResponse(url="/wishlist", status_code=303)


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

class EvaluateRequest(BaseModel):
    url: HttpUrl
    submitted_by: str
    submitter_org: str

    @field_validator("url", mode="before")
    @classmethod
    def _add_scheme(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if v and "://" not in v:
                v = "https://" + v
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "url": "https://notion.so",
                    "submitted_by": "rob",
                    "submitter_org": "BLKOUT",
                }
            ]
        }
    }


class EvaluateResponse(BaseModel):
    id: int
    url: str
    submitted_by: str
    submitter_org: str
    baldwin: str
    murray: str
    rustin: str
    rivera: str
    baldwin_recommendation: str
    murray_recommendation: str
    rustin_recommendation: str
    rivera_recommendation: str
    verdict: str


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "service": "dreamcatcher"}


@app.post("/evaluate", response_model=EvaluateResponse, tags=["council"])
async def evaluate(request: EvaluateRequest):
    """
    Submit a URL to the Dreamcatcher Council for evaluation.

    Each persona receives the current wishlist + guardrails as context, so
    edits in the editor UI immediately reshape future verdicts. The full
    evaluation — including the wishlist snapshot at the time of judgement —
    is persisted so history can be reviewed later.
    """
    url_str = str(request.url)
    submitted_by = request.submitted_by.strip()
    submitter_org = request.submitter_org.strip()

    if not submitted_by or not submitter_org:
        raise HTTPException(
            status_code=422,
            detail="Both your name and your organisation are required to summon the council.",
        )

    try:
        wishlist = load_wishlist()
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Wishlist unavailable, cannot convene council: {exc}",
        ) from exc

    content = wishlist.content

    # Fetch the page once and share across all four judges, so they evaluate
    # the actual tool rather than the LLM's training-data memory of the brand.
    page_content = await asyncio.to_thread(fetch_page_content, url_str)

    try:
        (
            baldwin_response,
            murray_response,
            rustin_response,
            rivera_response,
        ) = await asyncio.gather(
            asyncio.to_thread(baldwin, url_str, page_content, content),
            asyncio.to_thread(murray, url_str, page_content, content),
            asyncio.to_thread(rustin, url_str, page_content, content),
            asyncio.to_thread(rivera, url_str, page_content, content, submitter_org),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Council member failed to respond: {exc}",
        ) from exc

    baldwin_rec = extract_recommendation(baldwin_response)
    murray_rec = extract_recommendation(murray_response)
    rustin_rec = extract_recommendation(rustin_response)
    rivera_rec = extract_recommendation(rivera_response)
    verdict = derive_verdict(
        [baldwin_rec, murray_rec, rustin_rec],
        rivera_recommendation=rivera_rec,
    )

    try:
        saved = save_verdict(
            url=url_str,
            submitted_by=submitted_by,
            submitter_org=submitter_org,
            baldwin_response=baldwin_response,
            murray_response=murray_response,
            rustin_response=rustin_response,
            rivera_response=rivera_response,
            baldwin_recommendation=baldwin_rec,
            murray_recommendation=murray_rec,
            rustin_recommendation=rustin_rec,
            rivera_recommendation=rivera_rec,
            verdict=verdict,
            wishlist_snapshot=content,
            wishlist_updated_at=wishlist.updated_at,
            council_model=COUNCIL_MODEL,
        )
    except Exception as exc:
        # The council ran, we have a result. History persistence is best-effort —
        # don't fail the user's response if Supabase is having a moment.
        print(f"warning: verdict history save failed: {exc}")
        return EvaluateResponse(
            id=0,
            url=url_str,
            submitted_by=submitted_by,
            submitter_org=submitter_org,
            baldwin=baldwin_response,
            murray=murray_response,
            rustin=rustin_response,
            rivera=rivera_response,
            baldwin_recommendation=baldwin_rec,
            murray_recommendation=murray_rec,
            rustin_recommendation=rustin_rec,
            rivera_recommendation=rivera_rec,
            verdict=verdict,
        )

    return EvaluateResponse(
        id=saved.id,
        url=url_str,
        submitted_by=submitted_by,
        submitter_org=submitter_org,
        baldwin=baldwin_response,
        murray=murray_response,
        rustin=rustin_response,
        rivera=rivera_response,
        baldwin_recommendation=baldwin_rec,
        murray_recommendation=murray_rec,
        rustin_recommendation=rustin_rec,
        rivera_recommendation=rivera_rec,
        verdict=verdict,
    )


# ---------------------------------------------------------------------------
# Verdict history
# ---------------------------------------------------------------------------

@app.get("/verdicts", response_class=HTMLResponse)
async def get_verdicts_page(request: Request, verdict: str | None = None):
    filter_value = (verdict or "").upper().strip() or None
    try:
        verdicts = list_verdicts(limit=60, verdict_filter=filter_value)
        counts = verdict_counts()
    except Exception as exc:
        return HTMLResponse(
            f"<h1>History unavailable</h1><pre>{exc}</pre>",
            status_code=503,
        )
    return templates.TemplateResponse(
        request=request,
        name="verdicts.html",
        context={
            "verdicts": verdicts,
            "counts": counts,
            "filter": filter_value,
        },
    )


@app.get("/verdicts/{verdict_id}", response_class=HTMLResponse)
async def get_verdict_detail(request: Request, verdict_id: int):
    try:
        verdict = get_verdict(verdict_id)
    except Exception as exc:
        return HTMLResponse(
            f"<h1>Verdict unavailable</h1><pre>{exc}</pre>",
            status_code=503,
        )
    if verdict is None:
        raise HTTPException(status_code=404, detail="Verdict not found")

    MD.reset()
    snapshot_html = MD.convert(verdict.wishlist_snapshot)
    return templates.TemplateResponse(
        request=request,
        name="verdict_detail.html",
        context={
            "verdict": verdict,
            "snapshot_html": snapshot_html,
        },
    )
