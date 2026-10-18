"""FastAPI upload endpoint.

Install with ``pip install -e ".[api]"``. The endpoint accepts a text payload
plus a flag specification, runs the deterministic scoring core, and returns the
canonical verdict with per-platform projections.

Scope note: this API scores. It does not extract claims or retrieve evidence -
those are L2/L3 and belong behind a separate, key-bearing service boundary so
that an air-gapped scoring deployment stays air-gapped.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse

from .ingest.canonical import from_text
from .pipeline import RawFlag, build_verdict
from .platforms import all_profiles, capability_matrix, project
from .render.vtt import overlay_spec, render_vtt
from .types import MediaType
from .validation import validate_verdict

app = FastAPI(
    title="omni-verify",
    version="0.1.0",
    description=(
        "Multi-platform content integrity engine. "
        "Emits a Compromised Content Ratio, an enforcement tier, and "
        "capability-filtered platform projections."
    ),
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "schema": "1.1.0"}


@app.get("/platforms")
def platforms() -> list[dict[str, Any]]:
    return capability_matrix()


@app.post("/score", response_model=None)
async def score(
    payload: UploadFile = File(...),
    flags: str = Form("[]"),
    stream_id: str = Form("STRM_UPLOAD"),
    platform: str = Form("Web"),
    genre: str = Form("MULTI"),
    confidence: float = Form(0.8),
    retrieval_available: bool = Form(True),
    analysis_mode: str = Form("FULL"),
    strict: bool = Form(True),
    render_vtt_track: bool = Form(False),
) -> JSONResponse | PlainTextResponse:
    import json

    try:
        raw_flags = json.loads(flags)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"flags is not valid JSON: {exc}") from exc

    text = (await payload.read()).decode("utf-8", errors="replace")
    if not text.strip():
        raise HTTPException(status_code=422, detail="payload is empty")

    content = from_text(
        stream_id=stream_id,
        platform=platform,
        text=text,
        media_type=MediaType.SOCIAL_POST,
        source_url=getattr(payload, "filename", None),
    )

    try:
        doc = build_verdict(
            content=content,
            flags=[RawFlag(**_coerce_flag(f)) for f in raw_flags],
            genre=genre,
            analysis_mode=analysis_mode,  # type: ignore[arg-type]
            analyzer_confidence=confidence,
            retrieval_available=retrieval_available,
            strict=False,  # report issues rather than 500
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    issues = validate_verdict(doc)
    if render_vtt_track and not issues:
        return PlainTextResponse(render_vtt(doc), media_type="text/vtt")

    doc["projections"] = {
        prof.platform_id: project(prof.platform_id, doc).to_dict()
        for prof in all_profiles()
    }
    doc["overlay_spec"] = overlay_spec(doc)
    if issues:
        doc["validation_issues"] = [str(i) for i in issues]
    return JSONResponse(doc, status_code=422 if issues else 200)


def _coerce_flag(spec: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "start", "end", "category", "severity", "verdict", "statement_made",
        "original_claim", "verified_fact", "explanation", "confidence",
        "retrieval_performed", "counter_evidence", "is_audio_claim",
        "timing_precision",
    }
    return {k: v for k, v in spec.items() if k in allowed}