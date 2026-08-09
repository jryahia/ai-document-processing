import json
from openai import OpenAI
from .config import get_settings

settings = get_settings()


def get_client() -> OpenAI:
    return OpenAI(api_key=settings.openai_api_key)


def summarize_text(text: str) -> str:
    if not settings.openai_api_key or not text.strip():
        return "No summary available (OpenAI API key not configured or no text extracted)."

    client = get_client()
    truncated = text[:12000]
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a document analyst. Summarize the provided document text "
                    "in exactly 3 concise sentences. Focus on the key information, purpose, "
                    "and important details."
                ),
            },
            {"role": "user", "content": f"Document text:\n\n{truncated}"},
        ],
        max_tokens=300,
        temperature=0.3,
    )
    return response.choices[0].message.content or ""


def extract_structured_data(text: str) -> dict:
    if not settings.openai_api_key or not text.strip():
        return {}

    client = get_client()
    truncated = text[:12000]
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a data extraction specialist. Extract structured information from the document. "
                    "Return ONLY a valid JSON object with these fields (use null if not found):\n"
                    "{\n"
                    '  "document_type": string,\n'
                    '  "dates": [{"label": string, "value": string}],\n'
                    '  "names": [{"label": string, "value": string}],\n'
                    '  "amounts": [{"label": string, "value": string, "currency": string}],\n'
                    '  "invoice_number": string | null,\n'
                    '  "reference_numbers": [string],\n'
                    '  "addresses": [{"label": string, "value": string}],\n'
                    '  "organization": string | null,\n'
                    '  "key_fields": {"key": "value"}\n'
                    "}"
                ),
            },
            {"role": "user", "content": f"Document text:\n\n{truncated}"},
        ],
        max_tokens=1000,
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content or "{}"
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"raw_response": content}


# Fields the extraction prompt asks for. Scalars count as filled when non-null and
# non-blank; lists count as filled when they hold at least one non-empty item;
# key_fields counts as filled when the mapping has at least one non-empty value.
SCALAR_FIELDS = ("document_type", "invoice_number", "organization")
LIST_FIELDS = ("dates", "names", "amounts", "addresses", "reference_numbers")
MAPPING_FIELDS = ("key_fields",)
EXPECTED_FIELD_COUNT = len(SCALAR_FIELDS) + len(LIST_FIELDS) + len(MAPPING_FIELDS)


def _is_non_empty(value) -> bool:
    """True when `value` carries actual content (not None, not blank/empty)."""
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return any(_is_non_empty(item) for item in (value.values() if isinstance(value, dict) else value))
    return True


def compute_confidence_score(extracted: dict) -> int:
    """
    Heuristic extraction-completeness score in the range 0-100.

    Purely a function of the structured data returned by `extract_structured_data`:
    the percentage of the 9 expected fields that came back with content. It is
    deterministic, model-independent, and costs no extra tokens — it is a measure of
    how complete the extraction is, not of how correct the model believes it to be.

    An empty dict (no API key, or no text) scores 0.
    """
    if not isinstance(extracted, dict) or not extracted:
        return 0

    filled = 0
    for field in SCALAR_FIELDS + LIST_FIELDS + MAPPING_FIELDS:
        if _is_non_empty(extracted.get(field)):
            filled += 1

    return round(filled * 100 / EXPECTED_FIELD_COUNT)
