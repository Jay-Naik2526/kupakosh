"""One place to drop every in-process cache after the database changes (rebuild, upload job)."""
from __future__ import annotations


def reset_all():
    from app.copilot import agent
    from app.engines import analogs, context, hazard, lookahead
    from app.search import embeddings

    context.reset()
    from app.api import routes_geo
    routes_geo.reset_cache()
    analogs.reset()
    embeddings.index.cache_clear()
    hazard.base_rate.cache_clear()
    lookahead._profile.cache_clear()
    for f in (agent._index, agent._names, agent._basin_names, agent._dense_map):
        f.cache_clear()
