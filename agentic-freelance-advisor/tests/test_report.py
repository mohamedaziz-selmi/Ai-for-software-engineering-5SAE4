"""Tests of the report: its structure, and that every URL and claim in it is grounded in retrieved evidence."""

import re

import httpx
import pytest
from fakes import (
    DEFAULT_PLAN,
    META,
    REQUEST,
    ScriptedLLM,
    call,
    done,
    make_tools,
)
from langchain_core.messages import AIMessage

from app.agent.context import estimate_tokens
from app.agent.graph import run_research
from app.agent.prompts import BREVITY, SHORT_REASONING_HINT
from app.agent.report import (
    COMMANDS_NOTE,
    LOOPBACK_HOSTS,
    ORIGIN_NOTES,
    REMOVED_LINK,
    TITLES,
    assess,
    build_report_messages,
    build_response,
    check_claims,
    clean_generated,
    section_c,
)
from app.agent.state import AgentDeps
from app.schemas.research import EvidenceItem, ResearchResponse, Source, ToolResult
from app.tools import DATASET_SEARCH, GITHUB_SEARCH, WEB_SEARCH

URL = re.compile(r"https?://[^\s)\]>\"'`]+")


@pytest.fixture
def run(make_settings):
    """Run the full graph with scripted model replies and return (state, deps, llm)."""

    def go(replies=None, *, texts=None, plans=None, tools=None, unavailable=None, **settings):
        llm = ScriptedLLM(replies if replies is not None else [call((DATASET_SEARCH, {"query": "fake news"}), (GITHUB_SEARCH, {"query": "fake news detection"})), done()],
                          plans, texts)
        settings.setdefault("max_gap_nudges", 0)
        deps = AgentDeps(settings=make_settings(**settings), llm_factory=lambda n: llm, tools=tools or make_tools(),
                         unavailable_at_start=unavailable or {})
        return run_research(REQUEST, deps), deps, llm

    return go


def source(n, kind, title="Title", url=None, **metadata):
    return Source(id=f"S{n}", kind=kind, title=title, url=url or f"https://example.com/{n}", metadata=metadata, found_by=[1])


def urls_in(text):
    return {match.group(0).rstrip(".,;:") for match in URL.finditer(text)}


# --------------------------------------------------------------------------- structure


def test_report_has_all_seven_sections_in_order_with_the_right_origin(run):
    state, *_ = run()
    report = state["report"]
    assert [s.id for s in report.sections] == list("ABCDEFG")
    assert [s.title for s in report.sections] == [TITLES[i] for i in "ABCDEFG"]
    origins = {s.id: s.origin for s in report.sections}
    assert origins == {"A": "derived_from_request", "B": "model_recommendation", "C": "tool_evidence",
                       "D": "model_recommendation", "E": "model_recommendation", "F": "model_recommendation", "G": "tool_evidence"}
    for section in report.sections:
        assert section.content.strip()
        assert f"## {section.id}. {section.title}" in report.markdown
    assert report.title.startswith("Technical implementation guide: Build a fake news detector")
    assert "Nothing was downloaded, cloned, installed or executed" in report.markdown


def test_every_section_says_where_its_content_comes_from(run):
    state, *_ = run()
    markdown = state["report"].markdown
    for note in ORIGIN_NOTES.values():
        assert note in markdown


def test_commands_are_never_presented_as_tested(run):
    state, *_ = run(texts=["Stack text", "Architecture text", "pip install fastapi", "1. Do it"])
    sections = {s.id: s.content for s in state["report"].sections}
    assert sections["E"].endswith(COMMANDS_NOTE) and sections["F"].endswith(COMMANDS_NOTE)
    assert COMMANDS_NOTE not in sections["B"] and COMMANDS_NOTE not in sections["D"]
    assert "No command in this report was executed" in sections["G"]


def test_model_sections_are_written_by_four_separate_bounded_calls(run):
    state, _, llm = run(texts=["B text", "D text", "E text", "F text"])
    assert len(llm.report_prompts) == 4
    briefs = [prompt[1].content for prompt in llm.report_prompts]
    for letter, prompt in zip("BDEF", briefs):
        assert f"Write section {letter}," in prompt
        assert "SOURCES (retrieved by tools)" in prompt
    assert [c["node"] for c in state["llm_calls"] if c["node"].startswith("report")] == ["report B", "report D", "report E", "report F"]


def test_report_prompt_fits_the_context_window(make_settings):
    deps = AgentDeps(settings=make_settings(), llm_factory=lambda n: None, tools={})
    ledger = {f"S{i}": source(i, "repository", title="t" * 60, stars=5, language="Python", possibly_stale=True,
                              last_push="2020-01-01", license="mit") for i in range(1, 30)}
    for item in ledger.values():
        item.summary = "very long description " * 40
    plan = DEFAULT_PLAN.model_copy(update={"functional_requirements": ["r" * 160] * 5, "technical_constraints": ["c" * 160] * 3})
    for letter in "BDEF":
        messages = build_report_messages(letter, plan, ledger, deps)
        allowed = deps.settings.ollama_num_ctx - deps.settings.report_max_tokens
        assert estimate_tokens(messages[0].content + messages[1].content) <= allowed


# --------------------------------------------------------------------------- grounding


def test_urls_and_citations_in_model_text_must_come_from_the_ledger(run):
    real = "https://example.com/search_huggingface_datasets/fake-news/1"
    text = (f"Use FastAPI [S1] as in https://made-up.example/docs and [S99]. Try curl http://localhost:8000/predict. "
            f"The dataset page {real} [S1, S42] is useful.")
    state, *_ = run(texts=[text, "D", "E", "F"])
    section = next(s for s in state["report"].sections if s.id == "B").content

    assert "made-up.example" not in section and REMOVED_LINK in section
    assert real in section and "http://localhost:8000/predict" in section
    assert "[S99]" not in section and "S42" not in section and "[S1]" in section and "[S1]" in section
    validation = state["report"].validation
    assert validation.removed_urls == ["https://made-up.example/docs"]
    assert sorted(validation.removed_citations) == ["S42", "S99"]
    assert any("1 link(s) written by the model were removed" in item for item in state["report"].limitations)
    assert any("2 citation(s)" in item for item in state["report"].limitations)


def test_every_url_in_the_final_report_is_a_retrieved_source_or_loopback(run):
    attack = "See https://evil.example/a and https://phish.example/b?x=1 and http://localhost:3000/x."
    state, *_ = run(texts=[attack] * 4)
    report = state["report"]
    allowed = {s.url for s in state["sources"].values()}
    found = urls_in(report.markdown)
    assert found, "the report should contain links"
    for url in found:
        host = re.sub(r"^https?://([^/:]+).*$", r"\1", url)
        assert url in allowed or host in LOOPBACK_HOSTS, f"ungrounded URL in report: {url}"
    assert len(report.validation.removed_urls) == 8


def test_clean_generated_rules():
    ledger = {"S1": source(1, "web_page", url="https://example.com/docs/"), "S2": source(2, "web_page")}
    text, urls, citations = clean_generated(
        "## Recommended Technology Stack\nUse X [S1][S3] or Y [S2, S9] (general knowledge). See https://example.com/docs, and https://bad.example.", ledger)
    assert text.startswith("Use X [S1] or Y [S2] (general knowledge).")  # the title the model added is dropped
    assert "https://example.com/docs," in text  # a source URL followed by punctuation survives
    assert urls == ["https://bad.example"] and citations == ["S3", "S9"]
    kept, urls, citations = clean_generated("### Languages\n- Python [S1]", ledger)
    assert kept.startswith("### Languages") and not urls and not citations  # a real sub-heading is not removed


def test_citations_only_to_sources_that_exist_survive_a_run_without_any_sources(run):
    empty = lambda name: (lambda **kw: ToolResult(tool=name, arguments=kw, ok=True))  # noqa: E731
    tools = make_tools(**{n: empty(n) for n in (DATASET_SEARCH, GITHUB_SEARCH)})
    state, _, llm = run(tools=tools, texts=["Use Python [S1] (general knowledge)", "D", "E", "F"])
    assert "[S1]" not in next(s for s in state["report"].sections if s.id == "B").content
    assert "No external sources could be retrieved" in llm.report_prompts[0][1].content
    sections = {s.id: s.content for s in state["report"].sections}
    assert "No sources were retrieved." in sections["G"] and "Nothing relevant was retrieved." in sections["C"]


# --------------------------------------------------------------------------- evidence-built sections


def test_section_c_reports_only_what_the_tools_returned():
    stale = source(1, "repository", "owner/old", stars=7, license="not stated", possibly_stale=True, last_push="2019-01-01", language="Python")
    good = source(2, "repository", "owner/new", stars=1500, license="MIT", possibly_stale=False, last_push="2026-09-01")
    dataset = source(3, "dataset", "org/news", downloads=250, license="unknown", tasks=["text-classification"],
                     last_modified="2020-01-01", gated=True, size_category="10K<n<100K")
    docs = source(4, "web_page", "Official docs", domain="docs.example.com", looks_like_documentation=True)
    blog = source(5, "web_page", "A blog", domain="blog.example.com", looks_like_documentation=False)
    text = section_c(DEFAULT_PLAN, {s.id: s for s in (stale, good, dataset, docs, blog)}, {})

    assert "[owner/old](https://example.com/1) [S1]" in text
    assert "7 stars (small community)" in text and "no license stated: reuse rights are unclear" in text
    assert "possibly stale: last push 2019-01-01" in text
    assert "1,500 stars" in text and "license: MIT" in text and "recently active: last push 2026-09-01" in text
    assert "license unknown: check the dataset card before commercial use" in text
    assert "250 downloads (little community usage)" in text and "last updated 2020-01-01" in text
    assert "gated: access terms must be accepted first" in text and "task tags: text-classification" in text
    assert "the URL pattern suggests documentation or a guide (not verified as official)" in text
    assert "general web page, not necessarily official documentation" in text
    assert "no language tag, so its language must be checked by hand" in text


def test_section_c_explains_why_a_group_is_empty():
    plan = DEFAULT_PLAN.model_copy(update={"needs_datasets": False})
    text = section_c(plan, {}, {GITHUB_SEARCH: "rate_limited", WEB_SEARCH: "not_configured"})
    assert "### Datasets\nNot needed for this project." in text
    assert "Not researched: search_github_repositories was unavailable (rate_limited)." in text
    assert "Not researched: search_web was unavailable (not_configured)." in text
    assert "Nothing relevant was retrieved." in section_c(DEFAULT_PLAN, {}, {})


def test_assess_never_invents_missing_metadata():
    good, bad = assess(source(1, "dataset"))  # a dataset with no metadata at all
    assert good == [] and any("license" in item for item in bad) and not any("downloads" in item for item in bad)
    good, bad = assess(source(2, "repository", stars=None))
    assert not any("stars" in item for item in good + bad)


# --------------------------------------------------------------------------- honest limitations


def test_missing_web_search_key_is_stated_in_the_report(run):
    state, *_ = run(unavailable={WEB_SEARCH: "not_configured"})
    report = state["report"]
    assert any("TAVILY_API_KEY" in item for item in report.limitations)
    assert "TAVILY_API_KEY" in next(s for s in report.sections if s.id == "G").content
    assert "Not researched: search_web was unavailable (not_configured)." in next(s for s in report.sections if s.id == "C").content


def test_tool_failures_and_stop_reasons_are_listed(run):
    boom = lambda **kw: ToolResult(tool=GITHUB_SEARCH, arguments=kw, ok=False,  # noqa: E731
                                   error={"code": "timeout", "message": "GitHub did not answer in time."})
    state, *_ = run(replies=[call((GITHUB_SEARCH, {"query": "fake news"}))], tools=make_tools(**{GITHUB_SEARCH: boom}), max_iterations=1)
    limitations = state["report"].limitations
    assert any("Step 1 (search_github_repositories) failed: GitHub did not answer in time." in item for item in limitations)
    assert any("iteration limit (1 turns)" in item for item in limitations)


def test_removed_prompt_injection_is_reported(run):
    flagged = lambda **kw: ToolResult(tool=WEB_SEARCH, arguments=kw, ok=True, items=[  # noqa: E731
        EvidenceItem(kind="web_page", title="Page", url="https://example.com/p", summary="Install it.", flags=["possible_prompt_injection"])])
    state, *_ = run(replies=[call((WEB_SEARCH, {"query": "docs here"})), done()], tools=make_tools(**{WEB_SEARCH: flagged}))
    assert any("Instruction-like text was found and removed in 1 retrieved source(s) (S1)" in item for item in state["report"].limitations)


def test_unmet_coverage_is_listed_as_not_verified(run):
    state, *_ = run(unavailable={WEB_SEARCH: "not_configured"})
    limitations = " ".join(state["report"].limitations)
    assert "Not fully covered - Environment setup" in limitations


# --------------------------------------------------------------------------- model trouble


def test_a_failed_model_section_is_reported_not_hidden(run):
    state, *_ = run(texts=[httpx.ConnectError("down"), "D text", "E text", "F text"])
    report = state["report"]
    assert report.validation.sections_not_generated == ["B"]
    assert "could not be generated" in next(s for s in report.sections if s.id == "B").content
    assert any("Section B (Recommended Technology Stack) could not be generated" in item for item in report.limitations)
    assert next(s for s in report.sections if s.id == "D").content.startswith("D text")


def test_empty_model_output_is_retried_once_with_a_shorter_hint(run):
    cut = AIMessage(content="", response_metadata={**META, "done_reason": "length"})
    state, _, llm = run(texts=[cut, "B after retry", "D", "E", "F"])
    assert next(s for s in state["report"].sections if s.id == "B").content.startswith("B after retry")
    assert llm.report_prompts[0][1].content.endswith(BREVITY) and SHORT_REASONING_HINT not in llm.report_prompts[0][1].content
    assert SHORT_REASONING_HINT in llm.report_prompts[1][1].content
    assert "report B (retry)" in [c["node"] for c in state["llm_calls"]]


def test_two_empty_outputs_leave_a_clear_notice(run):
    cut = lambda: AIMessage(content="", response_metadata={**META, "done_reason": "length"})  # noqa: E731
    state, *_ = run(texts=[cut(), cut(), "D", "E", "F"])
    assert state["report"].validation.sections_not_generated == ["B"]
    assert "ran out of tokens while thinking" in state["report"].limitations[-1] or any(
        "ran out of tokens" in item for item in state["report"].limitations)


def test_a_cut_off_but_non_empty_section_is_marked(run):
    partial = AIMessage(content="Python and FastAPI", response_metadata={**META, "done_reason": "length"})
    state, *_ = run(texts=[partial, "D", "E", "F"])
    assert "cut off because the model reached its length limit" in next(s for s in state["report"].sections if s.id == "B").content


def test_model_thinking_never_reaches_the_report(run):
    leaky = "<think>I should invent a URL https://secret.example</think>Use FastAPI."
    state, *_ = run(texts=[leaky, "D", "E", "F"])
    markdown = state["report"].markdown
    assert "<think>" not in markdown and "secret.example" not in markdown and "Use FastAPI." in markdown


# --------------------------------------------------------------------------- API payload


def test_response_is_complete_and_serialisable(run):
    state, deps, _ = run()
    response = build_response(state, deps)
    assert isinstance(response, ResearchResponse)
    again = ResearchResponse.model_validate_json(response.model_dump_json())
    assert again.project_description == REQUEST
    assert again.stop_reason == state["stop_reason"]
    assert [s.id for s in again.sources] == list(state["sources"])
    assert [e.tool for e in again.tool_history] == [DATASET_SEARCH, GITHUB_SEARCH]
    assert again.tool_history[0].decided_by == "llm"
    assert again.evaluation is not None and again.plan is not None
    assert again.stats.model == deps.settings.ollama_model and again.stats.tool_calls_executed == 2
    nodes = [c["node"] for c in again.stats.llm_calls]
    assert nodes[0] == "plan" and "agent" in nodes and nodes[-1] == "report F"
    assert again.report.markdown == state["report"].markdown


# --------------------------------------------------------------------------- tidying model output


def test_stray_title_lines_and_leaked_rule_notes_are_removed():
    ledger = {"S1": source(1, "web_page")}
    text, _, _ = clean_generated("Section E: Environment Configuration\nPrerequisites: Python 3.9+ [S1]", ledger)
    assert text == "Prerequisites: Python 3.9+ [S1]"
    text, _, _ = clean_generated("Recommended Architecture:  \n- REST endpoint\n\n*Note: Avoided URLs and installation claims per rules.*", ledger)
    assert text == "- REST endpoint"
    text, _, _ = clean_generated("**Environment Configuration**\npip install flask", ledger)
    assert text == "pip install flask"
    kept, _, _ = clean_generated("Recommended: use Python 3.12\nand a virtual environment", ledger)
    assert kept.startswith("Recommended: use Python 3.12")  # a real first line is not mistaken for a title
    kept, _, _ = clean_generated("Prerequisites are Python and pip.\nNote: pip may need an upgrade.", ledger)
    assert "Note: pip may need an upgrade." in kept  # only notes that talk about the rules are removed


# --------------------------------------------------------------------------- claims must match the cited source


def evidence():
    return {
        "S1": source(1, "dataset", "jcblaise/fake_news_filipino", license="unknown", downloads=924),
        "S2": source(2, "dataset", "mariagrandury/fake_news_corpus_spanish", license="cc-by-4.0", downloads=574),
        "S3": source(3, "repository", "owner/detector", license="MIT", stars=1500),
        "S4": source(4, "dataset", "multi/license-set", license="cc-by-sa-4.0, cc-by-4.0, cc0-1.0", downloads=1158),
        "S5": source(5, "dataset", "sayalaruano/FakeNewsCorpusSpanish", license="not stated", downloads=807),
    }


def test_correct_statements_are_left_alone():
    text = ("Use the Spanish corpus [S2] (CC-BY-4.0, 574 downloads). "
            "The repository owner/detector [S3] has 1,500 stars and an MIT license.")
    marked, problems = check_claims(text, evidence())
    assert marked == text and problems == []


def test_a_license_that_is_not_the_cited_sources_license_is_marked():
    marked, problems = check_claims("Choose the Filipino set [S1] because it is MIT licensed.", evidence())
    assert marked.endswith("[CHECK: license 'MIT' is not the license of S1]") and len(problems) == 1


def test_an_unknown_or_unstated_license_cannot_be_claimed_as_a_specific_one():
    assert check_claims("It is released under CC-BY-4.0 [S1].", evidence())[1]  # S1: unknown
    assert check_claims("The corpus [S5] uses the Apache-2.0 license.", evidence())[1]  # S5: not stated


@pytest.mark.parametrize("claim", ["Apache-2.0", "Apache License 2.0", "Apache 2.0", "apache-2.0"])
def test_license_spelling_variants_are_accepted(claim):
    ledger = {"S1": source(1, "repository", "owner/long-name", license="Apache-2.0")}
    assert check_claims(f"It is under the {claim} license [S1].", ledger)[1] == []


def test_a_source_with_several_licenses_accepts_any_of_them():
    for claim in ("CC-BY-SA-4.0", "CC-BY-4.0", "CC0-1.0"):
        assert check_claims(f"Reusable under {claim} [S4].", evidence())[1] == []


def test_download_and_star_counts_must_equal_the_retrieved_counts():
    assert check_claims("It has 574 downloads [S2] and 1500 stars [S3].", evidence())[1] == []
    assert check_claims("It has 1,350 downloads [S2].", evidence())[1] == ["1,350 downloads does not match S2"]
    assert check_claims("About 1,501 stars [S3].", evidence())[1] == ["1,501 stars does not match S3"]


def test_naming_one_source_but_citing_another_is_marked():
    """The real mix-up from a live run: a dataset's name written next to another dataset's id."""
    marked, problems = check_claims("Use `sayalaruano/FakeNewsCorpusSpanish` [S2] for Spanish text.", evidence())
    assert problems == ["names sayalaruano/FakeNewsCorpusSpanish (S5) but cites S2"]
    assert "[CHECK: names sayalaruano/FakeNewsCorpusSpanish (S5) but cites S2]" in marked
    assert check_claims("Use `sayalaruano/FakeNewsCorpusSpanish` [S5].", evidence())[1] == []


def test_sentences_without_known_citations_are_not_checked():
    ledger = evidence()
    for text in ("Many projects use MIT licensed code with 5000 stars.", "It is MIT licensed [S99]."):
        assert check_claims(text, ledger) == (text, [])


def test_only_the_offending_line_is_marked_and_the_layout_is_kept():
    text = "Intro line [S2].\nIt is MIT licensed [S2].\n- bullet [S3]"
    marked, problems = check_claims(text, evidence())
    lines = marked.split("\n")
    assert lines[0] == "Intro line [S2]." and lines[2] == "- bullet [S3]"
    assert lines[1].startswith("It is MIT licensed [S2]. [CHECK:") and len(problems) == 1


def test_the_report_marks_and_reports_a_contradicted_claim(run):
    wrong = "The dataset [S1] is popular with 99999 downloads and an MIT license."
    state, *_ = run(texts=[wrong, "D", "E", "F"])
    report = state["report"]
    section = next(s for s in report.sections if s.id == "B").content
    assert "[CHECK: 99999 downloads does not match S1]" in section
    assert report.validation.unverified_claims == ["99999 downloads does not match S1"]
    assert any("1 statement(s) in model-written sections do not match the source they cite" in item for item in report.limitations)


# --------------------------------------------------------------------------- citations in parentheses, dataset language


def test_citations_in_parentheses_are_checked_and_unknown_ones_removed():
    ledger = {"S1": source(1, "web_page", url="https://example.com/a"), "S2": source(2, "web_page")}
    text, _, citations = clean_generated("Use X (S1) and Y (S9) or Z [S2, S7].", ledger)
    assert text == "Use X (S1) and Y or Z [S2]." and sorted(citations) == ["S7", "S9"]


def test_removing_an_unknown_citation_leaves_no_stray_space_before_punctuation():
    ledger = {"S1": source(1, "web_page", url="https://example.com/a")}
    text, _, citations = clean_generated("A single codebase [S9]. Fast builds [S1, S8]; hot reload (S4), ok.\nLast line [S5]", ledger)
    assert text == "A single codebase. Fast builds [S1]; hot reload, ok.\nLast line"
    assert sorted(citations) == ["S4", "S5", "S8", "S9"]


def test_claims_are_checked_even_when_the_model_cites_as_S7_shows_or_S8_colon():
    marked, problems = check_claims("It is MIT licensed (S2: fine) and S2 has 999 downloads.", evidence())
    assert problems == ["license 'MIT' is not the license of S2", "999 downloads does not match S2"]
    assert "[CHECK:" in marked
    assert check_claims("Choose it (S2 shows CC-BY-4.0 and 574 downloads).", evidence())[1] == []


def test_section_c_states_the_language_of_each_dataset():
    english = source(1, "dataset", "org/en", downloads=5000, license="mit", tasks=["text-classification"], languages=["en"])
    spanish = source(2, "dataset", "org/es", downloads=5000, license="mit", tasks=["text-classification"], languages=["es"])
    text = section_c(DEFAULT_PLAN, {s.id: s for s in (english, spanish)}, {})
    assert "languages: en" in text
    assert "not an English dataset (language tag: es)" in text


# --------------------------------------------------------------------------- tidy titles and wording


@pytest.mark.parametrize(
    "first_line",
    ["**D. Recommended Architecture**", "D. Recommended Architecture", "Section E: Environment Configuration",
     "## F. Step-by-Step Implementation Roadmap", "B) Recommended Technology Stack:"],
)
def test_a_title_with_a_section_letter_is_removed(first_line):
    text, _, _ = clean_generated(first_line + "\nThe real content [S1].", {"S1": source(1, "web_page")})
    assert text == "The real content [S1]."


def test_real_first_lines_and_code_fences_are_never_mistaken_for_titles():
    ledger = {"S1": source(1, "web_page")}
    for line in ("A recommended architecture is a pipeline.", "```bash", "```", "Prerequisites: Python 3.12", "B-trees are not needed."):
        assert clean_generated(line + "\nmore", ledger)[0].startswith(line)


def test_the_title_is_cut_at_a_word_boundary():
    from app.agent.report import short_title

    long = "A Python-based machine learning system that classifies news articles as real or fake using text input."
    cut = short_title(long)
    assert cut.endswith("...") and len(cut) <= 93 and not cut[:-3].endswith(("usin", "us"))
    assert cut == "A Python-based machine learning system that classifies news articles as real or fake..."
    assert short_title("Short objective.") == "Short objective"


def test_the_briefs_for_the_stack_and_the_environment_ask_for_honest_citations_and_a_supported_python():
    from app.agent.prompts import SECTION_BRIEFS

    assert "not licenses, not hosting sites" in SECTION_BRIEFS["B"]
    assert "never cite a dataset or a repository for a general claim" in SECTION_BRIEFS["B"]
    assert "for Python that means 3.10 or newer" in SECTION_BRIEFS["E"]
    # not only for Python: another ecosystem must get its own package manager and runtime
    assert "package manager of the project's ecosystem" in SECTION_BRIEFS["E"] and "npm" in SECTION_BRIEFS["E"]
    assert "the Python dependencies" not in SECTION_BRIEFS["E"]
