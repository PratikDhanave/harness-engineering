"""Lesson 4 on the Agent Framework: memory is the context pipeline.

Short-term memory is an AgentSession; facts are a context provider that looks
things up and adds only what it found. Both run with no cloud.
"""
from __future__ import annotations

import pytest

from harness.af.remember import build_remembering_agent

FACTS = [
    ("refunds", "Refunds over 1000 pounds need a second approver."),
    ("hours", "Support is staffed 9 to 5 on weekdays."),
]


@pytest.mark.asyncio
async def test_the_conversation_is_carried_between_runs():
    agent, session, client, _ = build_remembering_agent(FACTS)
    await agent.run("I bought this last Tuesday", session=session)
    await agent.run("which order do you mean?", session=session)
    assert len(client.seen) == 2
    assert "last Tuesday" in client.seen[1], "the second call carries the first turn"


@pytest.mark.asyncio
async def test_a_new_session_remembers_nothing():
    agent, session, client, _ = build_remembering_agent(FACTS)
    await agent.run("I bought this last Tuesday", session=session)
    _, fresh, _, _ = build_remembering_agent(FACTS)
    await agent.run("which order?", session=fresh)
    assert "last Tuesday" not in client.seen[-1]


@pytest.mark.asyncio
async def test_only_the_relevant_facts_are_added_not_the_whole_corpus():
    agent, session, _, knowledge = build_remembering_agent(FACTS)
    await agent.run("tell me about a second approver", session=session)
    assert knowledge.last_hits == ["Refunds over 1000 pounds need a second approver."]


@pytest.mark.asyncio
async def test_nothing_is_added_when_nothing_matches():
    agent, session, _, knowledge = build_remembering_agent(FACTS)
    await agent.run("zebra", session=session)
    assert knowledge.last_hits == []


@pytest.mark.asyncio
async def test_the_leak_singular_does_not_find_the_plural():
    """Keyword overlap, no stemming: `refund` does not match "Refunds".

    This is the honest weakness of the local store — real retrieval uses
    embeddings, which is what AI Search brings. Pinned so the claim on the
    slide stays checkable.
    """
    agent, session, _, knowledge = build_remembering_agent(FACTS)
    await agent.run("refund", session=session)
    assert knowledge.last_hits == [], "no stemming, so the right doc is missed"


@pytest.mark.asyncio
async def test_the_leak_a_common_word_can_outrank_the_right_answer():
    agent, session, _, knowledge = build_remembering_agent(FACTS)
    await agent.run("what is the refund policy?", session=session)
    # "is" overlaps the hours doc; "refund" matches nothing. The wrong document
    # wins, confidently and with a score.
    assert knowledge.last_hits == ["Support is staffed 9 to 5 on weekdays."]
