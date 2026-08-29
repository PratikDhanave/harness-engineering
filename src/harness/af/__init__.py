"""Microsoft Agent Framework implementations of the seven lesson seams.

Each module here satisfies the same seam as its local counterpart in
`harness/`, but built on Agent Framework primitives instead of hand-rolled
Python. The local versions stay: they are the teaching stand-in, they keep the
test suite and CI cloud-free, and having both sides of one seam is the point
of the seam pattern.

What is genuinely in-process (no Azure, no key, no network):

    durable.py   WorkflowBuilder + FileCheckpointStorage           (L2)
    gate.py      WorkflowContext.request_info + @response_handler  (L7)

Wired here but needing a chat client to do anything useful:

    guard.py     AgentMiddleware around the model call             (L1)
    route.py     HandoffBuilder                                    (L5)
    supervise.py ConcurrentBuilder / MagenticBuilder               (L6)
    remember.py  AgentSession + history providers                  (L4)

State the leak: Lesson 3 has no in-process equivalent. Code Interpreter is a
*hosted* tool — the isolation is somebody else's machine, which is the whole
point of it — so `harness/sandbox.py` keeps the local subprocess and the
managed sandbox stays a cloud swap. See sandbox.py's docstring.
"""


def run_sync(coro, async_name: str):
    """Run `coro` to completion, or explain why it cannot be run here.

    Each lesson offers a blocking wrapper so the examples read like ordinary
    Python. `asyncio.run()` refuses to nest, though, and the framework is async
    throughout — so anyone calling a wrapper from inside async code got
    "asyncio.run() cannot be called from a running event loop", which names
    neither the cause nor the cure. This says both.
    """
    import asyncio

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    coro.close()
    raise RuntimeError(
        f"you are already inside an event loop, so use `await {async_name}(...)` "
        f"instead of the blocking wrapper"
    )
