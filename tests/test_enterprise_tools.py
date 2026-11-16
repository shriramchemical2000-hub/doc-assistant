from types import SimpleNamespace

from src.doc_assistant.rag.enterprise_tools import EnterpriseToolsService


def make_service():
    service = EnterpriseToolsService(SimpleNamespace(gemini_api_key="test-key"))
    service._generate = lambda prompt, max_tokens=5000: prompt
    return service


def test_comparison_prompt_requests_before_after_and_impact():
    output = make_service().compare_documents(
        "Approval requires manager sign-off.",
        "Approval requires department-head sign-off.",
        "policy_v1.txt",
        "policy_v2.txt",
    )
    assert "OLDER VERSION" in output
    assert "NEWER VERSION" in output
    assert "before/after" in output
    assert "department-head" in output


def test_gap_review_handles_multiple_documents():
    output = make_service().review_gaps_and_conflicts([
        {"filename": "policy.txt", "text": "Requests require manager approval."},
        {"filename": "procedure.txt", "text": "Requests are automatically approved."},
    ])
    assert "potential contradictions" in output
    assert "policy.txt" in output
    assert "procedure.txt" in output


def test_training_material_prompt_is_source_grounded():
    output = make_service().create_training_material(
        "Employees must submit the form before the deadline.",
        "process.txt",
        "Knowledge quiz",
        "New employees",
    )
    assert "15 questions" in output
    assert "New employees" in output
    assert "Employees must submit the form" in output

def test_comparison_indexes_additions_removals_and_modifications_with_source_evidence():
    output = make_service().compare_documents(
        "Requests require manager approval.\n"
        "The obsolete mailbox remains active.\n"
        "Use the standard request form.",
        "Requests require department-head approval.\n"
        "Use the standard request form.\n"
        "A tracking reference is created.",
        "policy_v1.txt",
        "policy_v2.txt",
    )

    assert "Deterministic change evidence index" in output
    assert "— MODIFIED" in output
    assert "— REMOVED" in output
    assert "— ADDED" in output
    assert "manager approval" in output
    assert "department-head approval" in output
    assert "The obsolete mailbox remains active" in output
    assert "A tracking reference is created" in output
    assert "[OLD-" in output
    assert "[NEW-" in output
    assert "human validation" in output


def test_comparison_does_not_report_case_or_whitespace_as_word_changes():
    output = make_service().compare_documents(
        "Approval requires manager sign-off.",
        "  approval   requires manager sign-off.  ",
        "policy_v1.txt",
        "policy_v2.txt",
    )

    assert "No word/number-level changes were detected" in output
    assert "punctuation, layout, tables or visual formatting" in output

