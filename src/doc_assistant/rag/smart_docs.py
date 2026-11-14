from __future__ import annotations

from src.doc_assistant.rag.answer import AnswerService


class SmartDocsService:
    """Map-reduce document workflows powered by the configured Gemini model."""

    CHUNK_CHARS = 18000
    MAX_CHUNKS = 30

    def __init__(self, settings):
        self.settings = settings
        self.generator = AnswerService(settings)

    @classmethod
    def _split_text(cls, text: str) -> list[str]:
        paragraphs = [part.strip() for part in text.splitlines() if part.strip()]
        chunks: list[str] = []
        current = ""
        for paragraph in paragraphs:
            # A very long paragraph is split safely instead of exceeding the prompt budget.
            pieces = [
                paragraph[i:i + cls.CHUNK_CHARS]
                for i in range(0, len(paragraph), cls.CHUNK_CHARS)
            ]
            for piece in pieces:
                if current and len(current) + len(piece) + 2 > cls.CHUNK_CHARS:
                    chunks.append(current)
                    current = piece
                else:
                    current = f"{current}\n{piece}".strip()
        if current:
            chunks.append(current)
        return chunks

    def run(self, document_text: str, task: str, instructions: str = "") -> str:
        if not self.settings.gemini_api_key:
            raise RuntimeError("Gemini API key is not configured in Streamlit Secrets.")
        if task not in {"Summarise document", "Create an SOP", "Explain an existing SOP"}:
            raise ValueError("Choose a supported Smart Docs task.")
        chunks = self._split_text(document_text)
        if not chunks:
            raise ValueError("The uploaded document contains no readable text.")
        if len(chunks) > self.MAX_CHUNKS:
            raise ValueError(
                f"This document is very large ({len(chunks)} processing sections). "
                f"The current free-demo limit is {self.MAX_CHUNKS} sections. "
                "Try a smaller document or split it into volumes."
            )

        if task == "Summarise document":
            map_instruction = (
                "Summarise this section of a larger document. Capture its heading, key ideas, "
                "important facts, figures, dates, definitions, risks and action items. Preserve "
                "technical terms and do not invent missing information."
            )
        elif task == "Create an SOP":
            map_instruction = (
                "Extract organisation-wide process information from this section for a formal, "
                "department-neutral SOP. Capture: process purpose and boundaries; trigger and end "
                "condition; process owner and participating roles; cross-functional hand-offs; "
                "inputs, outputs and dependencies; prerequisites; systems, tools or resources; "
                "ordered activities; decision points and criteria; approvals and control points; "
                "risks, safeguards and quality checks; records and evidence; exceptions, service "
                "failures and escalation routes; measures or service levels if stated; and related "
                "policies or documents. Do not assume a particular industry, department, system, "
                "role or regulatory framework. Do not invent absent steps; record gaps as "
                "'Not specified in source'."
            )
        else:
            map_instruction = (
                "Explain this SOP section in plain language. Identify its purpose, who does what, "
                "prerequisites, numbered actions, decision points, warnings, records and escalation. "
                "Explain technical terms briefly and flag ambiguous or missing instructions."
            )

        section_notes = []
        for index, chunk in enumerate(chunks, start=1):
            prompt = (
                "You are DocuMind Smart Docs. Analyse only the supplied document section. "
                f"{map_instruction}\n\n"
                f"SECTION {index} OF {len(chunks)}:\n{chunk}\n\n"
                "Return concise, structured notes. Keep specific values and conditions exactly as written."
            )
            section_notes.append(
                f"### Extracted notes — section {index}\n{self.generator._call_gemini(prompt, 1100)}"
            )

        if task == "Summarise document":
            final_instruction = (
                "Create a useful, well-organised document summary with: executive summary; "
                "section-by-section summary; key points; important numbers, dates and definitions; "
                "risks, obligations and action items; and a short 'What matters most' section. "
                "Do not repeat the same point unnecessarily."
            )
        elif task == "Create an SOP":
            final_instruction = (
                "Create a formal, organisation-wide, department-neutral draft SOP using only the "
                "extracted source notes. This template must work for processes from any business "
                "function or industry; do not make it specific to one department. Use these "
                "sections where the source supports them: "
                "1. Document Control (document ID, version, status, owner, approver, effective "
                "date and review date; use placeholders when absent); "
                "2. Purpose and Intended Outcome; "
                "3. Scope, Boundaries and Exclusions; "
                "4. Terms, Definitions and References; "
                "5. Process Ownership and Roles; include a RACI-style table only where the source "
                "identifies responsibilities, otherwise mark roles for confirmation; "
                "6. Trigger, Inputs, Preconditions and Dependencies; "
                "7. Systems, Tools and Resources; "
                "8. End-to-End Procedure with numbered actions, responsible role, expected "
                "output and decision/acceptance criteria; "
                "9. Cross-Functional Handoffs and Communications; "
                "10. Controls, Approvals, Risk Considerations and Quality Checks; "
                "11. Exceptions, Rework, Incident Handling and Escalation; "
                "12. Outputs, Records, Evidence and Retention requirements; "
                "13. Performance Measures or Service Levels, only if defined in the source; "
                "14. Related Documents; "
                "15. Review, Change and Approval History; "
                "16. Gaps Requiring Process-Owner Confirmation. "
                "Keep the document concise but operationally useful. Distinguish source-backed "
                "requirements from proposed placeholders. Never invent policy, legal obligations, "
                "approval limits, role assignments, service levels, safety controls or retention "
                "periods. For missing information write '[Confirm with process owner]'. If a "
                "section is not applicable or not supported, say so rather than guessing. "
                "Label the result clearly as DRAFT — NOT APPROVED FOR OPERATIONAL USE."
            )
        else:
            final_instruction = (
                "Teach this SOP to a new employee in plain language. Start with what the SOP is "
                "trying to achieve, then explain each step in order, who owns it, what inputs are "
                "needed, what decisions must be made, what evidence/records are produced, and when "
                "to stop or escalate. Include a quick-reference checklist, common mistakes, and "
                "questions the reader should ask the process owner where the SOP is unclear. "
                "Do not add steps that are not supported by the source."
            )

        combined = "\n\n".join(section_notes)
        final_prompt = (
            "You are DocuMind Smart Docs, an expert document analyst. Synthesize the section notes "
            "into one coherent output. The notes are derived from the uploaded source document; "
            "do not add unsupported facts. Clearly identify uncertainties and omissions.\n\n"
            f"TASK: {task}\n"
            f"ADDITIONAL USER INSTRUCTIONS: {instructions or 'None'}\n\n"
            f"REQUIRED OUTPUT:\n{final_instruction}\n\n"
            f"SECTION NOTES:\n{combined}\n\n"
            "Write in clear Markdown with useful headings and tables where appropriate."
        )
        return self.generator._call_gemini(final_prompt, 5000)
