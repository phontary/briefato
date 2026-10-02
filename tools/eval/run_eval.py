#!/usr/bin/env python3
"""Briefato quality harness — run the real pipeline over a synthetic corpus and measure.

WHAT THIS IS
------------
`BRIEFATO_LLM_MOCK=true` makes the mock provider produce a shape-correct draft that
largely mirrors the input. The existing tests therefore prove the MACHINERY
(routing, retrieval, rule enforcement, storage, isolation) — not writing quality.
This harness is the quality gate: it runs every corpus case through the **real**
`generate_letter` pipeline and computes, per case:

* **deterministic findings** — the existing R1–R67 rule checker (reused, not
  reimplemented) hard/soft counts and rule ids;
* **echo detection** — `difflib.SequenceMatcher` similarity + token Jaccard between
  the dictation and the output, verdict ``ECHO (keine eigene Formulierung)`` > 0.85;
* **must_contain / must_not_contain** coverage (human quality expectations);
* **structural checks** — block presence + order;
* **optional LLM judge** (`--judge-model`) — 0–5 rubric scores with reasons/citations.

Output: a timestamped ``run.json`` + ``scorecard.md`` per run, and a model-vs-model
diff table via ``--compare RUN_A RUN_B``.

USAGE
-----
    # offline self-check, mock provider, all cases
    tools/eval/run_eval.py --provider mock --out /tmp/eval-mock

    # a real model (A/B) — requires a reachable OpenAI-compatible endpoint
    tools/eval/run_eval.py --provider openai --model mistral-large-latest \
        --base-url https://api.mistral.ai/v1 --out tools/eval/runs --judge-model gpt-4o-mini

    # compare two finished runs
    tools/eval/run_eval.py --compare runs/A/run.json runs/B/run.json

Stdlib + the repo venv only. No network in mock mode. Single-shot process: settings
and the SQLAlchemy engine are bound at import time from the environment below.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
REPO_ROOT = EVAL_DIR.parents[1]
APP_DIR = REPO_ROOT / "app"

# Sibling modules (run as a script: sys.path[0] is this directory).
from eval_checks import check_must_contain, check_must_not_contain, check_structure  # noqa: E402
from eval_corpus import Case, load_cases  # noqa: E402
from eval_echo import ECHO_THRESHOLD, ECHO_THRESHOLDS_BY_TYPE, detect_echo, echo_threshold_for  # noqa: E402
from eval_judge import AXES, judge_output  # noqa: E402

MOCK_BANNER = "MOCK — misst KEINE Schreibqualität"
REAL_BANNER = "Echter Modelllauf — Schreibqualität wird gemessen"

LETTERHEAD = {
    "practice_name": "Praxis Dr. Beispiel",
    "full_name": "Dr. med. Beispiel",
    "street": "Musterweg 1",
    "zip": "12345",
    "city": "Musterstadt",
    "phone": "0123 456789",
    "email": "praxis@example.test",
}


# --------------------------------------------------------------------------- helpers


def _ensure_paths() -> None:
    if str(APP_DIR) not in sys.path:
        sys.path.insert(0, str(APP_DIR))


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-") or "run"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def configure_env(args: argparse.Namespace, tmp_dir: str) -> None:
    """Set the environment BEFORE importing the app (settings+engine bind at import)."""
    os.environ["BRIEFATO_DATA_DIR"] = tmp_dir
    os.environ.setdefault("BRIEFATO_SECRET_KEY", "briefato-eval-secret-key")
    os.environ["BRIEFATO_DB_URL"] = f"sqlite:///{Path(tmp_dir) / 'eval.db'}"
    os.environ.setdefault("BRIEFATO_ENV", "dev")
    os.environ.pop("BRIEFATO_BRAIN_DIR", None)  # repo-relative default brain
    if args.provider == "mock":
        os.environ["BRIEFATO_LLM_MOCK"] = "true"
        os.environ.setdefault("BRIEFATO_LLM_MODEL", "briefato-mock-de-1")
    else:
        os.environ["BRIEFATO_LLM_MOCK"] = "false"
        if args.model:
            os.environ["BRIEFATO_LLM_MODEL"] = args.model
        if args.base_url:
            os.environ["BRIEFATO_LLM_BASE_URL"] = args.base_url
        # API key comes from BRIEFATO_LLM_API_KEY in the environment — never a CLI flag,
        # never logged, never written to the run file.


def effective_dictation(case: Case, enrich: bool) -> str:
    """The text actually sent to the pipeline.

    Default: the case's curated ``dictation``. With ``--enrich``: the dictation plus
    the full, messy ``sources`` block — the un-distilled KIS export, which is the
    input the enrichment path (Musterbrief-derived standard content) has to cope with.
    """
    if enrich and case.sources:
        return case.dictation + "\n\n" + case.sources_block()
    return case.dictation


def _seed(db):
    from briefato.models import Patient, Subscription, User

    user = User(
        email=f"eval-{uuid.uuid4().hex[:10]}@briefato-eval.test",
        password_hash="x",
        full_name="Dr. med. Beispiel",
        practice_name="Praxis Dr. Beispiel",
        street="Musterweg 1",
        zip="12345",
        city="Musterstadt",
        phone="0123 456789",
        tax_id="12/345/67890",
        ui_lang="de",
    )
    db.add(user)
    db.commit()
    patient = Patient(
        user_id=user.id,
        first_name="Anna",
        last_name="Muster",
        birth_date=date(1968, 5, 3),
        sex="w",
        insurance="AOK",
        insurance_number="A123456789",
        street="Beispielweg 2",
        zip="12345",
        city="Musterstadt",
        phone="0123 111222",
        email="anna.muster@example.test",
    )
    db.add(patient)
    db.add(Subscription(user_id=user.id, plan_code="klinik", letters_quota=400, letters_used=0))
    db.commit()
    return user, patient


def _finding_ids(checks: list[dict]) -> tuple[list[str], list[str]]:
    hard: set[str] = set()
    soft: set[str] = set()
    for check in checks or []:
        for finding in check.get("findings") or []:
            rule_id = str(finding.get("rule_id") or "")
            if not rule_id:
                continue
            if finding.get("severity") == "hard":
                hard.add(rule_id)
            else:
                soft.add(rule_id)
    return sorted(hard), sorted(soft)


# --------------------------------------------------------------------------- one case


def evaluate_case(
    case: Case,
    db,
    user,
    patient,
    settings,
    *,
    enrich: bool,
    judge_provider,
    judge_model: str,
    repeat: int = 1,
) -> dict:
    from briefato import security
    from briefato.pipeline import generate as gen_mod
    from briefato.pipeline.providers import PipelineError

    dictation = effective_dictation(case, enrich)
    repeat = max(1, int(repeat))
    record: dict = {
        "id": case.id,
        "title": case.title,
        "doc_type_expected": case.doc_type,
        "enrich": bool(enrich),
        "repeat": repeat,
        "status": "ok",
        "error": "",
        "notes": case.notes,
        "content_file": f"cases/{case.id}.txt",
    }

    contents: list[str] = []
    docs: list[tuple[str, dict, object]] = []
    for _ in range(repeat):
        try:
            letter = gen_mod.generate_letter(
                db,
                user=user,
                patient=patient,
                kind=case.doc_type,
                dictation=dictation,
                letterhead=dict(LETTERHEAD),
            )
        except PipelineError as exc:
            record["status"] = "failed"
            record["error"] = f"{type(exc).__name__}: {exc}"
            return record
        content = security.decrypt_field(letter.content_enc) or ""
        last = getattr(letter, "last_check", {}) or {}
        contents.append(content)
        docs.append((content, last, letter))

    actual_type = str(docs[0][1].get("doc_type") or docs[0][2].kind)
    threshold = echo_threshold_for(actual_type)
    echoes = [detect_echo(dictation, content, threshold=threshold) for content, _, _ in docs]
    similarities = [echo.similarity for echo in echoes]
    # Representative run = the median-similarity one, so a single noisy run cannot
    # decide the record (echo similarity is unstable across runs — see docs/05 §5).
    representative = sorted(range(len(similarities)), key=lambda index: similarities[index])[len(similarities) // 2]
    content, last, _letter = docs[representative]
    echo = echoes[representative]

    hard_ids, soft_ids = _finding_ids(last.get("checks") or [])
    record.update(
        {
            "doc_type_actual": actual_type,
            "doc_type_match": actual_type == case.doc_type,
            "retried": bool(last.get("retried")),
            "findings": {
                "hard_count": len(hard_ids),
                "soft_count": len(soft_ids),
                "hard_ids": hard_ids,
                "soft_ids": soft_ids,
            },
            "echo": echo.as_dict(),
            "echo_repeat": {
                "n": len(echoes),
                "similarities": [round(value, 4) for value in similarities],
                "median": round(sorted(similarities)[len(similarities) // 2], 4),
                "min": round(min(similarities), 4),
                "max": round(max(similarities), 4),
                "threshold": threshold,
                "representative_index": representative,
            },
            "must_contain": check_must_contain(content, list(case.must_contain)).as_dict(),
            "must_not_contain_violations": check_must_not_contain(content, list(case.must_not_contain)),
            "structure": check_structure(content, actual_type, list(case.expected_blocks)).as_dict(),
            "tokens_in": int(getattr(docs[representative][2], "tokens_in", 0) or 0),
            "tokens_out": int(getattr(docs[representative][2], "tokens_out", 0) or 0),
            "content_chars": len(content),
            # Raw generated text for the run dir; popped before run.json is written.
            "content_text": content,
            "contents": contents,
        }
    )

    if judge_provider is not None:
        judged = judge_output(
            judge_provider, dictation=dictation, output=content, doc_type=actual_type, model=judge_model
        )
        record["judge"] = judged.as_dict()
    else:
        record["judge"] = None

    return record


# --------------------------------------------------------------------------- aggregate


def aggregate(results: list[dict]) -> dict:
    completed = [r for r in results if r.get("status") == "ok"]
    similarities = [r["echo"]["similarity"] for r in completed]
    echo_cases = [r["id"] for r in completed if r["echo"]["is_echo"]]
    content_echo_cases = [r["id"] for r in completed if r["echo"].get("content_echo")]
    hard_total = sum(r["findings"]["hard_count"] for r in completed)
    soft_total = sum(r["findings"]["soft_count"] for r in completed)
    cases_with_hard = [r["id"] for r in completed if r["findings"]["hard_count"] > 0]
    matched = sum(len(r["must_contain"]["matched"]) for r in completed)
    contain_total = sum(r["must_contain"]["total"] for r in completed)
    not_contain_violations = [r["id"] for r in completed if r["must_not_contain_violations"]]
    structure_failures = [r["id"] for r in completed if not r["structure"]["ok"]]
    doc_type_mismatches = [r["id"] for r in completed if not r["doc_type_match"]]
    judge_means = [r["judge"]["mean"] for r in completed if r.get("judge") and r["judge"].get("mean") is not None]

    return {
        "cases": len(results),
        "completed": len(completed),
        "failed": [r["id"] for r in results if r.get("status") != "ok"],
        "mean_similarity": round(sum(similarities) / len(similarities), 4) if similarities else None,
        "mean_jaccard": round(
            sum(r["echo"]["jaccard"] for r in completed) / len(completed), 4
        )
        if completed
        else None,
        "echo_cases": echo_cases,
        "echo_count": len(echo_cases),
        "echo_baseline": f"{len(echo_cases)}/{len(completed)}",
        "content_echo_cases": content_echo_cases,
        "content_echo_count": len(content_echo_cases),
        "content_echo_baseline": f"{len(content_echo_cases)}/{len(completed)}",
        "hard_findings_total": hard_total,
        "soft_findings_total": soft_total,
        "cases_with_hard_findings": cases_with_hard,
        "must_contain_matched": matched,
        "must_contain_total": contain_total,
        "must_contain_coverage": round(matched / contain_total, 4) if contain_total else 1.0,
        "must_not_contain_violating_cases": not_contain_violations,
        "structure_failures": structure_failures,
        "doc_type_mismatches": doc_type_mismatches,
        "mean_judge_score": round(sum(judge_means) / len(judge_means), 2) if judge_means else None,
    }


# --------------------------------------------------------------------------- outputs


def _fmt(value, suffix: str = "") -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.3f}{suffix}"
    if isinstance(value, list):
        return ", ".join(str(v) for v in value) or "—"
    return f"{value}{suffix}"


def _scorecard(run: dict) -> str:
    agg = run["aggregate"]
    is_mock = run["is_mock"]
    banner = MOCK_BANNER if is_mock else REAL_BANNER
    lines: list[str] = []
    lines.append("# Briefato — Qualitäts-Scorecard")
    lines.append("")
    if is_mock:
        lines.append(f"> ⚠️ **{MOCK_BANNER}**")
        lines.append(">")
        lines.append(
            "> Dieser Lauf nutzt den Mock-Provider. Er misst die **Maschinerie** (Routing, "
            "Retrieval, Block-/Regelkonformität, Speicherung) — **nicht** die Schreibqualität "
            "eines Modells. Ein Echtheits-Urteil erfordert `--provider openai` mit einem echten "
            "Modell und der freigegebenen (lawyer/DSGVO-Approved) Route."
        )
    else:
        lines.append(f"> ✅ **{REAL_BANNER}**")
    lines.append("")
    lines.append("## Lauf")
    lines.append("")
    lines.append(f"- **Run-ID:** `{run['run_id']}`")
    lines.append(f"- **Zeit (UTC):** {run['timestamp']}")
    lines.append(f"- **Provider:** `{run['provider']}` · **Modell:** `{run['model']}`")
    lines.append(f"- **Base-URL:** {run.get('base_url') or '—'}")
    lines.append(f"- **Enrich (Rohquellen einbezogen):** {'ja' if run['enrich'] else 'nein'}")
    lines.append(f"- **LLM-Judge:** {run.get('judge_model') or '— (nicht konfiguriert)'}")
    lines.append(f"- **Fälle:** {agg['completed']}/{agg['cases']} erfolgreich")
    if int(run.get("repeat", 1) or 1) > 1:
        lines.append(f"- **Wiederholungen pro Fall:** {int(run['repeat'])} (Echo als Median + Bereich)")
    lines.append("")
    lines.append("## Gesamt")
    lines.append("")
    lines.append("| Metrik | Wert |")
    lines.append("|---|---|")
    lines.append(f"| Mean Echo-Similarity | {_fmt(agg['mean_similarity'])} |")
    lines.append(f"| Mean Token-Jaccard | {_fmt(agg['mean_jaccard'])} |")
    _per_type_thresholds = ", ".join(f"{key} {value:.2f}" for key, value in sorted(ECHO_THRESHOLDS_BY_TYPE.items()))
    lines.append(
        f"| Echo-Schwelle | {ECHO_THRESHOLD:.2f} (Standard)"
        + (f"; {_per_type_thresholds}" if _per_type_thresholds else "")
        + " |"
    )
    lines.append(f"| **Echo-Fälle** | **{agg['echo_baseline']}** |")
    lines.append(f"| Content-Echo-Fälle (Token-Jaccard > 0.85) | {agg.get('content_echo_baseline', '—')} |")
    lines.append(f"| Harte Regel-Findings (Summe) | {agg['hard_findings_total']} |")
    lines.append(f"| Weiche Regel-Findings (Summe) | {agg['soft_findings_total']} |")
    lines.append(f"| Fälle mit harten Findings | {_fmt(len(agg['cases_with_hard_findings']))} |")
    lines.append(f"| must_contain-Abdeckung | {_fmt(agg['must_contain_coverage'])} ({agg['must_contain_matched']}/{agg['must_contain_total']}) |")
    lines.append(f"| must_not_contain-Verstöße | {_fmt(len(agg['must_not_contain_violating_cases']))} |")
    lines.append(f"| Strukturelle Fehlschläge | {_fmt(len(agg['structure_failures']))} |")
    lines.append(f"| Typ-Triage-Fehlschläge | {_fmt(len(agg['doc_type_mismatches']))} |")
    lines.append(f"| Mean LLM-Judge (0–5) | {_fmt(agg['mean_judge_score'])} |")
    if agg["failed"]:
        lines.append(f"| Fehlgeschlagene Fälle | {', '.join(agg['failed'])} |")
    lines.append("")
    lines.append("## Pro Fall")
    lines.append("")
    lines.append("| Fall | Typ | Typ✓ | Hard | Soft | must✓ | Echo-Sim | Jaccard | Echo? | Struktur |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for item in run["cases"]:
        if item.get("status") != "ok":
            lines.append(f"| `{item['id']}` | {item['doc_type_expected']} | — | — | — | — | — | — | FEHLER | — |")
            continue
        contain = f"{len(item['must_contain']['matched'])}/{item['must_contain']['total']}"
        lines.append(
            "| `{id}` | {typ} | {typ_ok} | {hard} | {soft} | {contain} | {sim} | {jac} | {echo} | {struct} |".format(
                id=item["id"],
                typ=item["doc_type_actual"],
                typ_ok="✓" if item["doc_type_match"] else "✗",
                hard=item["findings"]["hard_count"],
                soft=item["findings"]["soft_count"],
                contain=contain,
                sim=_fmt(item["echo"]["similarity"]),
                jac=_fmt(item["echo"]["jaccard"]),
                echo="ECHO" if item["echo"]["is_echo"] else ("C-ECHO" if item["echo"].get("content_echo") else "—"),
                struct="ok" if item["structure"]["ok"] else "✗",
            )
        )
    lines.append("")
    lines.append("## Details")
    lines.append("")
    for item in run["cases"]:
        lines.append(f"### `{item['id']}` — {item['title']}")
        lines.append("")
        if item.get("status") != "ok":
            lines.append(f"- **FEHLER:** {item['error']}")
            lines.append("")
            continue
        lines.append(f"- Erwarteter Typ: `{item['doc_type_expected']}` · tatsächlich: `{item['doc_type_actual']}`"
                     f" {'✓' if item['doc_type_match'] else '✗'}" + (" (Retry ausgelöst)" if item.get("retried") else ""))
        lines.append(f"- Regeln: {item['findings']['hard_count']} hart / {item['findings']['soft_count']} weich"
                     + (f" — hart: {', '.join(item['findings']['hard_ids'])}" if item["findings"]["hard_ids"] else ""))
        missing = item["must_contain"]["missing"]
        lines.append(f"- must_contain: {len(item['must_contain']['matched'])}/{item['must_contain']['total']}"
                     + (f" — fehlt: {', '.join(missing)}" if missing else ""))
        if item["must_not_contain_violations"]:
            lines.append(f"- **must_not_contain-Verstoß:** {', '.join(item['must_not_contain_violations'])}")
        lines.append(f"- Echo: similarity={item['echo']['similarity']:.3f}, token_ratio={item['echo']['token_ratio']:.3f}, "
                     f"jaccard={item['echo']['jaccard']:.3f} → {item['echo']['verdict']}"
                     + (" (Content-Echo: alle Inhaltswörter geteilt)" if item['echo'].get('content_echo') and not item['echo']['is_echo'] else ""))
        repeat = item.get("echo_repeat") or {}
        if int(repeat.get("n", 1) or 1) > 1:
            values = ", ".join(f"{value:.3f}" for value in repeat.get("similarities", []))
            lines.append(
                f"- Echo über {repeat['n']} Läufe: median={_fmt(repeat.get('median'))}, "
                f"Bereich {_fmt(repeat.get('min'))}–{_fmt(repeat.get('max'))} (Werte: {values}) — "
                "einzelne Läufe sind verrauscht, der Median zählt"
            )
        lines.append(
            f"- Echo-Schwelle (Typ `{item['doc_type_actual']}`): {_fmt(item['echo']['threshold'])} | "
            f"Text: `{item.get('content_file', 'cases/' + item['id'] + '.txt')}`"
        )
        structure = item["structure"]
        if structure["missing"] or not structure["order_ok"] or structure["canonical_missing"]:
            lines.append(f"- Struktur: fehlende Blöcke {structure['missing'] or '—'}, "
                         f"Reihenfolge {'ok' if structure['order_ok'] else 'verletzt'}, "
                         f"kanonisch fehlend {structure['canonical_missing'] or '—'}")
        if item.get("judge"):
            judge = item["judge"]
            if judge.get("error"):
                lines.append(f"- LLM-Judge: **Fehler** — {judge['error']}")
            else:
                lines.append(f"- LLM-Judge ({judge.get('model') or 'judge'}): mean={judge.get('mean')} "
                             f"{judge['scores']}")
                for axis in AXES:
                    if axis in judge.get("reasons", {}) and judge["reasons"][axis]:
                        cite = judge.get("citations", {}).get(axis) or ""
                        lines.append(f"    - {axis}: {judge['reasons'][axis]}" + (f" — „{cite}“" if cite else ""))
        if item.get("notes"):
            lines.append(f"- Hinweis: {item['notes']}")
        lines.append("")
    return "\n".join(lines)


def _load_run(path: str) -> dict:
    candidate = Path(path)
    if candidate.is_dir():
        candidates = sorted(candidate.glob("run.json"))
        if not candidates:
            raise FileNotFoundError(f"no run.json in {candidate}")
        candidate = candidates[-1]
    return json.loads(candidate.read_text(encoding="utf-8"))


def compare_markdown(run_a: dict, run_b: dict) -> str:
    lines: list[str] = []
    lines.append("# Briefato — Modell A/B Vergleich")
    lines.append("")
    lines.append(f"- **A:** `{run_a['run_id']}` — provider `{run_a['provider']}`, model `{run_a['model']}`"
                 + (f" ({MOCK_BANNER})" if run_a["is_mock"] else ""))
    lines.append(f"- **B:** `{run_b['run_id']}` — provider `{run_b['provider']}`, model `{run_b['model']}`"
                 + (f" ({MOCK_BANNER})" if run_b["is_mock"] else ""))
    if run_a["is_mock"] or run_b["is_mock"]:
        lines.append("")
        lines.append(f"> ⚠️ Mindestens ein Lauf ist ein **{MOCK_BANNER}**-Lauf. Echo-Kennzahlen sind dann "
                     "eine Aussage über die Maschinerie, kein Schreibqualitätsvergleich.")
    lines.append("")
    lines.append("## Gesamtvergleich")
    lines.append("")
    lines.append("| Metrik | A | B | Δ (B−A) |")
    lines.append("|---|---|---|---|")
    a, b = run_a["aggregate"], run_b["aggregate"]

    def row(label, key):
        va, vb = a.get(key), b.get(key)
        delta = "—"
        if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
            delta = f"{vb - va:+.3f}"
        lines.append(f"| {label} | {_fmt(va)} | {_fmt(vb)} | {delta} |")

    row("Mean Echo-Similarity", "mean_similarity")
    row("Mean Token-Jaccard", "mean_jaccard")
    lines.append(f"| Echo-Fälle | {a['echo_baseline']} | {b['echo_baseline']} | "
                 f"{b['echo_count'] - a['echo_count']:+d} |")
    lines.append(f"| Harte Findings (Summe) | {a['hard_findings_total']} | {b['hard_findings_total']} | "
                 f"{b['hard_findings_total'] - a['hard_findings_total']:+d} |")
    lines.append(f"| must_contain-Abdeckung | {_fmt(a['must_contain_coverage'])} | {_fmt(b['must_contain_coverage'])} | "
                 f"{b['must_contain_coverage'] - a['must_contain_coverage']:+.3f} |")
    lines.append(f"| Strukturelle Fehlschläge | {len(a['structure_failures'])} | {len(b['structure_failures'])} | "
                 f"{len(b['structure_failures']) - len(a['structure_failures']):+d} |")
    lines.append(f"| Mean LLM-Judge | {_fmt(a['mean_judge_score'])} | {_fmt(b['mean_judge_score'])} | "
                 + (f"{b['mean_judge_score'] - a['mean_judge_score']:+.2f} |"
                    if isinstance(a.get("mean_judge_score"), (int, float)) and isinstance(b.get("mean_judge_score"), (int, float))
                    else "— |"))
    lines.append("")
    lines.append("## Pro Fall")
    lines.append("")
    lines.append("| Fall | Sim A | Sim B | Echo A | Echo B | Hard A | Hard B | must✓ A | must✓ B |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    a_cases = {item["id"]: item for item in run_a["cases"]}
    b_cases = {item["id"]: item for item in run_b["cases"]}
    for case_id in sorted(set(a_cases) | set(b_cases)):
        ca, cb = a_cases.get(case_id), b_cases.get(case_id)
        sa = _fmt(ca["echo"]["similarity"]) if ca and ca.get("status") == "ok" else "—"
        sb = _fmt(cb["echo"]["similarity"]) if cb and cb.get("status") == "ok" else "—"
        ea = "ECHO" if ca and ca.get("status") == "ok" and ca["echo"]["is_echo"] else "—"
        eb = "ECHO" if cb and cb.get("status") == "ok" and cb["echo"]["is_echo"] else "—"
        ha = ca["findings"]["hard_count"] if ca and ca.get("status") == "ok" else "—"
        hb = cb["findings"]["hard_count"] if cb and cb.get("status") == "ok" else "—"
        ma = f"{len(ca['must_contain']['matched'])}/{ca['must_contain']['total']}" if ca and ca.get("status") == "ok" else "—"
        mb = f"{len(cb['must_contain']['matched'])}/{cb['must_contain']['total']}" if cb and cb.get("status") == "ok" else "—"
        lines.append(f"| `{case_id}` | {sa} | {sb} | {ea} | {eb} | {ha} | {hb} | {ma} | {mb} |")
    lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------- driver


def run(args: argparse.Namespace) -> int:
    _ensure_paths()
    tmp_dir = args.tmp_dir or tempfile.mkdtemp(prefix="briefato-eval-")
    os.makedirs(tmp_dir, exist_ok=True)
    configure_env(args, tmp_dir)

    from briefato.config import get_settings
    from briefato.db import SessionLocal, init_db
    from briefato.pipeline.providers import OpenAICompatProvider, PipelineProviderError

    settings = get_settings()
    init_db()

    judge_provider = None
    if args.judge_model:
        from types import SimpleNamespace

        judge_settings = SimpleNamespace(
            llm_base_url=args.judge_base_url or settings.llm_base_url,
            llm_model=args.judge_model,
            llm_api_key=os.environ.get("BRIEFATO_LLM_API_KEY", ""),
            llm_timeout_s=getattr(settings, "llm_timeout_s", 180),
        )
        if not judge_settings.llm_api_key:
            print("[eval] --judge-model gesetzt, aber BRIEFATO_LLM_API_KEY fehlt — Judge übersprungen.", file=sys.stderr)
        else:
            judge_provider = OpenAICompatProvider(judge_settings)

    cases = load_cases(args.cases_dir, only=args.only)
    is_mock = bool(getattr(settings, "llm_mock", True))
    run_id = f"{_now().strftime('%Y%m%d-%H%M%S')}-{_slug(args.provider)}-{_slug(settings.llm_model)}"
    out_dir = Path(args.out) / run_id
    cases_out = out_dir / "cases"
    out_dir.mkdir(parents=True, exist_ok=True)

    db = SessionLocal()
    try:
        user, patient = _seed(db)
        results: list[dict] = []
        print(f"[eval] {len(cases)} Fälle · provider={args.provider} · model={settings.llm_model}"
              + (" · enrich" if args.enrich else "")
              + (f" · repeat={args.repeat}" if args.repeat and args.repeat > 1 else "")
              + (f" · judge={args.judge_model}" if judge_provider else ""))
        for case in cases:
            outcome = evaluate_case(
                case, db, user, patient, settings,
                enrich=args.enrich, judge_provider=judge_provider, judge_model=args.judge_model or "",
                repeat=max(1, int(args.repeat)),
            )
            # Persist the generated text so a defect can be diffed after the run.
            representative = outcome.pop("content_text", "")
            all_contents = outcome.pop("contents", [])
            if representative:
                cases_out.mkdir(parents=True, exist_ok=True)
                (cases_out / f"{case.id}.txt").write_text(representative, encoding="utf-8")
                if len(all_contents) > 1:
                    for index, text in enumerate(all_contents, 1):
                        (cases_out / f"{case.id}.run{index}.txt").write_text(text, encoding="utf-8")
            results.append(outcome)
            if outcome.get("status") == "ok":
                sim = outcome["echo"]["similarity"]
                repeat_note = ""
                if outcome.get("echo_repeat", {}).get("n", 1) > 1:
                    repeat_note = f" [{outcome['echo_repeat']['min']:.3f}–{outcome['echo_repeat']['max']:.3f}]"
                print(
                    f"  - {case.id:<26} typ={outcome['doc_type_actual']:<18} "
                    f"hard={outcome['findings']['hard_count']} "
                    f"must={len(outcome['must_contain']['matched'])}/{outcome['must_contain']['total']} "
                    f"echo_sim={sim:.3f}{repeat_note} {'ECHO' if outcome['echo']['is_echo'] else ''}"
                )
            else:
                print(f"  - {case.id:<26} FEHLER: {outcome['error']}", file=sys.stderr)
    finally:
        db.close()

    run_record = {
        "run_id": run_id,
        "timestamp": _now().isoformat(timespec="seconds"),
        "provider": args.provider,
        "model": settings.llm_model,
        "base_url": "" if is_mock else str(getattr(settings, "llm_base_url", "")),
        "enrich": bool(args.enrich),
        "repeat": max(1, int(args.repeat)),
        "judge_model": args.judge_model or "",
        "is_mock": is_mock,
        "quality_claim": MOCK_BANNER if is_mock else REAL_BANNER,
        "prompt_version": _prompt_version(),
        "aggregate": aggregate(results),
        "cases": results,
    }

    run_path = out_dir / "run.json"
    scorecard_path = out_dir / "scorecard.md"
    run_path.write_text(json.dumps(run_record, ensure_ascii=False, indent=2), encoding="utf-8")
    scorecard_path.write_text(_scorecard(run_record), encoding="utf-8")

    agg = run_record["aggregate"]
    print("")
    print(f"[eval] Echo-Baseline: {agg['echo_baseline']} (mean similarity {agg['mean_similarity']})")
    print(f"[eval] Content-Echo (Token-Jaccard>0.85): {agg.get('content_echo_baseline', '—')} "
          f"(mean jaccard {agg['mean_jaccard']})")
    print(f"[eval] harte Findings gesamt: {agg['hard_findings_total']} "
          f"in {len(agg['cases_with_hard_findings'])} Fall/Fällen")
    print(f"[eval] must_contain-Abdeckung: {agg['must_contain_coverage']:.1%} "
          f"({agg['must_contain_matched']}/{agg['must_contain_total']})")
    if agg["mean_judge_score"] is not None:
        print(f"[eval] mean LLM-Judge: {agg['mean_judge_score']}/5")
    print(f"[eval] run.json  -> {run_path}")
    print(f"[eval] scorecard -> {scorecard_path}")
    print("")
    if is_mock:
        print(f"[eval] ⚠️  {MOCK_BANNER} — dieser Lauf beweist die Maschinerie, NICHT die Schreibqualität.")
    return 0


def _prompt_version() -> str:
    try:
        from briefato.brain.prompt_assembly import PROMPT_VERSION

        return PROMPT_VERSION
    except Exception:  # noqa: BLE001
        return ""


def compare(args: argparse.Namespace) -> int:
    run_a = _load_run(args.compare[0])
    run_b = _load_run(args.compare[1])
    markdown = compare_markdown(run_a, run_b)
    out_dir = Path(args.out) if args.out else EVAL_DIR / "runs"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"compare-{run_a['run_id']}__vs__{run_b['run_id']}.md"
    out_path.write_text(markdown, encoding="utf-8")
    print(markdown)
    print(f"\n[eval] Vergleich -> {out_path}")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Briefato Qualitätsmessung (Eval-Harness)")
    parser.add_argument("--provider", choices=("mock", "openai"), default="mock")
    parser.add_argument("--model", default="", help="Modellname (OpenAI-kompatibel)")
    parser.add_argument("--base-url", default="", help="Basis-URL des OpenAI-kompatiblen Endpoints")
    parser.add_argument("--enrich", action="store_true", help="Rohquellen (sources) zusätzlich als Eingabe")
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="Jeden Fall N-mal laufen lassen und Echo als Median+Bereich ausweisen (Default 1; "
        "einzelne Läufe sind verrauscht)",
    )
    parser.add_argument("--only", action="append", default=None, help="Nur diese Fall-ID(s) laufen lassen")
    parser.add_argument("--out", default=str(EVAL_DIR / "runs"), help="Ausgabeverzeichnis")
    parser.add_argument("--cases-dir", default=None, help="Alternatives Corpus-Verzeichnis")
    parser.add_argument("--tmp-dir", default=None, help="Arbeitsverzeichnis für DB/Logs (Default: tempfile)")
    parser.add_argument("--judge-model", default="", help="Optionales Judge-Modell (OpenAI-kompatibel)")
    parser.add_argument("--judge-base-url", default="", help="Basis-URL des Judge-Endpoints")
    parser.add_argument("--compare", nargs=2, metavar=("RUN_A", "RUN_B"), help="Zwei Läufe vergleichen")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.compare:
        return compare(args)
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
