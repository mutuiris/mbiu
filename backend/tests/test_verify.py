"""Tests for the verification rules and how the orchestrator applies them."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

from mbiu.api.schemas import ClauseResult, ClauseResultEvent, ClauseStatus, Evidence, Outcome
from mbiu.evaluation.orchestrator import evaluate_contract
from mbiu.evaluation.verify import ClauseComparisonProposal, Sent, reading_grade, verify
from mbiu.llm.gemini import Gemini
from tests.pdf_factories import create_synthetic_text_pdf

CLAUSE = (
    "The Label shall pay the Artist 10% of net receipts within sixty (60) days of each statement."
)
SENT = Sent(
    clause_id="4.1",
    clause_text=CLAUSE,
    evidence=[
        Evidence(
            evidence_id="ev-1",
            template_id="tpl-royalties",
            source_title="Synthetic model agreement",
            jurisdiction="KE",
            excerpt="The Label shall pay the Artist a royalty of 15% of gross receipts.",
        )
    ],
)
VALID = ClauseComparisonProposal(
    comparison=Outcome.WORSE_FOR_YOU,
    headline="Your share is smaller than the standard",
    what_it_says="You get 10% of net receipts (the money left after the label's costs).",
    what_it_means="The standard gives 15% of all the money, so you could earn less.",
    clause_quote="10% of net receipts",
    evidence_quote="15% of gross receipts",
    evidence_id="ev-1",
    clause_id="4.1",
    ask_them="Can my royalty be 15% of gross receipts instead of 10% of net?",
)


def failed(sent: Sent = SENT, **changes: Any) -> set[str]:
    return set(verify(VALID.model_copy(update=changes), sent))


def with_clause(text: str) -> Sent:
    return Sent(clause_id=SENT.clause_id, clause_text=text, evidence=SENT.evidence)


def test_a_grounded_plain_proposal_passes_every_rule() -> None:
    assert verify(VALID, SENT) == {}


def test_quotes_must_be_exact_substrings_of_what_was_sent() -> None:
    assert failed(clause_quote="15% of net receipts") == {"quotes_are_exact"}
    assert failed(clause_quote="10%  of net receipts") == {"quotes_are_exact"}
    assert failed(clause_quote=" ") == {"quotes_are_exact"}
    assert failed(evidence_quote="15% of net receipts") == {"quotes_are_exact"}
    assert failed(evidence_quote=None) == set()


def test_ids_must_belong_to_this_request_and_clause() -> None:
    assert "ids_are_real" in failed(evidence_id="ev-9")
    assert failed(clause_id="7.2") == {"ids_are_real"}
    assert failed(evidence_id="tpl-royalties") == set()
    assert failed(evidence_id=None, clause_id=None) == set()


def test_an_invented_number_fails() -> None:
    reasons = verify(VALID.model_copy(update={"what_it_means": "You wait 90 days."}), SENT)
    assert set(reasons) == {"numbers_are_grounded"}
    assert "90" in reasons["numbers_are_grounded"]
    assert failed(headline="You earn 12.5% here") == {"numbers_are_grounded"}
    assert failed(what_it_means="You could wait three years.") == {"numbers_are_grounded"}


def test_numbers_from_the_clause_or_template_pass_in_digits_or_words() -> None:
    assert failed(what_it_means="You are paid 60 days after each statement.") == set()
    assert failed(what_it_means="You are paid sixty days after each statement.") == set()
    assert failed(what_it_means="This is one of the money clauses.") == set()


def test_legal_conclusions_and_advice_to_sign_fail() -> None:
    assert failed(what_it_means="This clause is unenforceable.") == {"no_legal_conclusions"}
    assert failed(what_it_means="You should not sign this.") == {"no_legal_conclusions"}
    assert failed(headline="Your money is safe here") == {"no_legal_conclusions"}


def test_the_contracts_own_words_are_not_legal_conclusions() -> None:
    sent = with_clause(f"{CLAUSE} The Artist gets a guaranteed fee.")
    assert failed(sent, what_it_means="You also get a guaranteed fee.") == set()


def test_hard_reading_fails_and_the_grade_is_configurable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dense = (
        "Contractual remuneration notwithstanding, the aforementioned administrative "
        "deductions substantially diminish the artist's prospective entitlements."
    )
    assert reading_grade(dense) > 9
    assert failed(what_it_means=dense) == {"plain_language"}
    monkeypatch.setattr("django.conf.settings.MAX_READING_GRADE", 40.0)
    assert failed(what_it_means=dense) == set()


def test_jargon_must_be_explained_on_the_same_card() -> None:
    assert failed(what_it_says="You get 10% of net receipts.") == {"plain_language"}
    assert failed(what_it_means="The rights last in perpetuity.") == {"plain_language"}
    assert failed(what_it_means="The rights last in perpetuity (forever).") == set()
    assert failed(what_it_means="Costs are recoupable, which means taken from you.") == set()


def test_fields_must_fit_a_phone() -> None:
    assert failed(headline="x" * 81) == {"fits_a_phone"}
    assert failed(ask_them="Can my royalty be 15% of gross receipts" + " ok" * 50 + "?") == {
        "fits_a_phone"
    }


def test_ask_them_must_be_a_specific_question() -> None:
    assert failed(ask_them="Raise my royalty to 15% of gross receipts.") == {"usable_question"}
    assert failed(ask_them="Can you explain this?") == {"usable_question"}
    assert failed(ask_them="Is this fair?") == {"usable_question"}
    assert failed(ask_them=None) == set()


def test_money_needs_gross_or_net_on_both_sides() -> None:
    sent = with_clause("The Label shall pay the Artist 10% of all receipts.")
    no_basis = {
        "what_it_says": "You get 10% of all receipts.",
        "what_it_means": "The standard gives 15%.",
        "ask_them": "Can my royalty be 15% of gross receipts?",
        "clause_quote": "10% of all receipts",
    }
    assert failed(sent, **no_basis) == {"money_is_comparable"}
    assert failed(sent, comparison=Outcome.CANNOT_COMPARE, **no_basis) == set()
    gross_and_net = with_clause("The Label pays 10% of net receipts, the template 15% of gross.")
    assert "money_is_comparable" not in failed(gross_and_net)


def test_failures_are_counted_per_rule(monkeypatch: pytest.MonkeyPatch) -> None:
    counted: list[dict[str, str]] = []
    counter = SimpleNamespace(add=lambda amount, attributes: counted.append(attributes))
    monkeypatch.setattr("mbiu.evaluation.verify.failures_counter", counter)
    failed(evidence_id="ev-9", evidence_quote=None, ask_them="Is this fair?")
    assert sorted(a["rule"] for a in counted) == ["ids_are_real", "usable_question"]


class ScriptedGemini:
    """A Gemini client that returns the given proposals in order and records each call."""

    def __init__(self, *proposals: ClauseComparisonProposal) -> None:
        self.proposals = list(proposals)
        self.calls: list[dict[str, Any]] = []
        self.aio = SimpleNamespace(interactions=SimpleNamespace(create=self._create))

    async def _create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        return SimpleNamespace(
            status="completed",
            output_text=self.proposals.pop(0).model_dump_json(),
            model="gemini-3.8-flash",
            usage=SimpleNamespace(total_input_tokens=100, total_output_tokens=50),
        )


PDF_CLAUSE = "1. Royalties\nThe Company will pay the Artist 10% of net receipts after all costs."
GOOD = ClauseComparisonProposal(
    comparison=Outcome.WORSE_FOR_YOU,
    headline="Your share is smaller than the standard",
    what_it_says="You get 10% of net receipts (the money left after costs).",
    what_it_means="The standard gives at least 15% of all the money.",
    clause_quote="10% of net receipts",
    evidence_quote="15% to 20% of Gross Receipts",
    evidence_id="ev-1",
    ask_them="Can my royalty be 15% of gross receipts instead?",
)
INVENTED_NUMBER = GOOD.model_copy(update={"what_it_means": "The standard gives 25%."})
UNSENT_ID = GOOD.model_copy(update={"evidence_id": "tpl-never-sent"})


def run(client: ScriptedGemini, monkeypatch: pytest.MonkeyPatch) -> ClauseResult:
    monkeypatch.setattr("django.conf.settings.FAILOVER_ENABLED", False)

    async def collect() -> list[ClauseResult]:
        pdf = create_synthetic_text_pdf([PDF_CLAUSE])
        llm = Gemini(client, timeout_s=5.0)
        return [
            e.payload
            async for e in evaluate_contract(pdf_bytes=pdf, llm=llm)
            if isinstance(e, ClauseResultEvent)
        ]

    [result] = asyncio.run(collect())
    return result


def test_a_verified_proposal_is_sent_without_repair(monkeypatch: pytest.MonkeyPatch) -> None:
    client = ScriptedGemini(GOOD)
    result = run(client, monkeypatch)
    assert len(client.calls) == 1
    assert result.status == ClauseStatus.EVALUATED
    assert result.what_it_means == GOOD.what_it_means


def test_one_repair_names_the_failed_rule_and_its_fix_is_sent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = ScriptedGemini(INVENTED_NUMBER, GOOD)
    result = run(client, monkeypatch)
    assert len(client.calls) == 2
    assert "numbers_are_grounded" in str(client.calls[1])
    assert result.status == ClauseStatus.EVALUATED
    assert result.what_it_means == GOOD.what_it_means


@pytest.mark.parametrize("bad", [INVENTED_NUMBER, UNSENT_ID], ids=["invented", "unsent_id"])
def test_a_second_failure_becomes_cannot_compare_without_model_wording(
    bad: ClauseComparisonProposal, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = ScriptedGemini(bad, bad)
    result = run(client, monkeypatch)
    assert len(client.calls) == 2
    assert result.status == ClauseStatus.CANNOT_COMPARE
    assert result.comparison == Outcome.CANNOT_COMPARE
    model_wording = {bad.headline, bad.what_it_says, bad.what_it_means, bad.ask_them}
    assert not model_wording & {result.headline, result.what_it_says, result.what_it_means}
    assert result.ask_them is None
    assert result.evidence_quote is None
