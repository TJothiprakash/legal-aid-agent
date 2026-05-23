import os
from dotenv import load_dotenv
from langfuse import Langfuse

load_dotenv()

_client = None


def get_langfuse() -> Langfuse:
    global _client
    if _client is None:
        _client = Langfuse(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            host=os.getenv("LANGFUSE_BASE_URL"),
            flush_at=1,
            flush_interval=0.5,
        )
    return _client


def create_trace(
    document_id: str,
    session_id: str,
    document_type: str = "",
    language: str = "en",
) -> object:
    lf = get_langfuse()
    trace = lf.trace(
        name="legal_aid_run",
        id=document_id,
        session_id=session_id,
        metadata={
            "document_type": document_type,
            "language":      language,
        },
    )
    return trace


def log_span(
    trace,
    name: str,
    input_data: dict = {},
    output_data: dict = {},
    metadata: dict = {},
) -> None:
    try:
        trace.span(
            name=name,
            input=input_data,
            output=output_data,
            metadata=metadata,
        )
        get_langfuse().flush()
    except Exception as e:
        print(f"[langfuse] span error: {e}")


def log_llm_call(
    trace,
    name: str,
    model: str,
    prompt: str,
    completion: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> None:
    try:
        trace.generation(
            name=name,
            model=model,
            input=prompt,
            output=completion,
            usage={
                "input":  input_tokens,
                "output": output_tokens,
            },
        )
        get_langfuse().flush()
    except Exception as e:
        print(f"[langfuse] generation error: {e}")


def flush() -> None:
    try:
        get_langfuse().flush()
    except Exception as e:
        print(f"[langfuse] flush error: {e}")