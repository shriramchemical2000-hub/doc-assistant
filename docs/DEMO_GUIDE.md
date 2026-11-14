# DocuMind demo walkthrough

This guide uses fictional sample documents included in `sample_documents/`. They contain no real company policies or personal information.

## 1. Load the sample knowledge base

In the app sidebar, upload and index these files:

- `Enterprise_Document_Control_Standard_v1.txt`
- `Enterprise_Document_Control_Standard_v2.txt`
- `Enterprise_Process_Change_Procedure.txt`

## 2. Demonstrate document Q&A

Open **Ask documents** and ask questions such as:

- What is the review cycle in version 1.0 of the document control standard?
- Who verifies the document metadata before publication?
- What records must be retained for a process change?

Inspect the retrieved source passages to verify the answer.

## 3. Demonstrate Smart Docs

Open **Smart Docs**, upload one sample document and try:

- Summarise document
- Create an SOP
- Explain an existing SOP

The SOP generator is designed to be department-neutral. It must mark missing process details for owner confirmation rather than inventing requirements.

## 4. Demonstrate version comparison

Open **Document Comparison**. Upload the v1 and v2 document control standards in the earlier/newer fields. Review the changed review cycle, added Risk Reviewer role, approval wording and change impact notes.

## 5. Demonstrate gap and conflict review

Open **Gap & Conflict Review** and analyse the indexed sample documents together. Review any potential inconsistency between the document control approval rule and the process change procedure. Treat the output as an AI-assisted review requiring a document owner's validation.

## 6. Demonstrate training content

Open **Training Assistant**, upload the process change procedure and generate a training guide, FAQ, quiz or quick-reference checklist.

## 7. Demonstrate governance metadata

Open **Document Governance**. For each indexed document, set an owner, lifecycle status, version, review date and category. Save the metadata and verify that it remains visible in the register for the current browser session.

## Demo limitations

- The sample files are fictional and exist only to demonstrate the workflows.
- The governance register is a lightweight metadata feature, not a full records-management or approval platform.
- The app's demo workspace is session-isolated. Do not upload confidential company or personal documents.
- AI-generated comparisons, gap findings and training materials require human review before operational use.
- This portfolio MVP does not provide enterprise SSO, role-based access control, immutable audit trails, formal approval routing or guaranteed persistent storage.
