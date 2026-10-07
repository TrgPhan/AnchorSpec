"""Validate the structure of the Vietnamese 12-week research plan (stdlib only)."""
from pathlib import Path
import hashlib
import json
import re


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs" / "plans" / "KE_HOACH_NGHIEN_CUU_DENSO_A2_12_TUAN.md"
REPORT = Path(__file__).with_name("a2_12_week_plan_validation.json")


def validate():
    raw = PLAN.read_bytes()
    text = raw.decode("utf-8", errors="strict").replace("\r\n", "\n")
    lines = text.splitlines()
    assert "\ufffd" not in text, "Unicode replacement character found"
    fences = [line for line in lines if line.startswith("```")]
    assert len(fences) % 2 == 0, "Unbalanced code fences"
    weeks = re.findall(r"^### Tu\u1ea7n (\d+) [^\n]+", text, re.M)
    assert weeks == [str(i) for i in range(1, 13)], weeks
    sections = re.findall(r"^## (\d+)\.", text, re.M)
    assert sections == [str(i) for i in range(1, 14)], sections
    diagrams = re.findall(r"```mermaid\n(.*?)\n```", text, re.S)
    assert len(diagrams) == 1, "Expected one Mermaid diagram"
    diagram = diagrams[0]
    nodes = set(re.findall(r"\b([A-Z][A-Z0-9]*)(?:\[|\{)", diagram))
    assert diagram.count("[") == diagram.count("]"), "Unbalanced node brackets"
    assert diagram.count("{") == diagram.count("}"), "Unbalanced decision braces"
    references = re.findall(
        r"-->\s*(?:\|[^|]+\|\s*)?([A-Z][A-Z0-9]*)|\.->\s*([A-Z][A-Z0-9]*)",
        diagram,
    )
    targets = {value for pair in references for value in pair if value}
    assert targets <= nodes, sorted(targets - nodes)
    table_errors = []
    for index, line in enumerate(lines):
        if line.startswith("|") and not (index and lines[index - 1].startswith("|")):
            columns = line.count("|")
            cursor = index
            while cursor < len(lines) and lines[cursor].startswith("|"):
                if lines[cursor].count("|") != columns:
                    table_errors.append(cursor + 1)
                cursor += 1
    assert not table_errors, table_errors
    for term in ["G0", "G7", "real-only", "DDPM", "surrogate", "physics",
                 "provenance", "RUL", "CC BY-NC", "Mermaid", "N1", "N5", "unknown"]:
        assert term.lower() in text.lower(), term
    report = {
        "file": str(PLAN),
        "bytes": len(raw),
        "lines": len(lines),
        "weeks": weeks,
        "sections": sections,
        "code_fences": len(fences),
        "mermaid_nodes": len(nodes),
        "utf8": "passed",
        "table_consistency": "passed",
        "mermaid_structure": "passed; syntax not parsed or rendered",
        "sha256": hashlib.sha256(raw).hexdigest(),
        "scope": "Document structure only; no ML experiment or scientific validation",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    validate()
