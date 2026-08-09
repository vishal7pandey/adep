"""Classification prompt template for the classify_document tool [BLK-127, PE].

This prompt is sent to the VLM to classify a document page into one of the
known document types. The candidate types and their descriptions are injected
at runtime from the registered prebuilt definitions.
"""

CLASSIFY_PROMPT_TEMPLATE = """\
You are a document classification expert. Examine the provided document page image \
and classify it into one of the candidate document types listed below.

## Candidate Document Types

{candidate_list}

## Instructions

1. Analyze the visual layout, text content, structure, and formatting of the page.
2. Match the document to the most likely candidate type.
3. Provide a confidence score between 0.0 and 1.0.
4. Give a brief reasoning (1-2 sentences) explaining your classification.
5. If the document does not match any candidate type, set document_type to "unknown" \
with a low confidence score.

## Response Format

Respond with a JSON array of predictions, ranked by confidence (highest first). \
Each prediction must have these fields:

- "document_type": the type identifier from the candidate list, or "unknown"
- "confidence": float between 0.0 and 1.0
- "reasoning": brief explanation string

Example response:
```json
[
  {{"document_type": "invoice", "confidence": 0.92, "reasoning": "Contains vendor info, line items, and total amount due."}},
  {{"document_type": "purchase_order", "confidence": 0.45, "reasoning": "Has a table structure but lacks PO-specific fields."}}
]
```

Return ONLY the JSON array, no other text.
"""

MULTI_PAGE_PROMPT_TEMPLATE = """\
You are a document classification expert. You are given {page_count} page images \
from a multi-page document. Classify EACH page independently using the candidate \
types below, then determine if the document is multi-type (pages differ in type).

## Candidate Document Types

{candidate_list}

## Instructions

1. Analyze each page image separately.
2. For each page, provide a classification with document_type, confidence, and reasoning.
3. After classifying all pages, set "is_multi_type" to true if pages classify to \
different document types.

## Response Format

Respond with a JSON object:

```json
{{
  "pages": [
    {{"page": 1, "document_type": "invoice", "confidence": 0.92, "reasoning": "..."}},
    {{"page": 2, "document_type": "bank_statement", "confidence": 0.88, "reasoning": "..."}}
  ],
  "is_multi_type": true
}}
```

Return ONLY the JSON object, no other text.
"""


def build_candidate_list(candidates: list[dict[str, str]]) -> str:
    """Build the candidate type description list for the prompt.

    Args:
        candidates: List of dicts with "type" and "description" keys.

    Returns:
        Formatted string listing each candidate type.
    """
    lines = []
    for c in candidates:
        lines.append(f"- **{c['type']}**: {c['description']}")
    return "\n".join(lines)
