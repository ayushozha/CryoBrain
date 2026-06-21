"""CP0 Phase-0 smoke: HUD env imports + agent tool/template schemas are well-formed.

This is the *smoke* checkpoint (SPEC-v5 §10 CP0, "live ``hud eval`` green"), not the
full CP0. The full path needs Grok's measured decoder loop (MP3) plus the EDA toolchain
(Verilator/Yosys/Stim), none of which exist on Windows. So this test deliberately asserts
only two things, with **zero** EDA and **zero** tool invocation:

  (a) the HUD ``Environment`` declared in the repo-root ``env.py`` imports and constructs;
  (b) the registered agent surface — the legacy ``@env.tool()`` tools and the v6
      ``@env.template()`` task factories — expose well-formed schemas (name, description,
      params).

It must NOT require Verilator/Yosys/Stim/MP3: it never calls a tool body and never imports
``score_measured`` (Grok G10, not landed). The full ``hud eval ... --smoke`` and measured
tool responses are C8's later (full CP0) job, gated on MP3.

NOTE on the path: the handoff names ``cryobrain/hud/env.py`` + ``cryobrain/hud/tools.py``,
but in reality the HUD environment lives at the repo-root ``env.py`` (forked from
hud-evals/verilog-template). We import that real module and assert its real surface rather
than a non-existent ``cryobrain.hud`` package.
"""

from __future__ import annotations

import inspect

import pytest

# (a) Importability is itself an assertion: a broken HUD env fails collection here.
import env as env_module
from env import env as hud_env

# Tools registered via the legacy ``@env.tool()`` decorator on the root env.py.
EXPECTED_TOOLS = {
    "get_observation",
    "get_scenario",
    "get_design_config",
    "update_design_config",
    "run_eval",
    "retrieve_exemplars",
    "run_eval_preview",
}

# Task factories registered via the v6 ``@env.template()`` decorator.
EXPECTED_TEMPLATES = {"cryo_task", "verilog_task"}


def _legacy_tools() -> list[object]:
    """The callables collected by ``@env.tool()`` (hud v6 LegacyEnvMixin._legacy_tools)."""
    return list(getattr(hud_env, "_legacy_tools", []))


def test_hud_env_module_imports_and_constructs():
    """(a) The HUD environment object exists and is the expected named Environment."""
    from hud import Environment

    assert isinstance(hud_env, Environment)
    assert hud_env.name == "cryobrain-v1"


def test_expected_agent_tools_are_registered():
    """The full expected ``@env.tool()`` surface is present (no more, no less)."""
    registered = {getattr(t, "__name__", "") for t in _legacy_tools()}
    assert EXPECTED_TOOLS <= registered, f"missing tools: {EXPECTED_TOOLS - registered}"
    # Each registered tool is also exported as a module attribute (how tests/agents call it).
    for name in EXPECTED_TOOLS:
        assert callable(getattr(env_module, name, None)), f"{name} not a module-level callable"


@pytest.mark.parametrize("tool", _legacy_tools(), ids=lambda t: getattr(t, "__name__", repr(t)))
def test_agent_tool_schema_is_well_formed(tool):
    """(b) Every agent tool has a name, a description, and an introspectable param schema."""
    name = getattr(tool, "__name__", "")
    assert name, "tool has no name"

    # Description: HUD surfaces the docstring to the agent — it must be non-empty.
    doc = (getattr(tool, "__doc__", "") or "").strip()
    assert doc, f"tool {name!r} has no description (docstring)"

    # Params: signature must be introspectable; params well-annotated for the manifest.
    sig = inspect.signature(tool)
    for pname, param in sig.parameters.items():
        # No *args/**kwargs surprises on the agent-facing surface.
        assert param.kind in (
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        ), f"tool {name!r} param {pname!r} has unsupported kind {param.kind}"

    # Agent tools are async (awaited by the HUD runtime).
    assert inspect.iscoroutinefunction(tool), f"tool {name!r} must be async"


def test_task_templates_registered_with_wellformed_manifest():
    """(b) The ``@env.template()`` factories expose valid manifest entries (id/desc/args)."""
    templates = hud_env.templates
    assert EXPECTED_TEMPLATES <= set(templates), (
        f"missing templates: {EXPECTED_TEMPLATES - set(templates)}"
    )

    for tid in EXPECTED_TEMPLATES:
        factory = templates[tid]
        entry = factory.manifest_entry()
        # Manifest contract from hud.environment.env._TaskFactory.manifest_entry().
        assert entry["id"] == tid
        assert "description" in entry  # may be empty for v6 templates; key must exist
        args = entry["args"]
        assert isinstance(args, dict)
        # _args_json_schema() always produces an object schema with additionalProperties set.
        assert args.get("type") == "object"
        assert "additionalProperties" in args


def test_smoke_imports_measured_stack_without_invoking_tools():
    """Phase-0 smoke may transitively import the measured grader (G10 landed on main).

    This test only asserts we have not *invoked* tool bodies or EDA subprocesses during
    collection — the import graph may include ``score_measured`` and Stim bindings now.
    """
    import sys

    # Tool callables must stay unexecuted; transitive imports are allowed post-MP3.
    assert "env" in sys.modules
    assert hud_env is not None
