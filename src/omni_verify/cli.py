"""Command line interface.

Deliberately capable of running the scorer with **no** API keys: the CCR and
tier engine are pure computation, so a reviewer can reproduce any published
ratio offline from a verdict document.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .ingest.canonical import from_text
from .pipeline import build_verdict
from .platforms import capability_matrix, project
from .render.vtt import overlay_spec, render_vtt
from .validation import validate_verdict


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def cmd_score(args: argparse.Namespace) -> int:
    content = from_text(
        stream_id=args.stream_id,
        platform=args.platform,
        text=Path(args.file).read_text(encoding="utf-8"),
        source_url=args.file,
    )
    flags = [
        _raw_flag_from_spec(spec) for spec in json.loads(Path(args.flags).read_text("utf-8"))
    ]
    doc = build_verdict(
        content=content,
        flags=flags,
        analyzer_confidence=args.confidence,
        retrieval_available=not args.no_retrieval,
        stream_timestamp=args.timestamp,
        strict=not args.lenient,
    )
    _emit(doc, args)
    return 0


def _raw_flag_from_spec(spec: dict[str, Any]):
    from .pipeline import RawFlag

    return RawFlag(
        start=spec.get("start", 0),
        end=spec.get("end", 0),
        category=spec.get("category", "SCIENCE_TECH"),
        severity=spec.get("severity", "MODERATE"),
        verdict=spec.get("verdict", "UNVERIFIED"),
        statement_made=spec.get("statement_made", ""),
        original_claim=spec.get("original_claim", ""),
        verified_fact=spec.get("verified_fact", ""),
        explanation=spec.get("explanation", ""),
        confidence=spec.get("confidence", 0.5),
        retrieval_performed=spec.get("retrieval_performed", True),
        counter_evidence=spec.get("counter_evidence", []),
    )


def cmd_validate(args: argparse.Namespace) -> int:
    doc = _load(Path(args.file))
    issues = validate_verdict(doc)
    if not issues:
        print(f"VALID  {doc.get('stream_metadata', {}).get('stream_id')}")
        return 0
    for issue in issues:
        print(f"INVALID  {issue}")
    return 1


def cmd_project(args: argparse.Namespace) -> int:
    doc = _load(Path(args.file))
    platforms = args.platforms or [p["platform_id"] for p in capability_matrix()]
    out = {p: project(p, doc).to_dict() for p in platforms}
    print(json.dumps(out, indent=2))
    return 0


def cmd_rerender(args: argparse.Namespace) -> int:
    doc = _load(Path(args.file))
    print(render_vtt(doc))
    print("--- overlay spec ---")
    print(json.dumps(overlay_spec(doc), indent=2))
    return 0


def cmd_matrix(args: argparse.Namespace) -> int:
    rows = capability_matrix()
    cols = ["platform_id", "authority", "monetization_block", "strike_system", "native_labels"]
    widths = {c: max(len(c), *(len(str(r[c])) for r in rows)) for c in cols}
    print(" | ".join(c.ljust(widths[c]) for c in cols))
    print("-+-".join("-" * widths[c] for c in cols))
    for row in rows:
        print(" | ".join(str(row[c]).ljust(widths[c]) for c in cols))
    return 0


def _emit(doc: dict[str, Any], args: argparse.Namespace) -> None:
    if args.vtt:
        print(render_vtt(doc))
    print(json.dumps(doc, indent=2))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="omni-verify")
    sub = parser.add_subparsers(dest="command", required=True)

    p_score = sub.add_parser("score", help="score a text payload against a flag spec")
    p_score.add_argument("file")
    p_score.add_argument("flags", help="JSON file of RawFlag specs")
    p_score.add_argument("--stream-id", default="STRM_LOCAL")
    p_score.add_argument("--platform", default="Web")
    p_score.add_argument("--confidence", type=float, default=0.8)
    p_score.add_argument("--timestamp", default="")
    p_score.add_argument("--no-retrieval", action="store_true",
                          help="simulate retrieval failure (verdicts cap at UNVERIFIED)")
    p_score.add_argument("--lenient", action="store_true",
                         help="emit even if validation fails")
    p_score.add_argument("--vtt", action="store_true", help="also print a WebVTT track")
    p_score.set_defaults(func=cmd_score)

    p_val = sub.add_parser("validate", help="validate a verdict document")
    p_val.add_argument("file")
    p_val.set_defaults(func=cmd_validate)

    p_proj = sub.add_parser("project", help="project a verdict onto platforms")
    p_proj.add_argument("file")
    p_proj.add_argument("--platforms", nargs="*", default=None)
    p_proj.set_defaults(func=cmd_project)

    p_rr = sub.add_parser("render", help="re-render VTT and overlay spec")
    p_rr.add_argument("file")
    p_rr.set_defaults(func=cmd_rerender)

    p_mx = sub.add_parser("matrix", help="print the platform capability matrix")
    p_mx.set_defaults(func=cmd_matrix)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ValueError, KeyError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())