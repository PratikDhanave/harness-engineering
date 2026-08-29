"""Memory on the Agent Framework (Lesson 4).

`harness/memory/` builds three stores by hand. The framework has a place for
each of them, and it is the same place: the **context pipeline** that runs
before every model call.

    short-term   AgentSession + InMemoryHistoryProvider — the conversation,
                 carried between runs by passing the same session
    facts        a BaseContextProvider that looks things up and adds them to
                 the instructions for this call only — retrieval, i.e. RAG,
                 standing in for Azure AI Search
    scratch pad  still not built. The slide says so; so does this docstring.

The shape worth noticing: the fact provider does not paste the corpus into the
conversation. It searches, finds the few lines that matter, and adds only those
— which is the entire reason a knowledge store exists rather than a bigger
prompt.

State the leak: `InMemoryKnowledgeStore` scores by word overlap, so "car" does
not match "automobile" and a semantically perfect answer can score zero. Real
retrieval is embeddings, which is what AI Search brings. The seam is the same.
"""

from typing import Any

from agent_framework import (
    Agent,
    AgentSession,
    ContextProvider,
    InMemoryHistoryProvider,
    SessionContext,
)

from harness.af.guard import EchoChatClient
from harness.memory.knowledge import InMemoryKnowledgeStore


class KnowledgeProvider(ContextProvider):
    """Looks the question up and adds what it found — nothing more."""

    def __init__(self, store: InMemoryKnowledgeStore, *, top_k: int = 2) -> None:
        super().__init__(source_id="harness-knowledge")
        self._store = store
        self._top_k = top_k
        self.last_hits: list[str] = []

    async def before_run(
        self, *, agent: Any, session: AgentSession, context: SessionContext, state: dict[str, Any]
    ) -> None:
        question = " ".join(
            m.text for m in (context.input_messages or []) if getattr(m, "text", None)
        )
        hits = self._store.search(question, k=self._top_k)
        self.last_hits = [h.text for h in hits]
        if self.last_hits:
            context.extend_instructions(
                self.source_id,
                "Use only these facts:\n"
                + "\n".join(f"- {t}" for t in self.last_hits),
            )

    async def after_run(
        self, *, agent: Any, session: AgentSession, context: SessionContext, state: dict[str, Any]
    ) -> None:
        return None


def build_remembering_agent(
    facts: list[tuple[str, str]] | None = None,
) -> tuple[Agent, AgentSession, EchoChatClient, KnowledgeProvider]:
    """An agent with a conversation memory and a fact lookup, both cloud-free."""
    store = InMemoryKnowledgeStore()
    for doc_id, text in facts or []:
        store.add(doc_id, text)
    knowledge = KnowledgeProvider(store)
    client = EchoChatClient()
    agent = Agent(
        client,
        "Answer from the facts you are given.",
        context_providers=[InMemoryHistoryProvider(), knowledge],
    )
    return agent, AgentSession(), client, knowledge
