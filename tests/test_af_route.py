"""Lesson 5 on the Agent Framework: the graph itself picks the specialist."""
from __future__ import annotations

import pytest

from harness.af.route import BILLING, CODE, FALLBACK, RESEARCH, route


@pytest.mark.parametrize(
    "request_text, expected",
    [
        ("refund my invoice", BILLING),
        ("this will not compile", CODE),
        ("compare these three suppliers", RESEARCH),
        ("my cat is unwell", FALLBACK),
    ],
)
def test_routes_to_the_right_specialist(request_text, expected):
    assert route(request_text).specialist == expected


def test_the_matched_word_is_reported():
    assert route("refund my invoice").matched == "refund"


def test_unmatched_requests_fall_back_rather_than_failing():
    out = route("something entirely unrelated")
    assert out.specialist == FALLBACK
    assert out.matched is None


def test_a_paraphrase_is_missed_and_that_is_the_leak():
    """A keyword table has no idea what a word means.

    Any human reads this as a code problem. The table knows 'compile' and does
    not know "won't build", so it falls through. Pinned as a test because the
    talk claims it — and a claim nobody checks stops being true quietly.
    """
    assert route("the project won't build any more").specialist == FALLBACK


def test_rules_are_injectable_so_the_miss_is_one_line_to_fix():
    rules = {"won't build": CODE}
    assert route("the project won't build any more", rules).specialist == CODE
