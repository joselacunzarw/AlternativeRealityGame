import re


_REPLY_DELIMITERS = [
    re.compile(r"^\s*>"),
    re.compile(r"^\s*On .+wrote:\s*$", re.IGNORECASE),
    re.compile(r"^\s*(?:El|En) .+escribi[oó]:\s*$", re.IGNORECASE),
    re.compile(r"^\s*-{2,}\s*(?:Original Message|Mensaje original)\s*-{2,}\s*$", re.IGNORECASE),
    re.compile(r"^\s*-{2,}\s*Forwarded message\s*-{2,}\s*$", re.IGNORECASE),
]

_HEADER_BLOCK_PATTERNS = [
    re.compile(r"^\s*From:\s+", re.IGNORECASE),
    re.compile(r"^\s*De:\s+", re.IGNORECASE),
    re.compile(r"^\s*Sent:\s+", re.IGNORECASE),
    re.compile(r"^\s*Enviado:\s+", re.IGNORECASE),
    re.compile(r"^\s*To:\s+", re.IGNORECASE),
    re.compile(r"^\s*Para:\s+", re.IGNORECASE),
    re.compile(r"^\s*Cc:\s+", re.IGNORECASE),
    re.compile(r"^\s*Subject:\s+", re.IGNORECASE),
    re.compile(r"^\s*Asunto:\s+", re.IGNORECASE),
]


def extract_visible_reply(text: str) -> str:
    """
    Intenta quedarse solo con el contenido nuevo del jugador y descartar
    el historial citado por el cliente de correo.

    Si no encuentra delimitadores conocidos, devuelve el texto original limpio.
    """
    if not text:
        return ""

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    visible_lines: list[str] = []

    for line in lines:
        stripped = line.strip()

        if any(pattern.match(line) for pattern in _REPLY_DELIMITERS):
            break

        if stripped and any(pattern.match(line) for pattern in _HEADER_BLOCK_PATTERNS):
            break

        visible_lines.append(line)

    cleaned = "\n".join(visible_lines).strip()
    return cleaned or normalized.strip()
