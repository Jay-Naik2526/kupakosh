"""One place to drop every in-process cache after the database changes (rebuild, upload job)."""
from __future__ import annotations


def reset_all():
    from app.copilot import agent
    from app.engines import context, hazard, lookahead

    context.reset()
    hazard.base_rate.cache_clear()
    lookahead._profile.cache_clear()
    for f in (agent._index, agent._names, agent._basin_names):
        f.cache_clear()
