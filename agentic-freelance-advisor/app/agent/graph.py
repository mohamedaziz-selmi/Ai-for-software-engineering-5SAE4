"""LangGraph wiring of the research agent.

    START -> plan -> agent --tool calls--> tools --> evaluate --gaps and budget left--> agent
                       |                                |
                       +--no tool calls (wants to stop)-+--sufficient evidence or a limit hit--> report -> END

plan      the model reads the request once (structured output)
agent     the model decides: call a tool, or stop
tools     executes the calls, enforces the safeguards and records every result as evidence
evaluate  judges source coverage from the real evidence (no LLM) and decides whether research continues
report    writes the technical guide from the evidence

Routing is a plain function of the state. A recorded `stop_reason` is what ends the research loop.
"""

from typing import Any

from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph

from app.agent.nodes import make_agent_node, make_evaluate_node, make_plan_node, make_report_node, make_tools_node
from app.agent.state import AgentDeps, AgentState, initial_state


def route_after_agent(state: AgentState) -> str:
    """Tool calls go to the tool node; anything else (a stop or a limit) goes to the evaluator."""
    last = state["messages"][-1] if state["messages"] else None
    wants_tools = isinstance(last, AIMessage) and bool(last.tool_calls) and not state.get("stop_reason")
    return "tools" if wants_tools else "evaluate"


def route_after_evaluate(state: AgentState) -> str:
    return "report" if state.get("stop_reason") else "agent"


def build_graph(deps: AgentDeps):
    graph = StateGraph(AgentState)
    graph.add_node("plan", make_plan_node(deps))
    graph.add_node("agent", make_agent_node(deps))
    graph.add_node("tools", make_tools_node(deps))
    graph.add_node("evaluate", make_evaluate_node(deps))
    graph.add_node("report", make_report_node(deps))

    graph.add_edge(START, "plan")
    graph.add_edge("plan", "agent")
    graph.add_conditional_edges("agent", route_after_agent, {"tools": "tools", "evaluate": "evaluate"})
    graph.add_edge("tools", "evaluate")
    graph.add_conditional_edges("evaluate", route_after_evaluate, {"agent": "agent", "report": "report"})
    graph.add_edge("report", END)
    return graph.compile()


def graph_config(deps: AgentDeps) -> dict[str, Any]:
    """Last-resort safety net behind the explicit iteration, tool-call and time limits."""
    settings = deps.settings
    return {"recursion_limit": settings.max_iterations * 3 + settings.max_gap_nudges * 2 + 12}


def run_research(request: str, deps: AgentDeps) -> AgentState:
    """Run the agent to completion and return the final state (which includes the report)."""
    return build_graph(deps).invoke(initial_state(request, deps), graph_config(deps))
