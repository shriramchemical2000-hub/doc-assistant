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
                "Extract process information from this section that could support a formal SOP: "
                "purpose, scope, triggers, responsible roles, prerequisites, equipment/materials, "
                "sequence of actions, decision points, limits, safety/quality checks, records, "
                "exceptions and escalation. Do not invent absent steps; label gaps as 'Not specified'."
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
                "Create a formal draft SOP based only on the extracted notes. Use these headings: "
                "Title; Purpose; Scope; Definitions; Roles and Responsibilities; Prerequisites; "
                "Tools/Materials; Procedure with numbered steps; Decision Points and Acceptance "
                "Criteria; Safety/Quality Checks; Records; Exceptions and Troubleshooting; "
                "Escalation; Revision/Approval placeholders; and Gaps Requiring Confirmation. "
                "Never fabricate operating limits, approvals, safety controls or responsibilities. "
                "Mark missing details as [Confirm with process owner]. Label the result DRAFT."
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
