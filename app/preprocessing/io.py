import csv
import json
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def _excel_value(cell, shared_strings):
    value = cell.find("m:v", NS)
    if value is None:
        inline = cell.find(".//m:t", NS)
        return inline.text if inline is not None else ""
    result = value.text or ""
    if cell.attrib.get("t") == "s":
        result = shared_strings[int(result)]
    return result


def read_xlsx(path):
    with zipfile.ZipFile(path) as archive:
        shared = []
        try:
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = ["".join(t.text or "" for t in item.findall(".//m:t", NS))
                      for item in root.findall("m:si", NS)]
        except KeyError:
            pass

        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {r.attrib["Id"]: r.attrib["Target"] for r in rels}
        sheet = workbook.find("m:sheets/m:sheet", NS)
        rel_id = sheet.attrib[f"{{{REL_NS}}}id"]
        target = targets[rel_id].lstrip("/")
        target = target if target.startswith("xl/") else "xl/" + target
        root = ET.fromstring(archive.read(target))

        rows = []
        for row in root.findall(".//m:sheetData/m:row", NS):
            values = {}
            for cell in row.findall("m:c", NS):
                ref = cell.attrib.get("r", "")
                column = "".join(ch for ch in ref if ch.isalpha())
                values[column] = _excel_value(cell, shared)
            rows.append(values)
        if not rows:
            return []
        headers = [str(v).strip() for v in rows[0].values()]
        return [{headers[i]: row.get(chr(65 + i), "") for i in range(len(headers))}
                for row in rows[1:]]


def read_posts(path):
    path = Path(path)
    if path.suffix.lower() == ".xlsx":
        rows = read_xlsx(path)
    elif path.suffix.lower() == ".jsonl":
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    else:
        with path.open(encoding="utf-8-sig", newline="") as file:
            rows = list(csv.DictReader(file))

    result = []
    for index, row in enumerate(rows, 1):
        content = str(row.get("Content", row.get("content", "")) or "").strip()
        if not content:
            continue
        result.append({
            "post_id": str(row.get("post_id") or row.get("STT") or index),
            "post_url": str(row.get("URL", row.get("post_url", "")) or "").strip(),
            "source_group": str(row.get(" Group", row.get("Group", row.get("source_group", ""))) or "").strip(),
            "subject": str(row.get("Subject", row.get("subject", "")) or "").strip(),
            "grade": str(row.get("Grade", row.get("grade", "")) or "").strip(),
            "location": str(row.get("Location", row.get("location", "")) or "").strip(),
            "mode": str(row.get("Mode", row.get("mode", "")) or "").strip(),
            "budget": str(row.get("Budget", row.get("budget", "")) or "").strip(),
            "content": content,
            "posted_at": str(row.get("Posted At", row.get("posted_at", "")) or "").strip(),
            "collected_at": str(row.get("Collected At", row.get("collected_at", "")) or "").strip(),
        })
    return result


def write_csv(path, rows, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_jsonl(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")
