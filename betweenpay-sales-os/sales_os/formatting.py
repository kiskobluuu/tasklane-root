from __future__ import annotations

import re


def normalize_social_text(text: str | None, platform: str | None = None) -> str:
    """Normalize escaped/newline-heavy social copy before it reaches a provider."""
    value = str(text or "")
    value = value.replace("\r\n", "\n").replace("\r", "\n")

    # Repair literal escape sequences accidentally stored in queue/database copy.
    value = value.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\t", " ")

    # Clean whitespace around real line breaks and prevent giant blank gaps.
    value = re.sub(r"[ \t]+\n", "\n", value)
    value = re.sub(r"\n[ \t]+", "\n", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    value = re.sub(r"[ \t]{2,}", " ", value)

    value = value.strip()

    # Facebook readability: long AI copy should not be one uninterrupted wall.
    # Do not rewrite meaning; only add paragraph separation at sentence boundaries.
    if (platform or "").lower() == "facebook" and "\n\n" not in value and len(value) >= 260:
        sentences = re.split(r"(?<=[.!?])\s+", value)
        if len(sentences) >= 4:
            chunks = []
            current = []
            for sentence in sentences:
                current.append(sentence)
                if len(" ".join(current)) >= 150:
                    chunks.append(" ".join(current).strip())
                    current = []
            if current:
                chunks.append(" ".join(current).strip())
            if len(chunks) > 1:
                value = "\n\n".join(chunks)

    return value
