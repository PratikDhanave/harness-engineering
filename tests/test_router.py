from harness.orchestration.router import (
    DEFAULT_RULES,
    RouteDecision,
    Router,
    Specialist,
)


def test_routes_billing_phrase():
    decision = Router().route("Please issue a refund for my last invoice")
    assert decision.specialist == Specialist.BILLING.value
    assert decision.matched_intent in {"refund", "invoice"}


def test_routes_code_phrase():
    decision = Router().route("The build fails to compile with a cryptic error")
    assert decision.specialist == Specialist.CODE.value
    assert decision.matched_intent in {"compile", "error"}


def test_routes_research_phrase():
    decision = Router().route("Can you find a paper I can cite for this claim?")
    assert decision.specialist == Specialist.RESEARCH.value
    assert decision.matched_intent in {"paper", "cite", "research", "study"}


def test_unknown_input_falls_back():
    decision = Router().route("hello there, nice weather today")
    assert decision == RouteDecision(
        specialist=Specialist.FALLBACK.value, matched_intent=None
    )


def test_matching_is_case_insensitive():
    decision = Router().route("URGENT: my INVOICE is wrong")
    assert decision.specialist == Specialist.BILLING.value
    assert decision.matched_intent == "invoice"


def test_custom_injected_rule_table():
    # A caller extends the vocabulary without touching the module.
    rules = {"visa": Specialist.BILLING, "segfault": Specialist.CODE}
    router = Router(rules)

    assert router.route("my visa was declined").specialist == Specialist.BILLING.value
    assert router.route("it ends in a segfault").specialist == Specialist.CODE.value
    # A default keyword is NOT in the custom table, so it must fall back.
    assert router.route("about the invoice").specialist == Specialist.FALLBACK.value


def test_injected_table_is_copied_defensively():
    rules = {"invoice": Specialist.BILLING}
    router = Router(rules)
    rules.clear()  # mutating the caller's dict must not affect the router
    assert router.route("about the invoice").matched_intent == "invoice"


def test_default_rules_left_unmodified_by_router():
    # Constructing a Router with no args must not alias/mutate DEFAULT_RULES.
    before = dict(DEFAULT_RULES)
    Router().rules["invoice"] = Specialist.CODE
    assert DEFAULT_RULES == before


def test_cross_specialist_tie_breaks_by_table_order_not_text_position():
    # "error" (CODE) appears BEFORE "invoice" (BILLING) in the text, but "invoice"
    # comes first in the rule table, so BILLING wins. The tie-break is table order,
    # not where the keyword sits in the message — the module's subtlest contract.
    decision = Router().route("I got an error on my invoice")
    assert decision.specialist == Specialist.BILLING.value
    assert decision.matched_intent == "invoice"
