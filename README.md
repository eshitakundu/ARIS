# ARIS

**Technology Adoption Intelligence System**

ARIS evaluates software tools and libraries and produces an evidence-backed adoption recommendation for engineering teams.

Instead of relying on GitHub stars, blog posts, and intuition, ARIS collects signals from multiple sources, scores them across six dimensions, and generates a structured Adoption Decision Brief delivered as both email and PDF.

## The Problem

Questions such as:

* Should we adopt LangChain?
* Is CrewAI production-ready?
* Should we build on this dependency?

are often answered through ad-hoc research.

ARIS turns that process into a repeatable evaluation workflow by combining ecosystem data, security signals, repository health metrics, adoption evidence, and community sentiment into a transparent recommendation.

## How It Works

ARIS executes a fixed workflow that:

1. Collects evidence from multiple sources in parallel.
2. Extracts structured findings using LLMs.
3. Computes scores deterministically using Python.
4. Generates a recommendation (ADOPT / TRIAL / HOLD / AVOID).
5. Produces a formatted email and PDF brief.

### Evaluation Dimensions

* Maintenance Health
* Security Risk
* Stack Compatibility
* Ecosystem Maturity
* Production Adoption
* Learning Curve

## Design Principles

### Deterministic Scoring

LLMs never generate scores.

All numerical evaluation is performed in Python using documented scoring rules.

### Explainability

Every recommendation can be traced back to collected evidence and dimension-level scoring.

### Reproducibility

The workflow follows a predefined DAG rather than autonomous agent routing, producing predictable and auditable outputs.

### Confidence Over Certainty

Missing or conflicting data lowers confidence rather than directly affecting scores.

## Current Capabilities

* Multi-source technology evaluation
* Parallel evidence collection
* Security analysis using OSV data
* GitHub repository health analysis
* Weighted scoring engine
* HTML email generation
* PDF report generation
* Confidence scoring

## Tech Stack

* Heym (self-hosted fork)
* OpenRouter
* GPT OSS 120B
* Python
* Tavily
* GitHub MCP
* OSV API
* PyPI Stats API
* npm Downloads API

## Status

ARIS is currently in active development.

Planned work includes validation benchmarking, repository-aware compatibility analysis, human review gates, and multi-tool comparison workflows.

## Architecture

Architecture diagrams, sample reports, and workflow screenshots will be added as the project evolves.
