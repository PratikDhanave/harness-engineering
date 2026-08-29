from harness.memory.knowledge import Hit, InMemoryKnowledgeStore
from harness.memory.summarize import summarize_thread
from harness.memory.thread import Message, SQLiteThreadStore


# --- short-term thread memory -------------------------------------------------


def test_thread_append_and_history_ordering(tmp_path):
    store = SQLiteThreadStore(tmp_path / "threads.db")
    store.append("t1", "user", "hello")
    store.append("t1", "assistant", "hi there")
    store.append("t1", "user", "how are you?")

    assert store.history("t1") == [
        Message("user", "hello"),
        Message("assistant", "hi there"),
        Message("user", "how are you?"),
    ]


def test_thread_isolates_by_thread_id(tmp_path):
    store = SQLiteThreadStore(tmp_path / "threads.db")
    store.append("a", "user", "in a")
    store.append("b", "user", "in b")

    assert store.history("a") == [Message("user", "in a")]
    assert store.history("b") == [Message("user", "in b")]
    assert store.history("missing") == []


def test_thread_persists_across_new_store_instance(tmp_path):
    db = tmp_path / "threads.db"
    first = SQLiteThreadStore(db)
    first.append("t", "user", "remember me")
    first.append("t", "assistant", "done")
    first.close()

    # A brand-new store on the same file must see the earlier turns, in order.
    second = SQLiteThreadStore(db)
    assert second.history("t") == [
        Message("user", "remember me"),
        Message("assistant", "done"),
    ]


# --- long-term knowledge retrieval -------------------------------------------


def test_search_more_overlap_ranks_higher():
    store = InMemoryKnowledgeStore()
    store.add("d1", "the quick brown fox")
    store.add("d2", "quick brown dogs run")
    store.add("d3", "nothing relevant here")

    hits = store.search("quick brown fox")
    # d1 has all three query terms; d2 has two; d3 has none.
    assert [h.doc_id for h in hits] == ["d1", "d2"]
    assert hits[0].score > hits[1].score
    assert hits[0].score == 1.0


def test_search_respects_k_limit():
    store = InMemoryKnowledgeStore()
    for i in range(5):
        store.add(f"d{i}", "alpha term")

    hits = store.search("alpha", k=2)
    assert len(hits) == 2
    assert all(isinstance(h, Hit) for h in hits)
    # k truncates the SORTED list, not an arbitrary subset: all tie at 1.0, so the
    # ascending doc_id tie-break makes the top-2 deterministically d0, d1.
    assert [h.doc_id for h in hits] == ["d0", "d1"]


def test_search_ties_break_by_doc_id():
    store = InMemoryKnowledgeStore()
    store.add("zeta", "alpha")
    store.add("alpha_doc", "alpha")
    store.add("mid", "alpha")

    hits = store.search("alpha", k=3)
    # All score equally (1.0); deterministic tie-break is ascending doc_id.
    assert [h.doc_id for h in hits] == ["alpha_doc", "mid", "zeta"]


def test_search_empty_query_returns_empty():
    store = InMemoryKnowledgeStore()
    store.add("d1", "some content")
    assert store.search("") == []
    assert store.search("   ") == []


def test_search_no_match_returns_empty():
    store = InMemoryKnowledgeStore()
    store.add("d1", "the quick brown fox")
    assert store.search("elephant giraffe") == []


def test_add_upserts_by_doc_id():
    # Re-adding an existing doc_id replaces its text and term set (an index merge),
    # rather than creating a duplicate or keeping the stale terms.
    store = InMemoryKnowledgeStore()
    store.add("d1", "old cat")
    store.add("d1", "new dog")

    dog = store.search("dog")
    assert [h.doc_id for h in dog] == ["d1"]
    assert dog[0].text == "new dog"
    assert store.search("cat") == []  # old terms are gone, not duplicated


# --- summarization ------------------------------------------------------------


def test_summarize_returns_full_text_when_short():
    messages = [
        Message("user", "hi"),
        Message("assistant", "hello"),
    ]
    summary = summarize_thread(messages, max_chars=500)
    assert summary == "user: hi\nassistant: hello"


def test_summarize_rolls_up_when_long():
    messages = [Message("user", f"turn number {i} with some padding text") for i in range(20)]
    full = "\n".join(f"{m.role}: {m.content}" for m in messages)

    summary = summarize_thread(messages, max_chars=200)

    # Roll-up triggered: meaningfully shorter than the full history...
    assert len(summary) < len(full)
    # ...and it announces exactly what it dropped (20 turns, keep=2 => 16 omitted),
    # keeping the first and last turns.
    assert "[...16 earlier turns omitted...]" in summary
    assert "turn number 0" in summary
    assert "turn number 19" in summary


def test_summarize_clamps_nonpositive_keep():
    # keep<=0 is clamped to 1 (documented) — without the guard, lines[-0:] would
    # select the WHOLE list and emit a marker that hides nothing.
    messages = [Message("user", f"turn number {i} with some padding text") for i in range(20)]
    summary = summarize_thread(messages, max_chars=100, keep=0)
    assert "[...18 earlier turns omitted...]" in summary  # behaves as keep=1: 20 - 2
    assert "turn number 0" in summary
    assert "turn number 19" in summary


def test_summarize_no_droppable_middle_returns_full():
    # Two long turns exceed max_chars but there is nothing in the middle to omit,
    # so we return them verbatim rather than emit a hollow marker.
    messages = [
        Message("user", "x" * 400),
        Message("assistant", "y" * 400),
    ]
    summary = summarize_thread(messages, max_chars=100, keep=2)
    assert "omitted" not in summary
    assert summary == f"user: {'x' * 400}\nassistant: {'y' * 400}"
