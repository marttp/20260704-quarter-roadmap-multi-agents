"""Structural tests for the ADK 2.0 graph (app.agent).

Asserts on the graph topology + agent configuration — never invokes the LLM.
(LLM behavior is validated via `agents-cli eval`, not pytest, per scaffold guidance.)
"""

from app import agent as agent_module
from app.models import AgentPositionsOutput


def test_app_is_constructed_with_expected_name():
    assert agent_module.app.name == "quarter_roadmap_copilot"
    assert agent_module.app.root_agent is agent_module.root_agent


def test_workflow_has_the_expected_five_edges():
    # Linear chain: START -> load -> planning_agent -> build_stakeholder_input ->
    #               stakeholder_agent -> summarize
    assert len(agent_module.root_agent.edges) == 5


def test_both_llm_agents_use_the_same_flash_model():
    assert agent_module.planning_agent.model == agent_module.stakeholder_agent.model
    assert "flash" in str(agent_module.planning_agent.model).lower()


def test_both_llm_agents_emit_structured_positions():
    # The output_schema guarantees the dashboard receives predictable JSON,
    # not free-form text.
    assert agent_module.planning_agent.output_schema is AgentPositionsOutput
    assert agent_module.stakeholder_agent.output_schema is AgentPositionsOutput


def test_positions_are_stored_to_distinct_state_keys():
    # summarize_node reads ctx.state['planning_positions'] and ['stakeholder_positions'].
    # The agents' output_keys must match exactly.
    assert agent_module.planning_agent.output_key == "planning_positions"
    assert agent_module.stakeholder_agent.output_key == "stakeholder_positions"


def test_function_nodes_are_decorated():
    # @node wraps a callable into a BaseNode the Workflow can schedule.
    from google.adk.workflow import BaseNode

    for fn in (
        agent_module.load_planning_state_node,
        agent_module.build_stakeholder_input_node,
        agent_module.summarize_node,
    ):
        assert isinstance(fn, BaseNode), fn
