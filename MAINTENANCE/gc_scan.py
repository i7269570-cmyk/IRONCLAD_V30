import os
import yaml
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(__file__))
RULES_PATH = os.path.join(ROOT, "MAINTENANCE", "gc_rules.yaml")
REPORT_PATH = os.path.join(ROOT, "MAINTENANCE", "gc_report.md")


def load_rules():
    with open(RULES_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def should_exclude(path: str, exclude_paths: list[str]) -> bool:
    norm = path.replace("\\", "/")
    return any(ex in norm for ex in exclude_paths)


def scan_file(path: str, rules: dict) -> list[str]:
    findings = []

    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        content = "".join(lines)

    for pattern in rules["rules"].get("forbid_patterns", []):
        if pattern in content:
            findings.append(f"FORBID_PATTERN: '{pattern}'")

    if "/RUNTIME/" in path.replace("\\", "/"):
        for pattern in rules["rules"].get("runtime_forbid", []):
            if pattern in content:
                findings.append(f"RUNTIME_STRATEGY_RISK: '{pattern}'")

    max_lines = rules["rules"].get("max_file_lines", 500)
    if len(lines) > max_lines:
        findings.append(f"FILE_TOO_LARGE: {len(lines)} lines")

    return findings


def main():
    rules = load_rules()
    exclude_paths = rules["rules"].get("exclude_paths", [])
    scan_exts = tuple(rules["rules"].get("scan_extensions", []))

    report_lines = [
        "# GC Scan Report",
        "",
        f"- Time: {datetime.now().isoformat()}",
        ""
    ]

    total_findings = 0

    for root, _, files in os.walk(ROOT):
        if should_exclude(root, exclude_paths):
            continue

        for file in files:
            if not file.endswith(scan_exts):
                continue

            path = os.path.join(root, file)
            if should_exclude(path, exclude_paths):
                continue

            findings = scan_file(path, rules)
            if findings:
                total_findings += len(findings)
                rel_path = os.path.relpath(path, ROOT).replace("\\", "/")
                report_lines.append(f"## {rel_path}")
                for item in findings:
                    report_lines.append(f"- {item}")
                report_lines.append("")

    if total_findings == 0:
        report_lines.append("No findings.")

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    print(f"GC_SCAN_COMPLETE: {total_findings} findings")
    print(f"REPORT: {REPORT_PATH}")


if __name__ == "__main__":
    main()