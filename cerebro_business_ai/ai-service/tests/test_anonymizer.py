from app.anonymizer import anonymize, restore

def test_identifiers_are_hidden_then_restored():
    original = "Jane Doe jane@example.com +1 555-123-4567"
    safe = anonymize(original)
    assert "jane@example.com" not in safe.text
    assert "+1 555-123-4567" not in safe.text
    assert restore(safe.text, safe.replacements) == original
