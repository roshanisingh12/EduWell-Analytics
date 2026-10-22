"""
EduWell Analytics - FastAPI application.

Serves the web dashboard (frontend/) at / and a JSON API under /api.
Each browser gets its own analysis session (cookie); until a CSV is uploaded
it sees the bundled synthetic sample, which is analysed once at startup.

API endpoints:
- GET  /api/health            Liveness/readiness probe
- GET  /api/dataset           Active dataset summary, validation checks and preview rows
- POST /api/upload            Upload, validate, clean, and analyze a CSV for this session
- POST /api/sample            Switch this session back to the synthetic sample
- GET  /api/overview          Summary KPI metrics & stress distribution
- GET  /api/cleaning-report   Data-quality, validation & cleaning results
- GET  /api/descriptive-stats Descriptive statistics, stress-group comparisons, distributions
- GET  /api/correlations      Pearson, Spearman, partial correlation, significance tests, regressions
- GET  /api/insights          Key narrative findings & limitations
- GET  /api/export-report     Download the report, CSV summaries, JSON or a ZIP bundle
- GET  /api/figures/{name}    Generated Matplotlib figures

Run locally:  python main.py
Production:   uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1 --proxy-headers
"""

import asyncio
import glob
import logging
import os
import re
import secrets
import shutil
from contextlib import asynccontextmanager

import pandas as pd
from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from analysis_service import (
    EXPORT_FILES,
    FIGURE_NAMES,
    AnalysisBusyError,
    AnalysisResult,
    DatasetError,
    ensure_figures,
    parse_csv,
    run_analysis,
)
from generate_sample_data import generate_synthetic_data
from session_store import SessionStore
from settings import BASE_DIR, load_settings

APP_VERSION = "1.2.0"
SESSION_COOKIE = "eduwell_sid"
SAMPLE_LABEL = "student_lifestyle_dataset.csv (Synthetic Sample)"
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
PRUNE_INTERVAL_SECONDS = 300

_SID_PATTERN = re.compile(r"[A-Za-z0-9_-]{32,64}")

settings = load_settings()
logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("eduwell")


# ----------------------------------------------------------------------
# Lifecycle
# ----------------------------------------------------------------------
def _load_sample() -> AnalysisResult:
    if os.path.exists(settings.sample_path):
        df = pd.read_csv(settings.sample_path)
    else:
        logger.warning("Sample dataset not found at %s; generating it in memory", settings.sample_path)
        df = generate_synthetic_data()
    return run_analysis(df, SAMPLE_LABEL, True, settings.work_dir, settings.analysis_wait_seconds)


def _clear_stale_work_dirs() -> None:
    # Sessions live in memory, so folders left by a previous process are orphaned.
    for path in glob.glob(os.path.join(settings.work_dir, "analysis-*")):
        shutil.rmtree(path, ignore_errors=True)


async def _prune_sessions(store: SessionStore) -> None:
    while True:
        await asyncio.sleep(PRUNE_INTERVAL_SECONDS)
        removed = await run_in_threadpool(store.prune)
        if removed:
            logger.info("Expired %d idle session(s); %d active", removed, len(store))


async def _warm_figures(result: AnalysisResult) -> None:
    try:
        await run_in_threadpool(ensure_figures, result, settings.analysis_wait_seconds)
    except Exception:
        logger.exception("Could not pre-render sample figures")


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.work_dir, exist_ok=True)
    _clear_stale_work_dirs()
    app.state.sessions = SessionStore(settings.session_ttl_minutes * 60, settings.max_sessions)
    app.state.sample = None
    try:
        app.state.sample = await run_in_threadpool(_load_sample)
        logger.info("Sample dataset analysed (%d rows)", app.state.sample.summary["cleaned_rows"])
    except Exception:
        logger.exception("Could not analyse the sample dataset; uploads still work")
    background = [asyncio.create_task(_prune_sessions(app.state.sessions))]
    if app.state.sample is not None:
        background.append(asyncio.create_task(_warm_figures(app.state.sample)))
    try:
        yield
    finally:
        for task in background:
            task.cancel()
        app.state.sessions.clear()
        if app.state.sample is not None:
            app.state.sample.dispose()


app = FastAPI(
    title="EduWell Analytics API",
    description="Statistical Research & Wellness Analytics API for Student Lifestyle Data",
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url="/api/docs" if settings.enable_docs else None,
    redoc_url=None,
    openapi_url="/api/openapi.json" if settings.enable_docs else None,
)

app.add_middleware(GZipMiddleware, minimum_size=1024)
if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )


# ----------------------------------------------------------------------
# Middleware: session cookie, upload size guard, security & cache headers
# ----------------------------------------------------------------------
CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; "
    "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
)


@app.middleware("http")
async def session_and_headers(request: Request, call_next):
    path = request.url.path
    if request.method == "POST" and path == "/api/upload":
        length = request.headers.get("content-length", "")
        # Allow headroom for multipart boundaries and form fields.
        if length.isdigit() and int(length) > settings.max_upload_bytes + 64 * 1024:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={"detail": f"File too large. The upload limit is {settings.max_upload_mb:g} MB."},
            )

    sid = request.cookies.get(SESSION_COOKIE, "")
    new_sid = None
    if not _SID_PATTERN.fullmatch(sid):
        sid = new_sid = secrets.token_urlsafe(32)
    request.state.sid = sid

    response = await call_next(request)

    if new_sid and path.startswith("/api/"):
        response.set_cookie(SESSION_COOKIE, new_sid, httponly=True, samesite="lax",
                            secure=settings.cookie_secure, path="/")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    response.headers.setdefault("X-Frame-Options", "DENY")
    if not path.startswith("/api/docs"):
        response.headers.setdefault("Content-Security-Policy", CSP)
    if path.startswith("/assets/"):
        response.headers.setdefault("Cache-Control", "no-cache, no-store, must-revalidate")
    elif path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
    return response


# ----------------------------------------------------------------------
# Error handling
# ----------------------------------------------------------------------
@app.exception_handler(DatasetError)
async def dataset_error_handler(request: Request, exc: DatasetError):
    return JSONResponse(status_code=exc.status_code, content={"detail": str(exc)})


@app.exception_handler(AnalysisBusyError)
async def busy_error_handler(request: Request, exc: AnalysisBusyError):
    return JSONResponse(status_code=503, content={"detail": str(exc)}, headers={"Retry-After": "30"})


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "An unexpected server error occurred."})


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def active_result(request: Request) -> AnalysisResult:
    """The analysis this browser session is looking at: its upload, or the shared sample."""
    result = request.app.state.sessions.get(request.state.sid) or request.app.state.sample
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No dataset is available yet. Upload a CSV via POST /api/upload.",
        )
    return result


async def _read_limited(file: UploadFile, limit: int) -> bytes:
    chunks, size = [], 0
    while chunk := await file.read(1024 * 1024):
        size += len(chunk)
        if size > limit:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. The upload limit is {settings.max_upload_mb:g} MB.",
            )
        chunks.append(chunk)
    return b"".join(chunks)


# ----------------------------------------------------------------------
# API Endpoints
# ----------------------------------------------------------------------
@app.get("/api")
def api_root(request: Request):
    return {
        "name": "EduWell Analytics API",
        "version": APP_VERSION,
        "status": "online",
        "sample_loaded": request.app.state.sample is not None,
        "docs": "/api/docs" if settings.enable_docs else None,
    }


@app.get("/api/health")
def health(request: Request):
    ready = request.app.state.sample is not None
    return JSONResponse(
        status_code=200,
        content={"status": "ok", "ready": ready, "version": APP_VERSION,
                 "active_sessions": len(request.app.state.sessions)},
    )


@app.get("/api/dataset")
def get_dataset(result: AnalysisResult = Depends(active_result)):
    """Active dataset summary, validation checks and the first cleaned rows."""
    return result.dataset


@app.post("/api/upload")
async def upload_csv(request: Request, file: UploadFile = File(...)):
    """Upload, validate, clean, and run full statistical analysis on a CSV file for this session."""
    filename = os.path.basename((file.filename or "").replace("\\", "/"))[:200]
    if not filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only CSV files (.csv) are supported.",
        )
    content = await _read_limited(file, settings.max_upload_bytes)
    df = await run_in_threadpool(parse_csv, content, settings.max_rows)
    result = await run_in_threadpool(
        run_analysis, df, filename, False, settings.work_dir, settings.analysis_wait_seconds
    )
    request.app.state.sessions.put(request.state.sid, result)
    logger.info("Analysed upload (%d rows, %d kept)", result.summary["raw_rows"], result.summary["cleaned_rows"])
    return {
        "status": "success",
        **result.summary,
        "message": f"Successfully uploaded and analyzed '{filename}'.",
    }


@app.post("/api/sample")
def load_sample_dataset(request: Request):
    """Switch this session back to the clearly labeled synthetic sample dataset."""
    request.app.state.sessions.drop(request.state.sid)
    result = active_result(request)
    return {
        "status": "success",
        **result.summary,
        "message": "Synthetic sample dataset loaded.",
        "label": "SYNTHETIC_RESEARCH_DATASET",
        "note": f"{result.summary['cleaned_rows']:,} synthetic records generated for demonstration.",
    }


@app.get("/api/overview")
def get_overview(result: AnalysisResult = Depends(active_result)):
    """Top-level summary metrics, stress tier counts/shares, and daily activity averages."""
    return result.overview


@app.get("/api/cleaning-report")
def get_cleaning_report(result: AnalysisResult = Depends(active_result)):
    """Cleaning stages, rows removed by reason, outlier bounds and the 24 h budget check."""
    return result.cleaning


@app.get("/api/descriptive-stats")
def get_descriptive_stats(result: AnalysisResult = Depends(active_result)):
    """Descriptive statistics, stress-group comparisons (ANOVA, eta²), box plots and histograms."""
    return result.stats


@app.get("/api/correlations")
def get_correlations(result: AnalysisResult = Depends(active_result)):
    """Correlation matrices, partial correlation, significance tests, regressions and a scatter sample."""
    return result.correlations


@app.get("/api/insights")
def get_insights(result: AnalysisResult = Depends(active_result)):
    """Generated empirical findings and study limitations."""
    return result.insights


EXPORT_FORMATS = {
    "txt": "report.txt",
    "cleaned_csv": "cleaned_data.csv",
    "csv": "cleaned_data.csv",
    "descriptive_csv": "descriptive_stats.csv",
    "group_csv": "group_comparison.csv",
    "pearson_csv": "pearson_corr.csv",
    "spearman_csv": "spearman_corr.csv",
}


@app.get("/api/export-report")
async def export_report(
    format: str = Query("txt", description="txt, cleaned_csv, descriptive_csv, group_csv, pearson_csv, "
                                           "spearman_csv, json or zip"),
    result: AnalysisResult = Depends(active_result),
):
    """Downloadable report, processed CSVs, combined JSON, or a ZIP bundle with figures."""
    fmt = format.lower()
    if fmt in EXPORT_FORMATS:
        name = EXPORT_FORMATS[fmt]
        media = "text/plain; charset=utf-8" if name.endswith(".txt") else "text/csv; charset=utf-8"
        return FileResponse(result.path(name), media_type=media, filename=EXPORT_FILES[name])
    if fmt == "json":
        return JSONResponse(
            result.export_json(),
            headers={"Content-Disposition": 'attachment; filename="eduwell_analysis.json"'},
        )
    if fmt == "zip":
        await run_in_threadpool(ensure_figures, result, settings.analysis_wait_seconds)
        return Response(
            content=result.export_zip(),
            media_type="application/zip",
            headers={"Content-Disposition": 'attachment; filename="eduwell_analysis_bundle.zip"'},
        )
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Unsupported format '{format}'. Supported formats: {', '.join([*EXPORT_FORMATS, 'json', 'zip'])}.",
    )


@app.get("/api/figures/{figure_name}")
async def get_figure(figure_name: str, result: AnalysisResult = Depends(active_result)):
    """Serves a Matplotlib figure for the active dataset (rendered on first request)."""
    if figure_name not in FIGURE_NAMES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Figure '{figure_name}' not found. Available: {', '.join(FIGURE_NAMES)}.",
        )
    await run_in_threadpool(ensure_figures, result, settings.analysis_wait_seconds)
    path = result.figure_path(figure_name)
    if path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Figure '{figure_name}' is unavailable.")
    return FileResponse(path, media_type="image/png")


# ----------------------------------------------------------------------
# Web dashboard
# ----------------------------------------------------------------------
def _load_index_html() -> str:
    with open(os.path.join(FRONTEND_DIR, "index.html"), encoding="utf-8") as f:
        return f.read().replace("__VERSION__", APP_VERSION)


INDEX_HTML = _load_index_html()
app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="assets")


@app.get("/", include_in_schema=False)
def index():
    return HTMLResponse(_load_index_html(), headers={"Cache-Control": "no-cache, no-store, must-revalidate"})


@app.get("/docs", include_in_schema=False)
def docs_redirect():
    from starlette.responses import RedirectResponse
    return RedirectResponse(url="/api/docs")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=settings.host, port=settings.port, log_level=settings.log_level.lower())
