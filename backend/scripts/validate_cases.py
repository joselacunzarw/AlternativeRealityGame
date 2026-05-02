"""Valida consistencia estructural y referencias de los casos JSON."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.case_validator import format_issues, validate_case_directory


def main() -> int:
    cases_dir = ROOT / "casos"
    assets_dir = ROOT / "assets"
    issues = validate_case_directory(cases_dir, assets_dir=assets_dir)

    if issues:
        print(format_issues(issues))
        error_count = sum(1 for issue in issues if issue.severity == "error")
        warning_count = sum(1 for issue in issues if issue.severity == "warning")
        print(f"\nResumen: {error_count} error(es), {warning_count} warning(s).")
        return 1 if error_count else 0

    print("Todos los casos son validos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
