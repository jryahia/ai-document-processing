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
