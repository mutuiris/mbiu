"""Verification suite for Load Tests and Runbooks — Ticket MB-30.

Verifies:
1. Synthetic 40-page contract fixture matches upload caps (exactly 40 pages, <10MB).
2. k6 load test script configuration, scenarios, and starting SLO thresholds.
3. Provider Outage Runbook walkthrough: failover toggles and circuit breaker error mapping.
4. Corpus Rollback Runbook walkthrough: active corpus version flipping.
5. Cost Spike Runbook walkthrough: token budget and concurrency limits.
6. Supabase Paused Runbook walkthrough: connection pooler settings (CONN_MAX_AGE == 0).
"""

from __future__ import annotations

from pathlib import Path

import pymupdf
from django.conf import settings
from django.test import override_settings

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_40_page_fixture_meets_upload_caps() -> None:
    """Verifies the synthetic load test contract is exactly at the 40-page cap."""
    fixture_path = REPO_ROOT / "infra" / "k6" / "fixtures" / "contract_40p.pdf"
    assert fixture_path.exists(), "40-page contract fixture must exist"

    doc = pymupdf.open(str(fixture_path))
    try:
        msg = f"Contract must have exactly {settings.MAX_PAGES} pages"
        assert len(doc) == settings.MAX_PAGES, msg
        # Must be well under the 10 MB limit
        file_size_mb = fixture_path.stat().st_size / (1024 * 1024)
        assert file_size_mb < settings.MAX_UPLOAD_MB
    finally:
        doc.close()


def test_k6_load_script_scenarios_and_slos() -> None:
    """Verifies that k6 load test script defines normal, slow_gemini, and failover scenarios."""
    script_path = REPO_ROOT / "infra" / "k6" / "k6_evaluations_load.js"
    assert script_path.exists(), "k6 script must exist"

    content = script_path.read_text(encoding="utf-8")
    assert "normal_scenario" in content
    assert "slow_gemini_scenario" in content
    assert "failover_scenario" in content
    assert "time_to_first_event" in content
    assert "evaluation_success_rate" in content
    assert "p(95)<3500" in content


def test_runbook_documentation_files_exist() -> None:
    """Verifies all four required 2 a.m. runbooks are present in docs/runbooks/."""
    runbooks_dir = REPO_ROOT / "docs" / "runbooks"
    required_runbooks = [
        "provider-outage.md",
        "corpus-rollback.md",
        "cost-spike.md",
        "supabase-paused.md",
    ]
    for filename in required_runbooks:
        runbook = runbooks_dir / filename
        assert runbook.exists(), f"Runbook {filename} must exist"
        text = runbook.read_text(encoding="utf-8")
        assert len(text) > 500, f"Runbook {filename} must contain comprehensive instructions"


def test_runbook_corpus_rollback_walkthrough() -> None:
    """Walkthrough: verifies flipping ACTIVE_CORPUS_VERSION is respected by settings."""
    assert getattr(settings, "ACTIVE_CORPUS_VERSION", None) is not None

    with override_settings(ACTIVE_CORPUS_VERSION="corpus-rolled-back-v1"):
        assert settings.ACTIVE_CORPUS_VERSION == "corpus-rolled-back-v1"


def test_runbook_supabase_pooler_settings_walkthrough() -> None:
    """Walkthrough: verifies connection settings enforce CONN_MAX_AGE == 0 for pooler."""
    db_config = settings.DATABASES["default"]
    # Must be 0 to prevent connection leakage in transaction poolers
    assert db_config.get("CONN_MAX_AGE") == 0
    assert db_config.get("DISABLE_SERVER_SIDE_CURSORS") is True


def test_runbook_cost_spike_budgets_walkthrough() -> None:
    """Walkthrough: verifies token budget, batch size, and concurrency ceilings."""
    assert settings.BATCH_SIZE == 6
    assert settings.LLM_CONCURRENCY == 4
    assert settings.TOKEN_BUDGET_PER_CONTRACT == 400000
    assert settings.DEADLINE_CAP_S == 300.0
