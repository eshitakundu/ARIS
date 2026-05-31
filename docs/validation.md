# ARIS — Validation Test Plan

Run this **after** the security-branch fix (delete the leftover `httpSecurityRisk → securityCompute` edge + set `securityCompute` inputExpression to `$mergeSecurityInputs`) and the `scoringCompute` replacement.

The goal of validation is **not** "are the numbers perfect" — heuristics never are. It's to prove two things a reviewer will ask:
1. **Ranking** — ARIS scores known-healthy tools above known-bad ones.
2. **Behaviour** — verdicts land in the right band, the security veto fires, and missing data lowers *confidence*, not the *score*.

---

## 0. Smoke test first (5 runs, ~10 min)

Before the full set, confirm the recent fixes actually took. Run these and eyeball the `traceScoreCompute` output.

| # | Input (`repo_or_tool` / `evaluation_context`) | What MUST be true now |
|---|---|---|
| S1 | `fastapi` / building a REST API in Python | `production_adoption` reflects stars+SO+dependents (not just case studies); `stack_compatibility = null`; `data_completeness ≤ 0.83` |
| S2 | `kubernetes` / container orchestration | `security_risk = null`, `data_available:false`; `confidence` lower than S1 — **not** security 100 |
| S3 | `express` / Node.js web server | registry routed as `npm`; trajectory used the npm path (not the Tavily fallback) |
| S4 | `requests` / HTTP client in Python | `security_risk` populated with a real `severity_breakdown`; score < 100 only if unpatched CVEs exist |
| S5 | `asdfqwerzzz` / anything | graceful: decomposer fails → `errorHandler`, or empty branches → low `confidence`. No silent 100s, no crash |

If S1 and S2 behave, the integration fixes are live. If S2 shows `security_risk = 100`, your `securityCompute` is still reading `$httpSecurityRisk.body` — fix the input expression.

---

## 1. The validation set (15 tools)

Run each through the full workflow and record the brief. Ground truth = the *expected band* and *expected rank* (1 = healthiest). Bands: **ADOPT ≥ 75 · TRIAL ≥ 60 · HOLD ≥ 40 · AVOID < 40**.

> Pick tools whose health is uncontroversial so the ground truth is defensible. Spot-check each tool's real state before trusting it as a label (e.g., glance at its GitHub + OSV) — a few of these can drift over time.

| Rank | Tool | Registry | Context | Expected band | Expected-strong dims | Expected-weak dims |
|---|---|---|---|---|---|---|
| 1 | `react` | npm | building a web frontend | ADOPT | maintenance, ecosystem, production | — |
| 2 | `fastapi` | PyPI | building a REST API | ADOPT | maintenance, learning, ecosystem | stack (null) |
| 3 | `numpy` | PyPI | numerical computing | ADOPT | maintenance, production, ecosystem | — |
| 4 | `express` | npm | Node.js web server | ADOPT | production, ecosystem | velocity (mature/slow) |
| 5 | `pydantic` | PyPI | data validation | ADOPT/TRIAL | maintenance, ecosystem | — |
| 6 | `langchain` | PyPI | building a RAG pipeline | TRIAL | ecosystem, velocity | bus factor, production, security |
| 7 | `polars` | PyPI | fast dataframes | TRIAL | velocity, ecosystem | production (younger) |
| 8 | `drizzle-orm` | npm | TypeScript ORM | TRIAL | velocity | production, maturity |
| 9 | `htmx` | npm | hypermedia frontend | TRIAL | enthusiasm, velocity | bus factor (small team) |
| 10 | `dspy` | PyPI | LLM prompt programming | TRIAL/HOLD | velocity | production, docs, maturity |
| 11 | `moment` | npm | date handling | HOLD | ecosystem (legacy) | velocity (maintenance mode), trajectory (declining) |
| 12 | `nose` | PyPI | Python testing | HOLD/AVOID | — | velocity, cadence (deprecated) |
| 13 | `request` | npm | HTTP client (Node) | AVOID/HOLD | ecosystem (legacy huge) | velocity (officially deprecated 2020), maintenance |
| 14 | `left-pad` | npm | string padding | AVOID | — | maintenance, production, ecosystem |
| 15 | *(a package with a known **unpatched critical** CVE — check OSV first)* | PyPI/npm | — | HOLD (via veto) | — | **security** (veto must cap at HOLD) |

**Coverage this gives you:** both registries; ADOPT→AVOID spread; mature-but-slow (express/moment) vs fast-but-young (polars/dspy); a deprecated package (request); an abandoned one (left-pad); and an explicit **security-veto** case (#15).

---

## 2. Edge-case / robustness tests

| Case | Input | Expected behaviour |
|---|---|---|
| Non-package tool | `kubernetes`, `vscode` | `security_risk = null` (registry `none`); confidence lower; no crash |
| Acronym tool name | `dspy`, `mcp` | `validate_queries` keeps queries on-domain (no gaming/shopping drift); sane results |
| Registry casing | force decomposer to emit `pypi` | `dataExtract` normalises to `PyPI`; OSV returns data; trajectory takes PyPI path |
| Zero-CVE known package | a small, clean PyPI lib | `security_risk` high (≈100) **with** `data_available:true` — this is correct (real signal), distinct from the `null` no-data case |
| Repo with no releases | a tool that ships via tags only | `release_cadence` handles missing release (`days_since` large, low cadence score), no crash |
| Garbage input | `asdfqwerzzz` | decomposer error → `errorHandler`; or empty branches → very low confidence |

---

## 3. Pass criteria

Score the run against these. The first two are the ones worth putting on a slide.

1. **Pairwise ranking (the headline metric).** For every (healthy, unhealthy) pair where ground-truth rank differs by a clear margin, ARIS's `weighted_score` must order them correctly. **Target: ≥ 90% pairwise win-rate.** In particular, *every* ADOPT-set tool must outscore *every* AVOID-set tool (100%).
2. **Band hit-rate.** Verdict lands in the expected band. **Target: ≥ 70% exact, ≥ 90% within ±1 band** (borderline tools straddling TRIAL/HOLD are fine).
3. **Security veto fires.** Test #15 must come back **HOLD** with `security_vetoed:true`, regardless of how high its other dimensions are.
4. **Honest confidence.** Non-package inputs and tools with missing branches show **lower confidence**, and their *scores* are not inflated by the missing dimension (stack/security `null`, not 100/fallback).
5. **Monotonic security.** No tool with more unpatched criticals scores *higher* on `security_risk` than one with fewer.
6. **No silent failures.** Every run either completes or routes to `errorHandler`; no run emits `debug_no_branches_found`.

If 1–4 pass, the product is demo-ready and the weights are defensible. If pairwise ranking is < 90%, look at which dimension is mis-ranking and adjust that dimension's internal weights (not the headline `DIM_WEIGHTS`) first.

---

## 4. Score it automatically

Collect results into a CSV (template in §5), then run this. It needs only the standard library.

```python
# score_validation.py  —  python3 score_validation.py results.csv
import csv, sys, itertools

BAND = {"ADOPT": 4, "TRIAL": 3, "HOLD": 2, "AVOID": 1}

rows = list(csv.DictReader(open(sys.argv[1] if len(sys.argv) > 1 else "results.csv")))
for r in rows:
    r["expected_rank"] = int(r["expected_rank"])
    r["aris_score"] = float(r["aris_score"])

# 1) pairwise ranking win-rate (lower expected_rank = healthier = should score higher)
wins = total = adopt_vs_avoid_fail = 0
for a, b in itertools.combinations(rows, 2):
    if a["expected_rank"] == b["expected_rank"]:
        continue
    better, worse = (a, b) if a["expected_rank"] < b["expected_rank"] else (b, a)
    total += 1
    if better["aris_score"] > worse["aris_score"]:
        wins += 1
    elif better["expected_band"] == "ADOPT" and worse["expected_band"] == "AVOID":
        adopt_vs_avoid_fail += 1
pairwise = wins / total * 100 if total else 0

# 2) band hit-rate (exact + within 1)
exact = within1 = 0
for r in rows:
    got, exp = BAND.get(r["aris_verdict"].upper(), 0), BAND.get(r["expected_band"].split("/")[0].upper(), 0)
    if got == exp: exact += 1
    if abs(got - exp) <= 1: within1 += 1
n = len(rows)

# 3) Spearman rank correlation (aris_score vs healthiness = -expected_rank)
def spearman(xs, ys):
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i]); r = [0]*len(v); i = 0
        while i < len(v):
            j = i
            while j+1 < len(v) and v[order[j+1]] == v[order[i]]: j += 1
            for k in range(i, j+1): r[order[k]] = (i+j)/2 + 1
            i = j+1
        return r
    rx, ry = ranks(xs), ranks(ys); nn = len(xs)
    d2 = sum((a-b)**2 for a, b in zip(rx, ry))
    return 1 - 6*d2/(nn*(nn*nn-1)) if nn > 1 else 0.0
rho = spearman([r["aris_score"] for r in rows], [-r["expected_rank"] for r in rows])

print(f"tools evaluated     : {n}")
print(f"pairwise win-rate   : {pairwise:.1f}%   (target >= 90%)")
print(f"ADOPT>AVOID failures: {adopt_vs_avoid_fail}   (target 0)")
print(f"band exact hit      : {exact}/{n} = {exact/n*100:.0f}%   (target >= 70%)")
print(f"band within +/-1    : {within1}/{n} = {within1/n*100:.0f}%   (target >= 90%)")
print(f"Spearman rho        : {rho:.2f}   (target >= 0.7)")
```

---

## 5. Results tracker (CSV template)

Save as `results.csv`, fill one row per run (read the values off `traceScoreCompute` / the brief):

```csv
tool,registry,expected_band,expected_rank,aris_verdict,aris_score,security,confidence,notes
react,npm,ADOPT,1,,,,,
fastapi,PyPI,ADOPT,2,,,,,
numpy,PyPI,ADOPT,3,,,,,
express,npm,ADOPT,4,,,,,
pydantic,PyPI,ADOPT,5,,,,,
langchain,PyPI,TRIAL,6,,,,,
polars,PyPI,TRIAL,7,,,,,
drizzle-orm,npm,TRIAL,8,,,,,
htmx,npm,TRIAL,9,,,,,
dspy,PyPI,TRIAL,10,,,,,
moment,npm,HOLD,11,,,,,
nose,PyPI,HOLD,12,,,,,
request,npm,AVOID,13,,,,,
left-pad,npm,AVOID,14,,,,,
SECURITY_CASE,PyPI,HOLD,15,,,,,
```

Fill `aris_verdict, aris_score, security, confidence` after each run, then `python3 score_validation.py results.csv`.

---

## What "ready" looks like

The product is demo-ready when, on this set:
- pairwise win-rate ≥ 90% and **zero** ADOPT-beats-AVOID failures,
- the security veto case returns HOLD,
- non-package inputs return lower confidence with `null` (not 100) security,
- and Spearman ρ ≥ 0.7.

That single table of results — plus the ρ — is the most convincing artifact you can put in the README and in front of an interviewer. It turns "I picked these weights" into "here's the evidence they rank reality correctly."
