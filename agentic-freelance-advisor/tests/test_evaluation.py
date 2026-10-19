"""Tests of the source-coverage evaluation: judged from evidence, never from the LLM's claim."""

import pytest
from fakes import DEFAULT_PLAN

from app.agent.evaluation import (
    MAX_ATTEMPTS_PER_AREA,
    evaluate_coverage,
    next_suggested_call,
    render_coverage,
    suggested_query,
)
from app.schemas.research import ResearchPlan, Source, ToolExecution
from app.tools import DATASET_SEARCH, GITHUB_INSPECT, GITHUB_SEARCH, WEB_SEARCH


def src(n, kind, title="Title", summary="", detail="", **metadata):
    return Source(id=f"S{n}", kind=kind, title=title, url=f"https://example.com/{n}", summary=summary,
                  detail=detail, metadata=metadata, found_by=[1])


def execution(tool, status="ok", **arguments):
    return ToolExecution(step=1, tool=tool, arguments=arguments, status=status, started_at="t", duration_seconds=0)


def ledger(*sources):
    return {s.id: s for s in sources}


def areas(evaluation):
    return {item.area: item for item in evaluation.items}


def plan(**overrides):
    return DEFAULT_PLAN.model_copy(update=overrides)


def test_empty_ledger_reports_every_researchable_area_as_missing_with_a_concrete_next_step():
    evaluation = evaluate_coverage(DEFAULT_PLAN, {}, [], {})
    found = areas(evaluation)
    assert found["requirements"].status == "covered"
    for area in ("technologies", "datasets", "github_examples", "architecture", "environment_setup", "development_steps", "source_references"):
        assert found[area].status == "missing", area
    assert not evaluation.sufficient
    assert found["datasets"].tool == DATASET_SEARCH and found["datasets"].arguments == {"query": "fake news"}
    assert "search_huggingface_datasets with short keywords such as 'fake news'" in found["datasets"].action
    assert found["github_examples"].tool == GITHUB_SEARCH
    assert found["environment_setup"].tool == WEB_SEARCH and "fake news detector installation setup" in found["environment_setup"].action


def test_requirements_without_a_usable_plan_are_weak_and_never_block_research():
    evaluation = evaluate_coverage(plan(functional_requirements=[]), {}, [], {})
    item = areas(evaluation)["requirements"]
    assert item.status == "weak" and item.action == ""


def test_not_needed_areas_are_not_applicable():
    found = areas(evaluate_coverage(plan(needs_datasets=False, needs_github_examples=False), {}, [], {}))
    assert found["datasets"].status == "not_applicable" and found["github_examples"].status == "not_applicable"
    assert found["datasets"].action == ""


def test_datasets_two_or_one_with_known_license_are_covered_a_lone_unlicensed_one_is_weak():
    two = ledger(src(1, "dataset", license="not stated"), src(2, "dataset", license="unknown"))
    assert areas(evaluate_coverage(DEFAULT_PLAN, two, [], {}))["datasets"].status == "covered"
    licensed = ledger(src(1, "dataset", license="mit"))
    assert areas(evaluate_coverage(DEFAULT_PLAN, licensed, [], {}))["datasets"].status == "covered"
    lone = areas(evaluate_coverage(DEFAULT_PLAN, ledger(src(1, "dataset", license="not stated")), [execution(DATASET_SEARCH, query="x")], {}))["datasets"]
    assert lone.status == "weak" and "license is not stated" in lone.detail
    assert "different, shorter keywords" in lone.action


def test_a_search_that_keeps_finding_nothing_stops_being_requested():
    history = [execution(DATASET_SEARCH, query=f"q{i}") for i in range(MAX_ATTEMPTS_PER_AREA)]
    item = areas(evaluate_coverage(DEFAULT_PLAN, {}, history, {}))["datasets"]
    assert item.status == "weak" and item.action == "" and "after 3 searches" in item.detail
    retry = areas(evaluate_coverage(DEFAULT_PLAN, {}, history[:1], {}))["datasets"]
    assert retry.status == "weak" or retry.status == "missing"
    assert retry.action  # still worth another try after one attempt


def test_unavailable_tool_is_reported_as_unavailable_not_missing():
    found = areas(evaluate_coverage(DEFAULT_PLAN, {}, [], {WEB_SEARCH: "not_configured"}))
    for area in ("technologies", "architecture", "environment_setup", "development_steps"):
        assert found[area].status == "unavailable" and found[area].action == "", area
        assert "not_configured" in found[area].detail
    assert found["datasets"].status == "missing"  # that tool still works


def test_documentation_and_dependency_files_make_technologies_covered():
    docs = ledger(src(1, "web_page", "FastAPI docs", looks_like_documentation=True))
    assert areas(evaluate_coverage(DEFAULT_PLAN, docs, [], {}))["technologies"].status == "covered"
    deps = ledger(src(1, "repository_detail", dependency_file="requirements.txt"))
    assert areas(evaluate_coverage(DEFAULT_PLAN, deps, [], {}))["technologies"].status == "covered"
    blog = ledger(src(1, "web_page", "Some blog", looks_like_documentation=False))
    weak = areas(evaluate_coverage(DEFAULT_PLAN, blog, [], {}))["technologies"]
    assert weak.status == "weak" and "no official-looking documentation" in weak.detail


def test_architecture_setup_and_steps_are_judged_by_matching_retrieved_text_and_name_the_sources():
    web = ledger(
        src(1, "web_page", "System architecture overview", summary="components and layers"),
        src(2, "web_page", "Installation guide", summary="pip install and requirements"),
        src(3, "web_page", "Step-by-step tutorial", summary="how to train and deploy"),
    )
    found = areas(evaluate_coverage(DEFAULT_PLAN, web, [], {}))
    assert found["architecture"].status == "covered" and "S1" in found["architecture"].source_ids
    assert found["environment_setup"].status == "covered" and "S2" in found["environment_setup"].source_ids
    assert found["development_steps"].status == "covered" and "S3" in found["development_steps"].source_ids
    assert "Keyword match" in found["architecture"].detail  # says what the judgement is based on


def test_dataset_descriptions_do_not_count_as_setup_guidance():
    only_datasets = ledger(src(1, "dataset", summary="install guide tutorial architecture", license="mit"))
    found = areas(evaluate_coverage(DEFAULT_PLAN, only_datasets, [], {}))
    for area in ("architecture", "environment_setup", "development_steps"):
        assert found[area].status == "missing"


def test_source_reference_thresholds():
    assert areas(evaluate_coverage(DEFAULT_PLAN, {}, [], {}))["source_references"].status == "missing"
    two = ledger(src(1, "web_page"), src(2, "web_page"))
    assert areas(evaluate_coverage(DEFAULT_PLAN, two, [], {}))["source_references"].status == "weak"
    three = ledger(src(1, "web_page"), src(2, "web_page"), src(3, "web_page"))
    assert areas(evaluate_coverage(DEFAULT_PLAN, three, [], {}))["source_references"].status == "covered"


def test_complete_evidence_is_sufficient_and_has_no_gaps():
    full = ledger(
        src(1, "web_page", "Docs, installation guide and tutorial", summary="architecture overview", looks_like_documentation=True),
        src(2, "dataset", license="mit"),
        src(3, "repository", stars=10),
    )
    evaluation = evaluate_coverage(DEFAULT_PLAN, full, [], {})
    assert evaluation.sufficient and evaluation.gaps == []
    assert all(item.status in ("covered", "not_applicable") for item in evaluation.items)


def test_suggested_queries_come_from_the_plan():
    custom = ResearchPlan(objective="Build a Python sentiment analysis REST API", functional_requirements=["x"], technical_constraints=[],
                          assumptions=[], needs_datasets=True, needs_github_examples=True, key_topics=["sentiment analysis", "fastapi"])
    assert suggested_query("datasets", custom) == "sentiment analysis"
    assert suggested_query("github_examples", custom) == "python sentiment analysis rest"
    assert suggested_query("architecture", custom) == "python sentiment analysis rest architecture guide"
    assert suggested_query("datasets", None) == "project"


def test_render_coverage_is_compact_and_actionable():
    evaluation = evaluate_coverage(plan(needs_github_examples=False), ledger(src(1, "dataset", license="mit")), [], {WEB_SEARCH: "not_configured"})
    text = render_coverage(evaluation)
    assert "- datasets: covered" in text
    assert "- github_examples: not needed" in text
    assert "- architecture: cannot be researched (tool unavailable)" in text
    assert len(text) < 900


def test_next_suggested_call_prefers_core_assets_and_skips_tried_or_unusable_ones():
    evaluation = evaluate_coverage(DEFAULT_PLAN, {}, [], {})
    everything = {DATASET_SEARCH, GITHUB_SEARCH, WEB_SEARCH}
    assert next_suggested_call(evaluation, everything, []) == (DATASET_SEARCH, {"query": "fake news"})
    assert next_suggested_call(evaluation, {GITHUB_SEARCH, WEB_SEARCH}, [])[0] == GITHUB_SEARCH
    tried = [execution(DATASET_SEARCH, query="fake news")]
    assert next_suggested_call(evaluation, everything, tried)[0] == GITHUB_SEARCH  # same query would be a duplicate
    assert next_suggested_call(evaluation, set(), []) is None


# --------------------------------------------------------------------------- reading a repository instead of web search


def repo(n, name, stars):
    return Source(id=f"S{n}", kind="repository", title=name, url=f"https://github.com/{name}", summary="x",
                  metadata={"stars": stars}, found_by=[1])


def test_without_web_search_the_most_popular_repository_is_suggested_for_reading():
    sources = ledger(repo(1, "small/one", 5), repo(2, "big/popular", 900), repo(3, "mid/two", 40))
    found = areas(evaluate_coverage(DEFAULT_PLAN, sources, [execution(GITHUB_SEARCH, query="x")], {WEB_SEARCH: "not_configured"}))
    for area in ("technologies", "architecture", "environment_setup", "development_steps"):
        item = found[area]
        assert item.tool == GITHUB_INSPECT and item.arguments == {"owner": "big", "repo": "popular"}, area
        assert "owner='big' and repo='popular'" in item.action and "S2" in item.action
        assert item.status in ("missing", "weak")


def test_with_web_search_available_web_search_is_preferred_over_reading_a_repository():
    found = areas(evaluate_coverage(DEFAULT_PLAN, ledger(repo(1, "big/popular", 900)), [], {}))
    assert found["environment_setup"].tool == WEB_SEARCH


def test_an_inspected_repository_covers_setup_steps_architecture_and_technologies():
    inspected = Source(id="S1", kind="repository_detail", title="big/popular", url="https://github.com/big/popular", summary="x",
                       detail="README -> Headings: Architecture; Installation; Usage | requirements.txt -> torch, fastapi",
                       metadata={"dependency_file": "requirements.txt"}, found_by=[1, 2])
    evaluation = evaluate_coverage(DEFAULT_PLAN, ledger(inspected, src(2, "dataset", license="mit")), [], {WEB_SEARCH: "not_configured"})
    found = areas(evaluation)
    for area in ("technologies", "architecture", "environment_setup", "development_steps"):
        assert found[area].status == "covered" and found[area].source_ids == ["S1"], area
    assert evaluation.sufficient


def test_repository_reading_is_limited_and_needs_a_usable_tool():
    sources = ledger(repo(1, "big/popular", 900))
    used_up = [execution(GITHUB_INSPECT, owner=f"o{i}", repo="r") for i in range(2)]
    exhausted = areas(evaluate_coverage(DEFAULT_PLAN, sources, used_up, {WEB_SEARCH: "not_configured"}))
    assert exhausted["environment_setup"].action == "" and exhausted["environment_setup"].status in ("weak", "unavailable")
    no_tools = areas(evaluate_coverage(DEFAULT_PLAN, sources, [], {WEB_SEARCH: "not_configured", GITHUB_INSPECT: "rate_limited"}))
    assert no_tools["environment_setup"].status == "unavailable" and no_tools["environment_setup"].action == ""


def test_next_suggested_call_can_be_a_repository_inspection():
    evaluation = evaluate_coverage(plan(needs_datasets=False), ledger(repo(1, "big/popular", 900)), [execution(GITHUB_SEARCH, query="x")],
                                   {WEB_SEARCH: "not_configured"})
    assert next_suggested_call(evaluation, {GITHUB_INSPECT, GITHUB_SEARCH}, []) == (GITHUB_INSPECT, {"owner": "big", "repo": "popular"})
    done_already = [execution(GITHUB_INSPECT, owner="BIG", repo="Popular")]
    assert next_suggested_call(evaluation, {GITHUB_INSPECT}, done_already) is None


def test_the_weak_detail_says_which_repositories_were_read_when_web_search_is_unavailable():
    sources = ledger(repo(1, "big/popular", 900))
    used_up = [execution(GITHUB_INSPECT, owner=f"o{i}", repo="r") for i in range(2)]
    item = areas(evaluate_coverage(DEFAULT_PLAN, sources, used_up, {WEB_SEARCH: "not_configured"}))["environment_setup"]
    assert item.status == "weak"
    assert item.detail == "No match in the README of the 2 repository(ies) read; web search is unavailable (not_configured)."


def test_after_one_fruitless_web_search_the_agent_is_pointed_at_a_repository_not_at_more_blog_posts():
    sources = ledger(repo(1, "big/popular", 900), src(2, "web_page", "Generic text preprocessing blog"))
    found = areas(evaluate_coverage(DEFAULT_PLAN, sources, [execution(WEB_SEARCH, query="fake news documentation")], {}))
    assert found["technologies"].tool == GITHUB_INSPECT and found["technologies"].arguments == {"owner": "big", "repo": "popular"}
    first_time = areas(evaluate_coverage(DEFAULT_PLAN, ledger(repo(1, "big/popular", 900)), [], {}))
    assert first_time["technologies"].tool == WEB_SEARCH  # the first attempt is still a web search
    no_repo = areas(evaluate_coverage(DEFAULT_PLAN, ledger(src(2, "web_page", "blog")), [execution(WEB_SEARCH, query="x y")], {}))
    assert no_repo["technologies"].tool == WEB_SEARCH  # nothing to read: keep searching the web


def test_the_documentation_hint_asks_for_one_named_library_not_a_topic():
    action = areas(evaluate_coverage(DEFAULT_PLAN, {}, [], {}))["technologies"].action
    assert "ONE library" in action and "naming it" in action and "scikit-learn" in action and "FastAPI" in action


def test_queries_are_built_from_the_project_not_from_the_plans_first_sub_topic():
    """A live run copied the hint 'text preprocessing architecture guide' (the plan's first key topic) into its
    searches and got generic preprocessing blog posts instead of material about fake news detection."""
    request = "Build a fake news detection system using Python and machine learning ."
    drifting = plan(objective="A machine learning system in Python that classifies text as real or fake news",
                    key_topics=["Text preprocessing", "Model selection", "Dataset curation"])
    assert suggested_query("architecture", drifting, request) == "fake news detection python architecture guide"
    assert suggested_query("environment_setup", drifting, request) == "fake news detection python installation setup"
    assert suggested_query("github_examples", drifting, request) == "fake news detection python"
    assert suggested_query("datasets", drifting, request) == "fake news"  # language and kind of software are not the subject
    assert "preprocessing" not in " ".join(suggested_query(a, drifting, request) for a in ("datasets", "architecture", "technologies"))
    sentiment = "Research how to build a Python sentiment analysis REST API. Find datasets and GitHub examples."
    assert suggested_query("datasets", drifting, sentiment) == "sentiment analysis"
    assert suggested_query("architecture", drifting, "How do I enable CORS in FastAPI?") == "enable cors fastapi architecture guide"


def test_the_evaluation_uses_the_request_for_its_hints():
    request = "Build a fake news detection system using Python and machine learning ."
    topics = plan(objective="A system", key_topics=["Text preprocessing"])
    found = areas(evaluate_coverage(topics, {}, [], {}, request))
    assert found["architecture"].arguments == {"query": "fake news detection python architecture guide"}
    assert found["datasets"].arguments == {"query": "fake news"}


@pytest.mark.parametrize("text", ["Run npm install", "yarn add react", "flutter pub get", "composer install", "gradle build", "docker compose up"])
def test_setup_instructions_of_other_ecosystems_are_recognised(text):
    web = ledger(src(1, "web_page", "Getting going", summary=text))
    assert areas(evaluate_coverage(DEFAULT_PLAN, web, [], {}))["environment_setup"].status == "covered"
