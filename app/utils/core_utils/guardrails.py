"""Security guardrails for prompt injection prevention, indirect web injection defense, and secret leak scanning."""

import re
from typing import Tuple

from app.config.log_config import logger
from app.exceptions.domain import SecurityValidationError

# Max allowed topic length to prevent buffer/token exhaustion attacks
MAX_QUERY_LENGTH = 300

# High-confidence prompt injection signatures (case-insensitive)
PROMPT_INJECTION_PATTERNS = [
    # Direct instruction overrides
    re.compile(
        r"\b(?:ignore|disregard|forget|override|bypass|cancel)\b.{0,60}\b(?:previous|all|prior|system|above)\b.{0,40}\b(?:instructions?|prompts?|rules?|directives?|guidelines?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:do not follow|stop following)\b.{0,40}\b(?:instructions?|rules?|system)\b",
        re.IGNORECASE,
    ),
    # Jailbreak / persona hijack
    re.compile(
        r"\b(?:you are now|pretend you are|act as|roleplay as)\b.{0,60}\b(?:dan|unfiltered|jailbreak|developer mode|godmode|root)\b",
        re.IGNORECASE,
    ),
    # System prompt / secret exfiltration attempts
    re.compile(
        r"\b(?:reveal|print|output|display|show|echo|leak|dump)\b.{0,50}\b(?:system prompt|api[ _-]?keys?|environment|secret[ _-]?key|credentials?|passwords?|base prompt)\b",
        re.IGNORECASE,
    ),
    # Raw instruction delimiter injections
    re.compile(
        r"(\[INST\]|\[/INST\]|<<SYS>>|<</SYS>>|<\|im_start\|>|<\|im_end\|>|<\|system\|>|<\|assistant\|>)",
        re.IGNORECASE,
    ),
    # Fake system XML tag spoofing
    re.compile(
        r"<\/?(?:system|instruction|developer_note|assistant|human_message|user_instruction)>",
        re.IGNORECASE,
    ),
]

# Patterns in external web snippets that could hijack the downstream drafting LLM
INDIRECT_INJECTION_PATTERNS = [
    re.compile(
        r"(<!--.*?-->|<script[\s\S]*?<\/script>|<style[\s\S]*?<\/style>)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(\[INST\]|\[/INST\]|<<SYS>>|<</SYS>>|<\|im_start\|>|<\|im_end\|>|<\|system\|>|<\|assistant\|>)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:AI\s*INSTRUCTION|SYSTEM\s*COMMAND|NEW\s*INSTRUCTION):\s*.+",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:ignore\s+all\s+previous\s+instructions|disregard\s+prior\s+instructions)\b",
        re.IGNORECASE,
    ),
]

# Signatures for secret/credential leakage scanning in generated reports
SECRET_LEAK_PATTERNS = [
    (re.compile(r"tvly-[a-zA-Z0-9_\-]{20,}"), "[REDACTED_TAVILY_KEY]"),
    (re.compile(r"sk-[a-zA-Z0-9_\-]{20,}"), "[REDACTED_OPENAI_KEY]"),
    (re.compile(r"AIza[0-9A-Za-z_\-]{35}"), "[REDACTED_GEMINI_KEY]"),
    (
        re.compile(
            r"eyJ[a-zA-Z0-9_\-]{10,}\.eyJ[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]{10,}"
        ),
        "[REDACTED_JWT_TOKEN]",
    ),
    (
        re.compile(
            r"(?i)(?:api[ _-]?key|secret[ _-]?key|admin_password)\s*[:=]\s*['\"][^'\"]{6,}['\"]"
        ),
        "[REDACTED_CREDENTIAL]",
    ),
]


def validate_and_sanitize_query(
    raw_query: str,
    max_length: int = MAX_QUERY_LENGTH,
    strict_raise: bool = True,
) -> str:
    """Validate user query against prompt injection and adversarial manipulation.

    Args:
        raw_query: The raw topic or user prompt to validate.
        max_length: Maximum allowed query length.
        strict_raise: If True, raises SecurityValidationError on detected injection.
            If False, neutralizes patterns and returns safe text.

    Returns:
        Sanitized, validated query string.

    Raises:
        SecurityValidationError: If malicious injection pattern is detected and strict_raise=True.
    """
    if not raw_query or not raw_query.strip():
        return ""

    # Remove null bytes and control characters (except newline/tab)
    cleaned = "".join(
        ch for ch in raw_query if ch == "\n" or ch == "\t" or ord(ch) >= 32
    ).strip()

    # Enforce maximum length
    if len(cleaned) > max_length:
        logger.warning(
            "Query exceeded maximum safe length (%d > %d). Clamping.",
            len(cleaned),
            max_length,
        )
        cleaned = cleaned[:max_length].strip()

    # Check for direct prompt injection signatures
    for pattern in PROMPT_INJECTION_PATTERNS:
        match = pattern.search(cleaned)
        if match:
            matched_phrase = match.group(0)
            logger.warning(
                "Security Guardrail Triggered: Potential prompt injection detected '%s'",
                matched_phrase,
            )
            if strict_raise:
                raise SecurityValidationError(
                    f"Query rejected by security guardrail: Adversarial or prompt injection pattern detected ('{matched_phrase}')."
                )
            cleaned = pattern.sub("[REDACTED_ADVERSARIAL_INJECTION]", cleaned)

    return cleaned


def sanitize_external_content(content: str, max_chars: int = 3000) -> str:
    """Sanitize retrieved external web/document content to prevent indirect prompt injection.

    Neutralizes hidden instructions, script tags, HTML comments, and LLM boundary delimiters.

    Args:
        content: Raw snippet or article content from web search.
        max_chars: Maximum safe character length for single snippet.

    Returns:
        Sanitized content safe for inclusion in LLM prompt context.
    """
    if not content:
        return ""

    sanitized = content

    # Strip dangerous HTML comments, script tags, and prompt injection signatures
    for pattern in INDIRECT_INJECTION_PATTERNS:
        sanitized = pattern.sub(" ", sanitized)

    # Defang raw XML-like boundary tags
    sanitized = sanitized.replace("<system>", "&lt;system&gt;")
    sanitized = sanitized.replace("</system>", "&lt;/system&gt;")
    sanitized = sanitized.replace("<user_query>", "&lt;user_query&gt;")
    sanitized = sanitized.replace("</user_query>", "&lt;/user_query&gt;")

    # Remove null bytes
    sanitized = sanitized.replace("\x00", "")

    # Normalize excessive whitespace
    sanitized = re.sub(r"\s+", " ", sanitized).strip()

    if len(sanitized) > max_chars:
        sanitized = sanitized[:max_chars].strip() + "..."

    return sanitized


def scan_output_for_secrets(text: str) -> Tuple[bool, str]:
    """Scan synthesized report text for accidental credential or API key leakage.

    Args:
        text: Report markdown, JSON, or text to inspect.

    Returns:
        Tuple of (has_leaks: bool, sanitized_text: str).
    """
    if not text:
        return False, text

    has_leaks = False
    cleaned_text = text

    for pattern, replacement in SECRET_LEAK_PATTERNS:
        if pattern.search(cleaned_text):
            has_leaks = True
            logger.warning(
                "Security Guardrail Alert: Leaked credential pattern detected in output. Redacting."
            )
            cleaned_text = pattern.sub(replacement, cleaned_text)

    return has_leaks, cleaned_text


def wrap_untrusted_data(tag_name: str, data: str) -> str:
    """Wrap untrusted input or evidence in strict delimiter tags for LLM prompt context."""
    safe_data = sanitize_external_content(data)
    return f'<{tag_name} role="untrusted_context">\n{safe_data}\n</{tag_name}>'
