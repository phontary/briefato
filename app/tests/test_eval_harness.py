"""Tests for the Briefato quality harness (WORKSTREAM-EVAL).

Offline, no network: the integration test runs ``tools/eval/run_eval.py`` in mock
mode as a subprocess (fresh settings/DB), and the unit tests import the harness
modules directly — none of them touch the app package.

Run with::

    cd /workspace/briefato && .venv/bin/python -m pytest app/tests/test_eval_harness.py -q
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = REPO_ROOT / "tools" / "eval"
CASES_DIR = EVAL_DIR / "cases"

if str(EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(EVAL_DIR))

from eval_checks import (  # noqa: E402
    check_must_contain,
    check_must_not_contain,
    check_structure,
    contains,
    contains_strict,
)
from eval_corpus import CorpusError, load_cases  # noqa: E402
from eval_echo import ECHO_THRESHOLDS_BY_TYPE, ECHO_VERDICT, detect_echo, echo_threshold_for  # noqa: E402
from eval_judge import AXES, parse_judge_response  # noqa: E402
from run_eval import effective_dictation  # noqa: E402


# --------------------------------------------------------------------------- echo detector


def test_echo_detector_flags_verbatim_copy():
    dictation = (
        "Patient seit 3 Tagen Oberbauchschmerzen. Sonographie zeigt Gallensteine. "
        "Labor CRP 87 mg/l. Wir nahmen die Pat. stationaer auf.\n\nDiagnosen:\nCholezystolithiasis"
    )
    result = detect_echo(dictation, dictation)
    assert result.is_echo is True
    assert result.verdict == ECHO_VERDICT
    assert result.similarity == pytest.approx(1.0)
    assert result.content_echo is True


def test_echo_detector_passes_genuinely_rewritten_text():
    dictation = (
        "Patient seit 3 Tagen Oberbauchschmerzen, Sonographie zeigt Gallensteine, Labor CRP 87 mg/l. "
        "Wir nahmen die Pat. stationaer auf.\n\nDiagnosen:\nCholezystolithiasis"
    )
    rewritten = (
        "Die Patientin stellte sich mit seit drei Tagen bestehenden Schmerzen im rechten Oberbauch vor. "
        "Die bildgebende Diagnostik ergab Konkremente der Gallenblase. Der stationäre Aufenthalt diente der "
        "weiteren Abklärung und Schmerzbehandlung. Nach Beschwerdefreiheit erfolgte die Entlassung.\n\n"
        "Diagnosen:\nKonkremente der Gallenblase"
    )
    result = detect_echo(dictation, rewritten)
    assert result.is_echo is False
    assert result.verdict != ECHO_VERDICT
    assert result.similarity < 0.85
    assert result.content_echo is False


def test_echo_structural_labels_are_removed_before_comparison():
    # Only the block label is shared — that must not read as an echo.
    result = detect_echo("Diagnosen:\nAortenaneurysma", "Diagnosen:\nBandscheibenvorfall")
    assert result.is_echo is False


def test_echo_empty_output_is_not_an_echo():
    result = detect_echo("irgendein Diktat", "")
    assert result.is_echo is False
    assert result.similarity == 0.0


def test_echo_threshold_is_per_document_type():
    # Compression types legitimately share more of the input verbatim.
    assert echo_threshold_for("zusammenfassung") == 0.92
    assert echo_threshold_for("entlassmedikationsplan") == 0.92
    assert echo_threshold_for("arztbrief") == 0.85
    assert echo_threshold_for(None) == 0.85
    assert set(ECHO_THRESHOLDS_BY_TYPE) == {"zusammenfassung", "entlassmedikationsplan"}


# --------------------------------------------------------------------------- must_contain


def test_must_contain_reports_missing_items_and_coverage():
    result = check_must_contain("Diagnosen:\nCholezystitis und Rektumkarzinoms", ["Cholezystitis", "Rektumkarzinom", "Ileus"])
    assert result.matched == ["Cholezystitis", "Rektumkarzinom"]  # inflection tolerated
    assert result.missing == ["Ileus"]
    assert result.coverage == pytest.approx(2 / 3)


def test_must_not_contain_is_strict_and_colon_aware():
    # A forbidden label with a colon must not fire on the plain word.
    assert check_must_not_contain("die CT des Abdomens", ["CT:"]) == []
    assert check_must_not_contain("Labor: CRP 87", ["Labor:"]) == ["Labor:"]
    # No false positive inside a longer word.
    assert check_must_not_contain("Befund im Handgelenk", ["Dg.:"]) == []
    assert check_must_not_contain("Troponinwert 0,01", ["Troponin"]) == []
    assert check_must_not_contain("Troponin 0,01", ["Troponin"]) == ["Troponin"]


def test_label_matching_distinguishes_colon_from_bare_word():
    assert contains("die CT des Abdomens", "CT:") is False
    assert contains("CT: Abdomen", "CT:") is True
    assert contains_strict("Cholezystitis bei Cholezystolithiasis", "Cholezystitis") is True


# --------------------------------------------------------------------------- structure


_SAMPLE_ARZTBRIEF = (
    "Die Patientin stellte sich vor. Wir nahmen die Patientin stationär auf.\n\n"
    "ambulante Therapieempfehlungen nach der Entlassung:\nWundkontrolle.\n\n"
    "Diagnosen:\nCholezystitis\n\n"
    "Nebenerkrankungen:\nkeine\n\n"
    "Therapie-Maßnahmen auf der Station:\nAnalgesie"
)


def test_structure_checks_presence_and_order():
    result = check_structure(
        _SAMPLE_ARZTBRIEF,
        "arztbrief",
        [
            "ambulante Therapieempfehlungen nach der Entlassung:",
            "Diagnosen:",
            "Nebenerkrankungen:",
            "Therapie-Maßnahmen auf der Station:",
        ],
    )
    assert result.ok is True
    assert result.missing == []


def test_structure_flags_wrong_block_order():
    wrong = (
        "Diagnosen:\nCholezystitis\n\n"
        "ambulante Therapieempfehlungen nach der Entlassung:\nWundkontrolle."
    )
    result = check_structure(wrong, "arztbrief", ["ambulante Therapieempfehlungen nach der Entlassung:", "Diagnosen:"])
    assert result.order_ok is False
    assert result.ok is False


# --------------------------------------------------------------------------- judge


def test_judge_response_parsing_is_clamped_and_averaged():
    payload = json.dumps(
        {
            "structure": {"score": 4, "reason": "Reihenfolge korrekt", "citation": ""},
            "completeness": {"score": 3, "reason": "ein Fakt fehlt", "citation": "Nausea"},
            "no_invention": {"score": 9, "reason": "zu hoch", "citation": ""},
            "register": {"score": 5, "reason": "fachlich", "citation": ""},
            "plain_text": {"score": 5, "reason": "kein Markdown", "citation": ""},
            "overall_comment": "solide",
        }
    )
    result = parse_judge_response(payload)
    assert set(result.scores) == set(AXES)
    assert result.scores["no_invention"] == 5  # clamped from 9
    assert result.mean == pytest.approx((4 + 3 + 5 + 5 + 5) / 5)
    assert result.citations["completeness"] == "Nausea"


def test_judge_prompt_cites_the_dictation_as_the_only_source():
    from eval_judge import build_judge_prompt

    system, user = build_judge_prompt("Diktat-Text", "Ausgabe-Text", "arztbrief")
    assert "DIKTAT" in user and "Diktat-Text" in user
    assert "Ausgabe-Text" in user
    assert "JSON" in user


def test_judge_prompt_is_reference_aware():
    """(c) The no_invention axis must be told that reference-grounded standard procedure
    is not an invention — and the reference text must be in the prompt."""
    from eval_judge import build_judge_prompt

    reference = (
        "Standardtechnik einer laparoskopischen Cholezystektomie: Team-Time-out, "
        "Hautdesinfektion, Capnoperitoneum, Präparation, Wundverschluss."
    )
    _system, user = build_judge_prompt("Diktat-Text", "Ausgabe-Text", "operationsbericht", reference=reference)
    assert "REFERENZWISSEN" in user
    assert reference in user
    assert "aus Referenz" in user
    assert "als BELEGT" in user
    assert "no_invention" in user

    # without a reference the dictation stays the only admissible source
    _system_plain, plain = build_judge_prompt("Diktat-Text", "Ausgabe-Text", "operationsbericht")
    assert "REFERENZWISSEN" not in plain
    assert "aus Referenz" not in plain


def test_corpus_carries_allowed_reference_for_op_cases():
    cases = {case.id: case for case in load_cases(CASES_DIR, only=["opbericht-01", "opbericht-02"])}
    assert set(cases) == {"opbericht-01", "opbericht-02"}
    for case in cases.values():
        lowered = case.allowed_reference.lower()
        assert case.allowed_reference.strip()
        assert "team-time-out" in lowered
        assert "wundverschluss" in lowered


# --------------------------------------------------------------------------- corpus


def test_corpus_loads_and_validates_cases():
    cases = load_cases(CASES_DIR)
    assert len(cases) >= 12
    ids = {case.id for case in cases}
    assert {"entlassbrief-01", "opbericht-01", "zusammenfassung-01", "pflegebericht-01"} <= ids
    for case in cases:
        assert case.doc_type
        assert case.dictation.strip()
        assert isinstance(case.must_contain, tuple)


def test_corpus_filter_and_unknown_id():
    cases = load_cases(CASES_DIR, only=["entlassbrief-01", "ambulant-01"])
    assert [case.id for case in cases] == ["ambulant-01", "entlassbrief-01"]
    with pytest.raises(CorpusError):
        load_cases(CASES_DIR, only=["does-not-exist"])


def test_enrich_appends_raw_sources():
    case = next(c for c in load_cases(CASES_DIR, only=["entlassbrief-01"]))
    plain = effective_dictation(case, enrich=False)
    enriched = effective_dictation(case, enrich=True)
    assert plain == case.dictation
    assert len(enriched) > len(plain)
    assert case.sources[0].label in enriched


# --------------------------------------------------------------------------- end-to-end (subprocess)


def test_runner_executes_subset_and_writes_scorecard(tmp_path):
    out_dir = tmp_path / "runs"
    tmp_dir = tmp_path / "work"
    cmd = [
        sys.executable,
        str(EVAL_DIR / "run_eval.py"),
        "--provider",
        "mock",
        "--only",
        "entlassbrief-01",
        "--only",
        "pflegebericht-01",
        "--out",
        str(out_dir),
        "--tmp-dir",
        str(tmp_dir),
    ]
    env = {
        **os.environ,
        "BRIEFATO_LLM_MOCK": "true",
        "BRIEFATO_ENV": "dev",
        "BRIEFATO_SECRET_KEY": "eval-test-secret",
    }
    env.pop("BRIEFATO_BRAIN_DIR", None)
    completed = subprocess.run(
        cmd, cwd=str(REPO_ROOT), env=env, capture_output=True, text=True, timeout=300
    )
    assert completed.returncode == 0, completed.stderr

    scorecards = list(out_dir.glob("*/scorecard.md"))
    assert len(scorecards) == 1
    scorecard = scorecards[0].read_text(encoding="utf-8")

    # The mock banner must be loud and unmistakable.
    assert "MOCK — misst KEINE Schreibqualität" in scorecard
    assert "misst die **Maschinerie**" in scorecard

    run_files = list(out_dir.glob("*/run.json"))
    assert len(run_files) == 1
    run = json.loads(run_files[0].read_text(encoding="utf-8"))

    assert run["is_mock"] is True
    assert run["provider"] == "mock"
    assert len(run["cases"]) == 2
    assert all(case["status"] == "ok" for case in run["cases"])
    # The mock copies its input — the harness must say so.
    assert run["aggregate"]["echo_count"] >= 1
    assert "Echo" in scorecard

    # The generated text is persisted per case so a defect can be diffed after the run.
    case_files = sorted(path.name for path in out_dir.glob("*/cases/*.txt"))
    assert "entlassbrief-01.txt" in case_files
    assert "pflegebericht-01.txt" in case_files
    assert run["cases"][0]["content_file"].startswith("cases/")
    assert "cases/entlassbrief-01.txt" in scorecard
    # The per-type echo threshold is reported in the scorecard.
    assert "Echo-Schwelle" in scorecard


def test_runner_repeat_reports_median_and_range(tmp_path):
    out_dir = tmp_path / "runs"
    tmp_dir = tmp_path / "work"
    cmd = [
        sys.executable,
        str(EVAL_DIR / "run_eval.py"),
        "--provider",
        "mock",
        "--only",
        "ambulant-01",
        "--repeat",
        "3",
        "--out",
        str(out_dir),
        "--tmp-dir",
        str(tmp_dir),
    ]
    env = {**os.environ, "BRIEFATO_LLM_MOCK": "true", "BRIEFATO_SECRET_KEY": "eval-test-secret"}
    env.pop("BRIEFATO_BRAIN_DIR", None)
    completed = subprocess.run(cmd, cwd=str(REPO_ROOT), env=env, capture_output=True, text=True, timeout=300)
    assert completed.returncode == 0, completed.stderr

    run = json.loads(next(iter(out_dir.glob("*/run.json"))).read_text(encoding="utf-8"))
    assert run["repeat"] == 3
    case = run["cases"][0]
    repeat = case["echo_repeat"]
    assert repeat["n"] == 3
    assert len(repeat["similarities"]) == 3
    assert repeat["min"] <= repeat["median"] <= repeat["max"]
    assert case["echo"]["threshold"] == 0.85

    case_dir = next(out_dir.glob("*/cases"))
    assert (case_dir / "ambulant-01.txt").exists()
    assert (case_dir / "ambulant-01.run1.txt").exists()
    assert (case_dir / "ambulant-01.run3.txt").exists()


def test_compare_mode_produces_a_diff_table(tmp_path):
    out_dir = tmp_path / "runs"
    tmp_dir = tmp_path / "work"
    base = [
        sys.executable,
        str(EVAL_DIR / "run_eval.py"),
        "--provider",
        "mock",
        "--only",
        "ambulant-01",
        "--out",
        str(out_dir),
    ]
    env = {**os.environ, "BRIEFATO_LLM_MOCK": "true", "BRIEFATO_SECRET_KEY": "eval-test-secret"}
    env.pop("BRIEFATO_BRAIN_DIR", None)
    first = subprocess.run(base + ["--tmp-dir", str(tmp_dir / "a")], cwd=str(REPO_ROOT), env=env, capture_output=True, text=True, timeout=300)
    assert first.returncode == 0, first.stderr
    run_a = sorted(out_dir.glob("*/run.json"))[-1]

    second = subprocess.run(base + ["--tmp-dir", str(tmp_dir / "b")], cwd=str(REPO_ROOT), env=env, capture_output=True, text=True, timeout=300)
    assert second.returncode == 0, second.stderr
    run_b = sorted(out_dir.glob("*/run.json"))[-1]

    compare = subprocess.run(
        [sys.executable, str(EVAL_DIR / "run_eval.py"), "--compare", str(run_a), str(run_b), "--out", str(tmp_path / "cmp")],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert compare.returncode == 0, compare.stderr
    assert "Vergleich" in compare.stdout
    assert "Mean Echo-Similarity" in compare.stdout
