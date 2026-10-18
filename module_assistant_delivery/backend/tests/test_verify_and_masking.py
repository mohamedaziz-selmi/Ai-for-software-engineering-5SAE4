from app.assistant.verify import quote_in_text, verify_citations
from app.llm.masking import Masker
from app.rag.retriever import RetrievedChunk

CHUNK = RetrievedChunk(
    chunk_id="doc-1-c004", document_id="doc-1", document_title="Spec", document_version=1, project_id="P1",
    heading_path="Spec > 4. Non-negotiable requirements",
    text="- NN-1 Pickup capacity: a shop accepts at most 20 orders per 15-minute pickup slot, and booking for a slot closes 2 hours before the slot starts.",
    score=0.9, page=None, line_start=40, line_end=41,
)


def test_exact_and_normalised_quotes_pass():
    assert quote_in_text("accepts at most 20 orders per 15-minute pickup slot", CHUNK.text)
    assert quote_in_text("  ACCEPTS at most 20\n orders  ", CHUNK.text)
    assert quote_in_text("“booking for a slot closes 2 hours before the slot starts.”", CHUNK.text)
    assert quote_in_text("a shop accepts at most 20 orders ... closes 2 hours before", CHUNK.text)


def test_fabricated_or_reordered_quotes_fail():
    assert not quote_in_text("accepts at most 30 orders", CHUNK.text)
    assert not quote_in_text("closes 2 hours before ... at most 20 orders", CHUNK.text)
    assert not quote_in_text("20", CHUNK.text)  # too short to be evidence


def test_table_quotes_ignore_cell_separators_but_not_wording():
    table = "| M1 | End of week 3 | Prototype | 20% |\n| M2 | End of week 7 | Ordering flow | 30% |"
    # Observed from qwen2.5:7b-instruct on 2026-10-18: row-boundary pipes dropped.
    assert quote_in_text("M1 | End of week 3 | Prototype | 20% \nM2 | End of week 7 | Ordering flow | 30%", table)
    assert not quote_in_text("M2 | End of week 9 | Ordering flow | 30%", table)


def test_list_bullets_are_formatting_not_wording():
    chunk = "Any feature that is not listed in section 3.1 is a change request. The client sends change requests in writing."
    # Observed from qwen2.5:7b-instruct on 2026-10-18 (served through the UI): a bullet added to an exact quote.
    assert quote_in_text("- Any feature that is not listed in section 3.1 is a change request.", chunk)
    assert quote_in_text("NN-1 Pickup capacity: a shop accepts at most 20 orders", "- NN-1 Pickup capacity: a shop accepts at most 20 orders per slot")
    assert not quote_in_text("- Any feature that is listed in section 3.1 is a change request.", chunk)


def test_verify_drops_unknown_chunks_and_bad_quotes():
    result = verify_citations(
        [("C1", "at most 20 orders per 15-minute pickup slot"), ("C7", "at most 20 orders"), ("C1", "unlimited orders")],
        {"C1": CHUNK},
    )
    assert [v.label for v in result.valid] == ["C1"]
    assert {d["reason"] for d in result.dropped} == {"unknown_chunk", "quote_not_in_chunk"}


def test_masking_replaces_pii_and_restores_it():
    masker = Masker()
    text = ("Contact orders-pm@example.com or +216 98 123 456 / 22 333 444. IBAN TN59 1000 6035 1835 9847 8831. "
            "api_key = 'sk-abcdefghijklmnopqrstuvwxyz123456' CIN: 01234567. Price 18,000 TND, 12345678 units.")
    masked = masker.mask(text)
    for secret in ("orders-pm@example.com", "98 123 456", "22 333 444", "TN59 1000", "sk-abcdef", "01234567"):
        assert secret not in masked
    assert "18,000 TND" in masked and "12345678 units" in masked  # amounts are not personal data
    assert masker.unmask(masked) == text


def test_masking_secrets_in_code_keeps_code_structure():
    code = 'SMTP_PASSWORD = "Sm7p-Dem0-Passw0rd-2026"\ntoken = secrets.token_urlsafe(32)\napiKey: "abcd1234efgh"'
    masker = Masker()
    masked = masker.mask(code)
    assert "Sm7p-Dem0-Passw0rd-2026" not in masked and "abcd1234efgh" not in masked
    assert 'SMTP_PASSWORD = "<SECRET_1>"' in masked
    assert "token = secrets.token_urlsafe(32)" in masked  # an expression, not a secret
    assert masker.unmask(masked) == code


def test_masking_is_stable_for_repeated_values():
    masker = Masker()
    first = masker.mask("a@example.com wrote to b@example.com")
    second = masker.mask("reply to a@example.com")
    assert first == "<EMAIL_1> wrote to <EMAIL_2>" and second == "reply to <EMAIL_1>"
