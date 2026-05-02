import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse


VALID_VAULT_TYPES = {"doc", "image", "audio", "video", "email"}
REQUIRED_CASE_FIELDS = {
    "case_id",
    "title",
    "briefing_intro",
    "duration_limit_hours",
    "director_logic",
    "vault_evidence",
    "characters",
}
REQUIRED_CHARACTER_FIELDS = {"name", "role", "system_prompt"}
REQUIRED_DIRECTOR_FIELDS = {"win_conditions", "lose_conditions"}
REQUIRED_EVENT_FIELDS = {
    "id",
    "trigger_after_hours",
    "trigger_condition",
    "character",
    "message_hint",
    "max_fires",
}
CASE_EMAIL_RE = re.compile(r"([A-Za-z0-9._%+-]+)@casos\.expedienteabierto\.com")
ARCHIVE_URL_RE = re.compile(r"https://archivos\.expedienteabierto\.com/[^\s\"')]+")
CASE_ALIAS_RE = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")


@dataclass(frozen=True)
class ValidationIssue:
    severity: str
    file_path: Path
    message: str
    case_id: str | None = None

    def format(self) -> str:
        prefix = f"[{self.severity.upper()}]"
        location = self.case_id or self.file_path.stem
        return f"{prefix} {location}: {self.message}"


def validate_case_directory(cases_dir: Path, assets_dir: Path | None = None) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for case_file in sorted(cases_dir.glob("*.json")):
        issues.extend(validate_case_file(case_file, assets_dir=assets_dir))
    return issues


def validate_case_file(case_file: Path, assets_dir: Path | None = None) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    try:
        case_data = json.loads(case_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [ValidationIssue("error", case_file, f"JSON invalido: {exc.msg}")]

    case_id = case_data.get("case_id")

    for field in sorted(REQUIRED_CASE_FIELDS):
        if field not in case_data:
            issues.append(_issue("error", case_file, f"Falta campo obligatorio '{field}'.", case_id))

    if issues:
        return issues

    if case_id != case_file.stem:
        issues.append(
            _issue(
                "error",
                case_file,
                f"case_id '{case_id}' no coincide con el nombre de archivo '{case_file.stem}'.",
                case_id,
            )
        )

    if not _is_non_empty_string(case_data.get("title")):
        issues.append(_issue("error", case_file, "title debe ser un string no vacio.", case_id))

    if not _is_non_empty_string(case_data.get("briefing_intro")):
        issues.append(_issue("error", case_file, "briefing_intro debe ser un string no vacio.", case_id))

    duration = case_data.get("duration_limit_hours")
    if not isinstance(duration, (int, float)) or duration <= 0:
        issues.append(_issue("error", case_file, "duration_limit_hours debe ser numerico y mayor a 0.", case_id))

    issues.extend(_validate_director_logic(case_file, case_id, case_data.get("director_logic")))
    issues.extend(_validate_characters(case_file, case_id, case_data.get("characters")))
    issues.extend(_validate_vault(case_file, case_id, case_data.get("vault_evidence")))
    issues.extend(_validate_proactive_events(case_file, case_id, case_data))
    issues.extend(_validate_briefing_contacts(case_file, case_id, case_data.get("briefing_intro", ""), case_data.get("characters", {})))
    issues.extend(_validate_archive_urls(case_file, case_id, case_data))

    if assets_dir is not None:
        case_assets_dir = assets_dir / case_id
        if not case_assets_dir.is_dir():
            issues.append(
                _issue(
                    "warning",
                    case_file,
                    f"No existe carpeta de assets para el caso en '{case_assets_dir}'.",
                    case_id,
                )
            )

    return issues


def format_issues(issues: Iterable[ValidationIssue]) -> str:
    return "\n".join(issue.format() for issue in issues)


def _validate_director_logic(case_file: Path, case_id: str, director_logic: object) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not isinstance(director_logic, dict):
        return [_issue("error", case_file, "director_logic debe ser un objeto JSON.", case_id)]

    for field in sorted(REQUIRED_DIRECTOR_FIELDS):
        if not _is_non_empty_string(director_logic.get(field)):
            issues.append(_issue("error", case_file, f"director_logic.{field} debe ser un string no vacio.", case_id))
    return issues


def _validate_characters(case_file: Path, case_id: str, characters: object) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not isinstance(characters, dict) or not characters:
        return [_issue("error", case_file, "characters debe ser un objeto no vacio.", case_id)]

    for alias, char_data in sorted(characters.items()):
        if not CASE_ALIAS_RE.match(alias):
            issues.append(_issue("error", case_file, f"Alias de personaje invalido: '{alias}'.", case_id))
        if not isinstance(char_data, dict):
            issues.append(_issue("error", case_file, f"characters['{alias}'] debe ser un objeto.", case_id))
            continue
        for field in sorted(REQUIRED_CHARACTER_FIELDS):
            if not _is_non_empty_string(char_data.get(field)):
                issues.append(
                    _issue("error", case_file, f"characters['{alias}'].{field} debe ser un string no vacio.", case_id)
                )
    return issues


def _validate_vault(case_file: Path, case_id: str, vault_evidence: object) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not isinstance(vault_evidence, dict) or not vault_evidence:
        return [_issue("error", case_file, "vault_evidence debe ser un objeto no vacio.", case_id)]

    seen_titles: set[str] = set()
    for code, evidence in sorted(vault_evidence.items()):
        if not isinstance(evidence, dict):
            issues.append(_issue("error", case_file, f"vault_evidence['{code}'] debe ser un objeto.", case_id))
            continue

        for field in ("title", "type", "desc"):
            if not _is_non_empty_string(evidence.get(field)):
                issues.append(
                    _issue("error", case_file, f"vault_evidence['{code}'].{field} debe ser un string no vacio.", case_id)
                )

        evidence_type = evidence.get("type")
        if isinstance(evidence_type, str) and evidence_type not in VALID_VAULT_TYPES:
            issues.append(
                _issue(
                    "error",
                    case_file,
                    f"vault_evidence['{code}'].type '{evidence_type}' no esta soportado.",
                    case_id,
                )
            )

        title = evidence.get("title")
        if isinstance(title, str):
            if title in seen_titles:
                issues.append(_issue("warning", case_file, f"vault_evidence reutiliza title '{title}'.", case_id))
            seen_titles.add(title)
    return issues


def _validate_proactive_events(case_file: Path, case_id: str, case_data: dict) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    proactive_events = case_data.get("proactive_events", [])
    if proactive_events in (None, []):
        return issues

    if not isinstance(proactive_events, list):
        return [_issue("error", case_file, "proactive_events debe ser una lista.", case_id)]

    duration = case_data.get("duration_limit_hours", 0)
    characters = case_data.get("characters", {})
    seen_ids: set[str] = set()

    for idx, event in enumerate(proactive_events):
        label = f"proactive_events[{idx}]"
        if not isinstance(event, dict):
            issues.append(_issue("error", case_file, f"{label} debe ser un objeto.", case_id))
            continue

        missing = sorted(field for field in REQUIRED_EVENT_FIELDS if field not in event)
        for field in missing:
            issues.append(_issue("error", case_file, f"{label} falta campo obligatorio '{field}'.", case_id))
        if missing:
            continue

        event_id = event.get("id")
        if event_id in seen_ids:
            issues.append(_issue("error", case_file, f"Evento proactivo duplicado: '{event_id}'.", case_id))
        seen_ids.add(event_id)

        if event.get("character") not in characters:
            issues.append(
                _issue(
                    "error",
                    case_file,
                    f"{label}.character referencia alias inexistente '{event.get('character')}'.",
                    case_id,
                )
            )

        trigger_after = event.get("trigger_after_hours")
        if not isinstance(trigger_after, (int, float)) or trigger_after < 0:
            issues.append(_issue("error", case_file, f"{label}.trigger_after_hours debe ser >= 0.", case_id))
        elif isinstance(duration, (int, float)) and trigger_after > duration:
            issues.append(
                _issue(
                    "warning",
                    case_file,
                    f"{label}.trigger_after_hours ({trigger_after}) excede duration_limit_hours ({duration}).",
                    case_id,
                )
            )

        max_fires = event.get("max_fires")
        if not isinstance(max_fires, int) or max_fires < 1:
            issues.append(_issue("error", case_file, f"{label}.max_fires debe ser entero >= 1.", case_id))

        for field in ("trigger_condition", "message_hint"):
            if not _is_non_empty_string(event.get(field)):
                issues.append(_issue("error", case_file, f"{label}.{field} debe ser un string no vacio.", case_id))

    return issues


def _validate_briefing_contacts(
    case_file: Path,
    case_id: str,
    briefing_intro: str,
    characters: dict,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    aliases = set(characters.keys())
    for match in CASE_EMAIL_RE.finditer(briefing_intro):
        alias = match.group(1)
        if alias not in aliases:
            issues.append(
                _issue(
                    "error",
                    case_file,
                    f"briefing_intro referencia contacto '{alias}@casos.expedienteabierto.com' sin personaje asociado.",
                    case_id,
                )
            )
    return issues


def _validate_archive_urls(case_file: Path, case_id: str, case_data: dict) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    expected_slug = _expected_archive_slug(case_id)
    for alias, char_data in case_data.get("characters", {}).items():
        prompt = char_data.get("system_prompt", "")
        if not isinstance(prompt, str):
            continue
        for raw_url in ARCHIVE_URL_RE.findall(prompt):
            parsed = urlparse(raw_url.rstrip(".,"))
            if parsed.netloc != "archivos.expedienteabierto.com":
                issues.append(_issue("error", case_file, f"URL de archivos invalida en '{alias}': {raw_url}", case_id))
                continue
            path_parts = [part for part in parsed.path.split("/") if part]
            if len(path_parts) < 2:
                issues.append(_issue("error", case_file, f"URL de archivos incompleta en '{alias}': {raw_url}", case_id))
                continue
            archive_slug = path_parts[0]
            if expected_slug and archive_slug != expected_slug:
                issues.append(
                    _issue(
                        "error",
                        case_file,
                        f"URL de archivos en '{alias}' apunta a '{archive_slug}' pero el caso espera '{expected_slug}'.",
                        case_id,
                    )
                )
    return issues


def _expected_archive_slug(case_id: str) -> str | None:
    number_match = re.search(r"_(\d+)$", case_id)
    if number_match:
        return f"caso{number_match.group(1)}"
    if case_id == "caso_cero":
        return "caso0"
    return None


def _issue(severity: str, case_file: Path, message: str, case_id: str | None = None) -> ValidationIssue:
    return ValidationIssue(severity=severity, file_path=case_file, message=message, case_id=case_id)


def _is_non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())
