"""Tests for the deterministic scoring in ARIS.

The scoring code lives inside the Heym workflow (workflows/main/main.json, node
"scoringCompute"). These tests pull that exact code out of the JSON and run it the
way Heym does: JSON on stdin, JSON on stdout. Nothing is copied, so the tests fail
if the workflow changes behaviour.
"""

import json
import random
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = sorted((ROOT / "workflows").rglob("*.json"))


def python_nodes():
    for path in WORKFLOWS:
        data = json.loads(path.read_text(encoding="utf-8"))
        for node in data.get("nodes", []):
            if node.get("type") == "pythonExec":
                yield path.relative_to(ROOT).as_posix(), node["data"]["label"], node["data"]["code"]


SCORING = next(code for _, label, code in python_nodes() if label == "scoringCompute")


def score(payload):
    proc = subprocess.run(
        [sys.executable, "-c", SCORING],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(proc.stdout)


def branches(level=80, crit=0, high=0, unpatched_days=0, contradictions=0, alternatives=3):
    """Branch outputs shaped like the real branch workflows, all at one quality level."""
    return {
        "github": {
            "commit_velocity": {"commit_velocity_trend_score": level},
            "bus_factor": {"bus_factor_score": level},
            "issue_health": {"issue_close_rate_score": level},
            "release_cadence": {"release_cadence_score": level},
            "contributor_count": 60 if level >= 80 else 5,
        },
        "security": {
            "severity_breakdown": {"critical": crit, "high": high},
            "days_since_oldest_unpatched": unpatched_days,
        },
        "community": {
            "scoring_proxies": {
                "docs_completeness": level,
                "tutorial_density": level,
                "setup_complexity": 100 - level,
                "api_surface_area": 100 - level,
                "debugging_difficulty": 100 - level,
            }
        },
        "production": {"production_score": level},
        "alternatives": {"alternatives": ["x"] * alternatives, "evaluated_tool_wins_when": "-"},
        "trajectory": {"adoption_momentum": level},
        "compression": {"compressed_findings": [], "contradictions": ["c"] * contradictions},
    }


# ---- every Python node in the workflow is valid code ----

@pytest.mark.parametrize("where,label,code", list(python_nodes()), ids=lambda v: v if isinstance(v, str) and len(v) < 40 else None)
def test_python_node_compiles(where, label, code):
    compile(code, f"{where}:{label}", "exec")


def test_workflow_has_18_python_nodes():
    assert len(list(python_nodes())) == 18


# ---- verdict bands ----

def band(weighted):
    return "ADOPT" if weighted >= 75 else "TRIAL" if weighted >= 60 else "HOLD" if weighted >= 40 else "AVOID"


@pytest.mark.parametrize("level,high", [(95, 0), (70, 1), (50, 3), (25, 5), (5, 6)])
def test_verdict_follows_weighted_score(level, high):
    out = score(branches(level=level, high=high))
    assert out["recommendation"] == band(out["weighted_score"])


def test_all_four_verdicts_are_reachable():
    seen = {score(branches(level=l, high=h))["recommendation"] for l, h in [(95, 0), (70, 1), (40, 3), (5, 6)]}
    assert seen == {"ADOPT", "TRIAL", "HOLD", "AVOID"}


def test_weights_sum_to_one():
    ns = {}
    exec(SCORING.split("# ===== TUNABLE CONSTANTS =====")[1].split("PRETTY")[0], ns)
    for name in ("DIM_WEIGHTS", "MAINT_W", "ECO_W", "LEARN_W"):
        assert sum(ns[name].values()) == pytest.approx(1.0), name


# ---- security veto ----

def test_security_veto_caps_a_strong_tool_at_hold():
    out = score(branches(level=95, crit=4))
    assert out["dimension_scores"]["security_risk"] < 30
    assert out["recommendation"] == "HOLD"
    assert out["recommendation_explanation"]["security_vetoed"] is True


def test_no_veto_when_security_is_fine():
    out = score(branches(level=95))
    assert out["recommendation"] == "ADOPT"
    assert out["recommendation_explanation"]["security_vetoed"] is False


def test_unpatched_penalty_is_capped():
    out = score(branches(level=95, unpatched_days=10_000))
    assert out["dimension_scores"]["security_risk"] == 75.0


# ---- repo-fit overrides ----

def test_already_used_forces_keep_and_strong_stack():
    payload = branches(level=50) | {"repo": {"repo_verdict": "ALREADY_USED"}}
    out = score(payload)
    assert out["recommendation"] == "KEEP"
    assert out["dimension_scores"]["stack_compatibility"] >= 90
    assert out["recommendation_explanation"]["first_party_production_boost_applied"] is True


def test_poor_fit_caps_stack():
    payload = branches(level=90) | {"stack": {"stack_compatibility": 95, "data_available": True}, "repo": {"repo_verdict": "POOR_FIT"}}
    assert score(payload)["dimension_scores"]["stack_compatibility"] <= 25


def test_migration_required_caps_stack_at_60():
    payload = branches(level=90) | {"stack": {"stack_compatibility": 95, "data_available": True}, "repo": {"repo_verdict": "MIGRATION_REQUIRED"}}
    assert score(payload)["dimension_scores"]["stack_compatibility"] == 60


# ---- confidence ----

def test_contradictions_lower_confidence():
    clean = score(branches(level=80))["confidence"]
    noisy = score(branches(level=80, contradictions=3))["confidence"]
    assert noisy < clean


def test_missing_data_lowers_confidence_and_drops_dimension():
    payload = branches(level=80)
    del payload["security"]
    out = score(payload)
    assert out["dimension_scores"]["security_risk"] is None
    assert out["confidence"] < score(branches(level=80))["confidence"]


def test_confidence_never_exceeds_095():
    payload = branches(level=100) | {"stack": {"stack_compatibility": 100, "data_available": True}}
    assert score(payload)["confidence"] <= 0.95


def test_no_branch_data_is_reported_not_scored():
    assert score({"nothing": 1}).get("debug_no_branches_found") is True


# ---- determinism and bounds ----

def test_same_evidence_gives_same_verdict():
    payload = branches(level=72, high=1, contradictions=1)
    runs = {json.dumps(score(payload), sort_keys=True) for _ in range(5)}
    assert len(runs) == 1


def test_random_evidence_stays_in_bounds():
    rng = random.Random(7)
    for _ in range(200):
        out = score(branches(
            level=rng.randint(0, 100),
            crit=rng.randint(0, 6),
            high=rng.randint(0, 6),
            unpatched_days=rng.randint(0, 900),
            contradictions=rng.randint(0, 6),
            alternatives=rng.randint(0, 6),
        ))
        assert out["recommendation"] in {"ADOPT", "TRIAL", "HOLD", "AVOID"}
        assert 0 <= out["weighted_score"] <= 100
        assert 0 <= out["confidence"] <= 0.95
        for v in out["dimension_scores"].values():
            assert v is None or 0 <= v <= 100
        if out["dimension_scores"]["security_risk"] < 30:
            assert out["recommendation"] in {"HOLD", "AVOID"}
