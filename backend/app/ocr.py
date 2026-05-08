import io
import fitz  # PyMuPDF
import pytesseract
from PIL import Image


def extract_text_from_pdf(file_path: str) -> str:
    texts: list[str] = []
    doc = fitz.open(file_path)
    for page in doc:
        text = page.get_text()
        if text.strip():
            texts.append(text.strip())
        else:
            pix = page.get_pixmap(dpi=200)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            ocr_text = pytesseract.image_to_string(img)
            if ocr_text.strip():
                texts.append(ocr_text.strip())
    doc.close()
    return "\n\n".join(texts)


def extract_text_from_image(file_path: str) -> str:
    img = Image.open(file_path)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    return pytesseract.image_to_string(img).strip()


def extract_text(file_path: str, file_type: str) -> str:
    if file_type == "pdf":
        return extract_text_from_pdf(file_path)
    return extract_text_from_image(file_path)
