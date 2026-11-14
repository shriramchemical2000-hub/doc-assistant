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
    assert "10 questions" in output
    assert "New employees" in output
    assert "Employees must submit the form" in output
