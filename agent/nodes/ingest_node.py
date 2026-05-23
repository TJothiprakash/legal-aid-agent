import time
import fitz
import pytesseract
from PIL import Image
from langdetect import detect
from agent.state import AgentState


def ingest_node(state: AgentState) -> AgentState:
    start = time.time()
    errors = list(state.get("errors", []))

    try:
        file_bytes: bytes = state["_file_bytes"]
        file_type = state["file_type"].lower()
        raw_text = ""

        if file_type == "pdf":
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            for page in doc:
                raw_text += page.get_text()
            if len(raw_text.strip()) < 50:
                for page in doc:
                    pix = page.get_pixmap(dpi=200)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    raw_text += pytesseract.image_to_string(img)

        elif file_type in ("jpg", "jpeg", "png", "image"):
            import io
            img = Image.open(io.BytesIO(file_bytes))
            raw_text = pytesseract.image_to_string(img)

        else:
            raw_text = file_bytes.decode("utf-8", errors="ignore")

        raw_text = " ".join(raw_text.split())

        try:
            detected_language = detect(raw_text[:500]) if raw_text else "en"
            if detected_language not in ("en", "ta"):
                detected_language = "en"
        except Exception:
            detected_language = "en"

    except Exception as e:
        errors.append(f"ingest_node error: {str(e)}")
        raw_text = ""
        detected_language = "en"

    timings = dict(state.get("node_timings", {}))
    timings["ingest"] = round(time.time() - start, 3)

    return {
        **state,
        "raw_text":          raw_text,
        "detected_language": detected_language,
        "errors":            errors,
        "node_timings":      timings,
    }