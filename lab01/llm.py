"""One place for the model call used by every Lab 1 script.

LiteLLM is the only thing that knows which provider we are talking to, so the
rest of the lab code never mentions Groq or Gemini: it changes `LLM_MODEL` in
`.env` and nothing else. Keys are read from the environment (Codespaces
secrets), never from a file in this folder.
"""

import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

# Windows consoles are cp1252 by default; model replies contain narrow and
# non-breaking spaces that would crash print(). Never fail on output encoding.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = "groq/openai/gpt-oss-20b"

# Counts retries for the whole process, so a diagnostic report can say how often
# the provider needed a second attempt instead of hiding it.
RETRIES = 0

# Suffixes LiteLLM adds per provider, so the price table is easy to fill in.
_CLEAN = {
    "\u202f": " ", "\u00a0": " ", "\u2009": " ", "\u2007": " ",
    "\u2011": "-", "\u2013": "-", "\u2014": "-",
    "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
    "\u200b": "",
}


def clean(text: str) -> str:
    """Normalise exotic spaces and quotes so console and markdown output are safe."""
    for bad, good in _CLEAN.items():
        text = text.replace(bad, good)
    return text


def load_env() -> str:
    """Load `.env` from the repository root and return the model name."""
    load_dotenv(ROOT / ".env")
    return os.getenv("LLM_MODEL", DEFAULT_MODEL)


def mask(secret: str) -> str:
    """Show that a key exists without printing any part of it."""
    if not secret:
        return "(not set)"
    return f"set ({len(secret)} chars, value never written to disk)"


@dataclass
class Reply:
    """What one completion cost and said."""

    text: str
    model: str
    ms: float
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    attempts: int = 1
    finish_reason: str = ""
    raw: object = field(default=None, repr=False)

    def as_row(self) -> str:
        return (f"{self.ms:7.0f} ms  {self.prompt_tokens:5d}+{self.completion_tokens:<5d}"
                f" = {self.total_tokens:<6d} tokens")


def _retryable(error: Exception) -> bool:
    """Rate limits and transport blips are worth a retry; a bad request is not."""
    name = type(error).__name__
    text = str(error)
    if name in {"RateLimitError", "APIConnectionError", "APITimeoutError", "Timeout",
                "ServiceUnavailableError", "InternalServerError", "APIError",
                "ConnectError", "ReadTimeout", "ConnectTimeout"}:
        return True
    return any(code in text for code in ("429", "500", "502", "503", "timed out",
                                         "Connection", "overloaded"))


def chat(messages, temperature: float = 0.0, max_tokens: int | None = None,
         model: str | None = None, backoff=(5, 10, 20, 30)) -> Reply:
    """Call the model once, retrying rate limits with the given backoff."""
    global RETRIES
    model = model or load_env()
    from litellm import completion  # imported here so `--help` works without it

    last = None
    for attempt, wait in enumerate((0,) + tuple(backoff), start=1):
        if wait:
            time.sleep(wait)
        try:
            started = time.perf_counter()
            resp = completion(model=model, messages=messages, temperature=temperature,
                              max_tokens=max_tokens)
            ms = (time.perf_counter() - started) * 1000
            message = resp.choices[0].message
            usage = getattr(resp, "usage", None)
            RETRIES += attempt - 1
            return Reply(
                text=clean((message.content or "").strip()),
                model=model,
                ms=ms,
                prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
                total_tokens=getattr(usage, "total_tokens", 0) or 0,
                attempts=attempt,
                finish_reason=getattr(resp.choices[0], "finish_reason", "") or "",
                raw=resp,
            )
        except Exception as error:  # noqa: BLE001 - re-raised below unless retryable
            last = error
            if not _retryable(error):
                raise
            print(f"  [retry] {type(error).__name__}: {str(error)[:100]}"
                  f" (waiting {backoff[min(attempt - 1, len(backoff) - 1)]} s)", flush=True)
    raise last


def env_summary() -> list[str]:
    """Environment lines every evidence file starts with."""
    model = load_env()
    probe = "GROQ_API_KEY" if model.startswith("groq/") else "GEMINI_API_KEY"
    return [
        f"# model: {model}",
        f"# {probe}: {mask(os.getenv(probe, ''))}",
        f"# python: {sys.version.split()[0]}",
    ]
