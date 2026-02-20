from __future__ import annotations

from app.orchestration.multi_agent_scheduler import MultiAgentScheduler, PlannedFile


async def _noop_llm(_system: str, _user: str) -> str:
    return "{}"


async def _noop_emit(_event_type: str, _payload) -> None:
    return None


def _scheduler() -> MultiAgentScheduler:
    return MultiAgentScheduler(llm_call=_noop_llm, emit=_noop_emit)


def test_apply_ast_dependencies_adds_links_from_refs():
    sch = _scheduler()
    plan = [
        PlannedFile(path="src/a.py", description="A", deps=[]),
        PlannedFile(path="src/b.py", description="B", deps=[]),
    ]
    ast_ctx = (
        '<ast_index root="x">\n'
        '  <symbol path="src/a.py" lang="python" kind="function" line="1" scope="<module>">foo</symbol>\n'
        '  <ref path="src/b.py" lang="python" line="2" context="<module>">foo</ref>\n'
        "</ast_index>"
    )
    out, stats = sch._apply_ast_dependencies(plan=plan, ast_context=ast_ctx)
    dep_map = {p.path: set(p.deps) for p in out}
    assert "src/a.py" in dep_map["src/b.py"]
    assert stats["added_links"] == 1
    assert stats["touched_files"] == 1
    assert "src/b.py->src/a.py" in set(stats["added_edges"])
    assert sch._count_plan_edges(out) == 1


def test_apply_ast_dependencies_avoids_direct_cycle():
    sch = _scheduler()
    plan = [
        PlannedFile(path="src/a.py", description="A", deps=["src/b.py"]),
        PlannedFile(path="src/b.py", description="B", deps=[]),
    ]
    ast_ctx = (
        '<ast_index root="x">\n'
        '  <symbol path="src/a.py" lang="python" kind="function" line="1" scope="<module>">foo</symbol>\n'
        '  <ref path="src/b.py" lang="python" line="2" context="<module>">foo</ref>\n'
        "</ast_index>"
    )
    out, stats = sch._apply_ast_dependencies(plan=plan, ast_context=ast_ctx)
    dep_map = {p.path: set(p.deps) for p in out}
    assert "src/a.py" not in dep_map["src/b.py"]
    assert stats["added_links"] == 0
    assert sch._count_plan_edges(out) == 1
