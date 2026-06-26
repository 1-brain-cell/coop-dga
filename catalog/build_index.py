#!/usr/bin/env python3
"""
Build the Catalog search index for day5.html.

Pipeline (1 เส้น):
    sources.json  +  raw/*.pdf   →   catalog-index.json   →   day5.html โหลดไปค้น

โหมด (ใช้ร่วมกันได้หลายโหมดพร้อมกัน):
    (ไม่มี flag)        build ปกติ — อ่าน PDF จาก raw/ หรือ metadata อย่างเดียว
    --discover          สแกน raw/*.pdf แล้วเติม stub entry ลง sources.json (ใช้ตอนเพิ่มไฟล์ใหม่)
    --link-drive        เติม drive_file_id โดย match ชื่อไฟล์กับ google_drive_links.json
    --download          ลองดาวน์โหลดไฟล์ Drive สาธารณะลง raw/ อัตโนมัติ
    --no-ocr            ข้าม OCR แม้ PDF จะเป็นรูปภาพ
    --strict            exit code 1 ถ้ามี entry ที่ปุ่ม "เปิดเอกสาร PDF" ใช้ไม่ได้

Optional dependencies (สคริปต์ยังรันได้แม้ไม่มีครบ):
    pip install pypdf pdfplumber pythainlp        # ดึงข้อความ PDF + ตัดคำไทย
    pip install pdf2image pytesseract pillow       # OCR สำหรับสไลด์ที่เป็นรูปภาพ
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCES = HERE / "sources.json"
RAW_DIR = HERE / "raw"
OUTPUT = HERE / "catalog-index.json"
DRIVE_LINKS = HERE / "google_drive_links.json"

DRIVE_VIEW = "https://drive.google.com/file/d/{fid}/view?usp=sharing"
DRIVE_DOWNLOAD = "https://drive.google.com/uc?export=download&id={fid}"

# Heuristic: if a PDF yields fewer chars than this, treat it as image-only and OCR.
MIN_TEXT_CHARS = 40


# ──────────────────────────────────────────────
# Text extraction
# ──────────────────────────────────────────────

def extract_with_pypdf(pdf_path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return ""
    try:
        reader = PdfReader(str(pdf_path))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception as exc:
        print(f"    pypdf failed: {exc}", file=sys.stderr)
        return ""


def extract_with_pdfplumber(pdf_path: Path) -> str:
    try:
        import pdfplumber
    except ImportError:
        return ""
    try:
        out = []
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page in pdf.pages:
                out.append(page.extract_text() or "")
        return "\n".join(out)
    except Exception as exc:
        print(f"    pdfplumber failed: {exc}", file=sys.stderr)
        return ""


def extract_with_ocr(pdf_path: Path) -> str:
    """OCR image-only PDFs (Thai + English). Needs pdf2image, pytesseract, Tesseract."""
    try:
        from pdf2image import convert_from_path
        import pytesseract
    except ImportError:
        print("    OCR libs not installed (pdf2image/pytesseract) — skipping OCR",
              file=sys.stderr)
        return ""
    try:
        images = convert_from_path(str(pdf_path), dpi=200)
    except Exception as exc:
        print(f"    pdf2image failed (is poppler installed?): {exc}", file=sys.stderr)
        return ""
    out = []
    for img in images:
        try:
            out.append(pytesseract.image_to_string(img, lang="tha+eng"))
        except Exception as exc:
            print(f"    tesseract failed (is 'tha' data installed?): {exc}",
                  file=sys.stderr)
            return ""
    return "\n".join(out)


def extract_text(pdf_path: Path, use_ocr: bool) -> str:
    text = extract_with_pypdf(pdf_path)

    pypdf_is_bad = len(text.strip()) < MIN_TEXT_CHARS or text.count('\x00') > 5
    if pypdf_is_bad:
        if text.count('\x00') > 5:
            print(f"    pypdf: {text.count(chr(0))} null chars (garbled font) — trying pdfplumber",
                  file=sys.stderr)
        plumber_text = extract_with_pdfplumber(pdf_path)
        if plumber_text:
            text = plumber_text

    plumber_is_bad = len(text.strip()) < MIN_TEXT_CHARS or text.count('\x00') > 5
    if plumber_is_bad and use_ocr:
        reason = ("little/no text" if len(text.strip()) < MIN_TEXT_CHARS
                  else f"{text.count(chr(0))} null characters")
        print(f"    {reason} — trying OCR", file=sys.stderr)
        ocr_text = extract_with_ocr(pdf_path)
        if ocr_text:
            text = ocr_text

    return text.replace('\x00', '')


# ──────────────────────────────────────────────
# Thai tokenization
# ──────────────────────────────────────────────

_thai_tokenizer = None
_tokenizer_ready = None  # None = unknown, True/False once probed


def thai_tokenize(text: str) -> str:
    """Return text with word boundaries as spaces for Thai-aware matching.

    Uses PyThaiNLP when available; falls back to a regex that separates
    Thai/Latin runs so non-Thai keywords stay searchable either way.
    """
    global _thai_tokenizer, _tokenizer_ready
    if _tokenizer_ready is None:
        try:
            from pythainlp.tokenize import word_tokenize
            _thai_tokenizer = word_tokenize
            _tokenizer_ready = True
        except ImportError:
            _tokenizer_ready = False
            print("    pythainlp not installed — using regex fallback tokenizer",
                  file=sys.stderr)

    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""

    if _tokenizer_ready:
        try:
            tokens = _thai_tokenizer(text, engine="newmm", keep_whitespace=False)
            return " ".join(t for t in tokens if t.strip())
        except Exception as exc:
            print(f"    pythainlp failed: {exc} — using fallback", file=sys.stderr)

    parts = re.findall(r"[฀-๿]+|[A-Za-z0-9.]+", text)
    return " ".join(parts)


# ──────────────────────────────────────────────
# Drive download (optional, public files only)
# ──────────────────────────────────────────────

def download_from_drive(fid: str, dest: Path) -> bool:
    import urllib.request
    url = DRIVE_DOWNLOAD.format(fid=fid)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
        if data[:4] != b"%PDF":
            print(f"    Drive did not return a PDF for {fid} "
                  f"(file may be private or need manual download)", file=sys.stderr)
            return False
        dest.write_bytes(data)
        return True
    except Exception as exc:
        print(f"    download failed for {fid}: {exc}", file=sys.stderr)
        return False


# ──────────────────────────────────────────────
# PDF locator + slug helper
# ──────────────────────────────────────────────

def find_pdf(entry: dict) -> Path | None:
    """Look for a local PDF named by id, drive_file_id, or explicit 'file'."""
    candidates = []
    if entry.get("file"):
        candidates.append(RAW_DIR / entry["file"])
    if entry.get("id"):
        candidates.append(RAW_DIR / f"{entry['id']}.pdf")
    if entry.get("drive_file_id"):
        candidates.append(RAW_DIR / f"{entry['drive_file_id']}.pdf")
    for c in candidates:
        if c.exists():
            return c
    return None


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


# ──────────────────────────────────────────────
# Mode: --discover  (scan raw/*.pdf → stub entries)
# ──────────────────────────────────────────────

def discover() -> None:
    """Scan raw/*.pdf and add a stub entry to sources.json for any new file.

    วาง PDF ลง raw/ แล้วรัน --discover จะได้ entry ใน sources.json ให้กรอก
    org / drive_file_id / title ต่อ (title ถูกเดาจากชื่อไฟล์ก่อน)
    """
    RAW_DIR.mkdir(exist_ok=True)
    sources = json.loads(SOURCES.read_text(encoding="utf-8")) if SOURCES.exists() else []

    covered: set[str] = set()
    used_ids: set[str] = set()
    for e in sources:
        if e.get("id"):
            used_ids.add(e["id"])
        p = find_pdf(e)
        if p:
            covered.add(p.name)

    added = 0
    for pdf in sorted(RAW_DIR.glob("*.pdf")):
        if pdf.name in covered:
            continue
        stem = pdf.stem
        base = slugify(stem) or stem or "doc"
        eid = base
        n = 1
        while eid in used_ids:
            n += 1
            eid = f"{base}-{n}"
        used_ids.add(eid)
        sources.append({
            "id": eid,
            "file": pdf.name,
            "drive_file_id": "",   # TODO: เติมจาก URL แชร์ Drive (/d/<ID>/view)
            "icon": "fa-file-lines",
            "org": "",             # TODO: ชื่อหน่วยงาน
            "title": stem,         # เดาจากชื่อไฟล์ — แก้ตามต้องการ
            "desc": "",
            "tags": [],
        })
        added += 1
        print(f"  + discovered {pdf.name}  ->  id={eid}")

    SOURCES.write_text(
        json.dumps(sources, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"discover: added {added} new entr{'y' if added == 1 else 'ies'} "
          f"to {SOURCES.name} (total {len(sources)})")


# ──────────────────────────────────────────────
# Mode: --link-drive  (เติม drive_file_id จาก google_drive_links.json)
# ──────────────────────────────────────────────

def _sanitize_filename(name: str) -> str:
    """Normalize filename for fuzzy matching (lowercase, strip ext, collapse separators)."""
    if not name:
        return ""
    name = name.lower()
    name = re.sub(r"\.pdf$", "", name)
    name = re.sub(r"[_\s']+", " ", name)
    return name.strip()


def _extract_fid(url: str) -> str:
    m = re.search(r"/d/([^/]+)", url or "")
    return m.group(1) if m else ""


def link_drive(links_path: Path = DRIVE_LINKS) -> None:
    """เติม drive_file_id ลง sources.json โดย match ชื่อไฟล์กับ google_drive_links.json

    - ไม่ทับ drive_file_id ที่มีอยู่แล้ว
    - รายงาน unmatched (ชื่อไฟล์ไม่ตรง) และ ambiguous (ซ้ำหลาย URL)
    """
    if not links_path.exists():
        print(f"--link-drive: ไม่พบ {links_path} — ข้าม", file=sys.stderr)
        return

    sources = json.loads(SOURCES.read_text(encoding="utf-8"))
    links = json.loads(links_path.read_text(encoding="utf-8"))

    # แมป sanitized-name → [file_id, ...]
    by_name: dict[str, list[str]] = {}
    for lnk in links:
        san = _sanitize_filename(lnk["name"])
        by_name.setdefault(san, []).append(_extract_fid(lnk["url"]))

    unmatched, filled = [], 0
    for entry in sources:
        if entry.get("drive_file_id"):
            continue
        fn = entry.get("file")
        if not fn:
            continue

        san_fn = _sanitize_filename(fn)

        # ถ้าชื่อมี (1) ให้ลอง match แบบไม่มี (1) ด้วย เช่น Rasamee(1) → Rasamee
        is_dupe_variant = False
        if "(1)" in fn:
            san_no1 = _sanitize_filename(fn.replace("(1)", ""))
            if san_no1 in by_name:
                san_fn = san_no1
                is_dupe_variant = True

        ids = by_name.get(san_fn)
        if not ids:
            unmatched.append(fn)
        elif len(ids) > 1:
            # ชื่อซ้ำ: ไฟล์ที่มี (1) ใช้ id ที่ 2, ไฟล์ปกติใช้ id แรก
            entry["drive_file_id"] = ids[1] if is_dupe_variant else ids[0]
            filled += 1
        else:
            entry["drive_file_id"] = ids[0]
            filled += 1

    SOURCES.write_text(
        json.dumps(sources, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"link-drive: เติม drive_file_id ให้ {filled} entry")
    if unmatched:
        print(f"  unmatched ({len(unmatched)} ชิ้น — เติมมือใน sources.json):")
        for fn in unmatched:
            print(f"    {fn}")


# ──────────────────────────────────────────────
# Main build
# ──────────────────────────────────────────────

def build(use_ocr: bool, do_download: bool) -> list[dict]:
    sources = json.loads(SOURCES.read_text(encoding="utf-8"))
    RAW_DIR.mkdir(exist_ok=True)
    index = []

    for entry in sources:
        eid = entry.get("id") or entry.get("drive_file_id") or entry.get("title")
        print(f"[{eid}] {entry.get('title', '')}")

        pdf_path = find_pdf(entry)
        if pdf_path is None and do_download and entry.get("drive_file_id"):
            dest = RAW_DIR / f"{entry['drive_file_id']}.pdf"
            print(f"    downloading {entry['drive_file_id']} ...")
            if download_from_drive(entry["drive_file_id"], dest):
                pdf_path = dest

        filename = pdf_path.name if pdf_path else f"{entry.get('title', eid)}.pdf"

        content = ""
        if pdf_path:
            content = extract_text(pdf_path, use_ocr).strip()
            print(f"    extracted {len(content)} chars")
        else:
            print("    no local PDF — metadata-only entry "
                  "(วาง PDF ใน catalog/raw/ แล้ว rebuild)")

        searchable = " ".join([
            entry.get("org", ""),
            entry.get("title", ""),
            entry.get("desc", ""),
            filename,
            " ".join(entry.get("tags", [])),
            content,
        ])
        content_tokens = thai_tokenize(searchable)

        url = entry.get("url")
        if not url and entry.get("drive_file_id"):
            url = DRIVE_VIEW.format(fid=entry["drive_file_id"])

        index.append({
            "id": eid,
            "icon": entry.get("icon", "fa-file-lines"),
            "org": entry.get("org", ""),
            "filename": filename,
            "title": entry.get("title", ""),
            "desc": entry.get("desc", ""),
            "tags": entry.get("tags", []),
            "year": entry.get("year"),
            "url": url,
            "content": content,
            "content_tokens": content_tokens,
        })

    return index


# ──────────────────────────────────────────────
# Build summary + --strict check
# ──────────────────────────────────────────────

def print_summary(index: list[dict], strict: bool) -> int:
    """พิมพ์สรุปสิ่งที่ยังไม่ครบ และ return exit code (1 ถ้า --strict และมีปัญหา)"""
    no_url = [it for it in index if not it.get("url")]
    no_org = [it for it in index if not it.get("org")]
    no_content = [it for it in index if not it.get("content")]

    print("\n── สรุปสถานะ ──────────────────────────────────────")
    print(f"  รวม: {len(index)} entry")

    if no_url:
        print(f"\n  ⚠  ปุ่ม 'เปิดเอกสาร PDF' ใช้ไม่ได้ ({len(no_url)} entry) — ต้องเติม drive_file_id หรือ url:")
        for it in no_url:
            print(f"       {it['id']}")
    else:
        print(f"  ✓  ทุก entry มี URL พร้อม ({len(index)} ชิ้น)")

    if no_org:
        print(f"\n  ⚠  org ว่าง ({len(no_org)} entry) — ค้นด้วยชื่อหน่วยงานไม่เจอ:")
        for it in no_org:
            print(f"       {it['id']}")
    else:
        print(f"  ✓  ทุก entry มี org")

    if no_content:
        print(f"\n  ℹ  content ว่าง ({len(no_content)} entry) — ค้นเนื้อหาในไฟล์ไม่ได้ (ไม่มี PDF หรือต้อง OCR):")
        for it in no_content:
            print(f"       {it['id']}")
    else:
        print(f"  ✓  ทุก entry มีเนื้อหา")

    print("────────────────────────────────────────────────────")

    if strict and no_url:
        print("\n  ERROR (--strict): มี entry ที่ปุ่ม PDF ใช้ไม่ได้ — แก้ก่อน commit", file=sys.stderr)
        return 1
    return 0


# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Catalog search index.")
    parser.add_argument("--no-ocr", action="store_true",
                        help="ข้าม OCR แม้ PDF จะเป็นรูปภาพ")
    parser.add_argument("--download", action="store_true",
                        help="ลองดาวน์โหลดไฟล์ Drive สาธารณะลง raw/ อัตโนมัติ")
    parser.add_argument("--discover", action="store_true",
                        help="สแกน raw/*.pdf เติม stub entry ลง sources.json แล้ว build")
    parser.add_argument("--link-drive", action="store_true",
                        help="เติม drive_file_id โดย match ชื่อไฟล์กับ google_drive_links.json")
    parser.add_argument("--strict", action="store_true",
                        help="exit code 1 ถ้ามี entry ที่ปุ่ม PDF ใช้ไม่ได้ (ใช้ก่อน commit)")
    args = parser.parse_args()

    if args.discover:
        discover()

    if args.link_drive:
        link_drive()

    if not SOURCES.exists():
        sys.exit(f"missing {SOURCES} — สร้างไฟล์นี้ก่อน (หรือรัน --discover)")

    index = build(use_ocr=not args.no_ocr, do_download=args.download)
    OUTPUT.write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"\nwrote {OUTPUT}  ({len(index)} entries)")

    exit_code = print_summary(index, strict=args.strict)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
