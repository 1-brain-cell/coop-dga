#!/usr/bin/env python3
"""
Build the Catalog search index for day5.html.

Pipeline (Phase 1 of the RAG/search plan):
    sources.json  ->  locate/download PDF  ->  extract text  ->  (OCR if needed)
                  ->  Thai word tokenize    ->  catalog-index.json

The script degrades gracefully: every external dependency is optional. If a
library or a PDF is missing, the affected step is skipped and a metadata-only
entry is still written, so the site keeps working while you fill in the gaps.

Usage:
    python build_index.py                # build from PDFs in ./raw (or metadata only)
    python build_index.py --download     # also try to fetch public Drive files into ./raw
    python build_index.py --no-ocr       # skip OCR even for image-only PDFs

Optional dependencies (install only what you need):
    pip install pypdf pdfplumber pythainlp        # text PDFs + Thai tokenizing
    pip install pdf2image pytesseract pillow       # OCR for image/scanned slides
    # OCR also needs the Tesseract binary + Thai data:
    #   Windows: install Tesseract, add Thai (tha) language data
    #   then `pytesseract` will pick it up
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

DRIVE_VIEW = "https://drive.google.com/file/d/{fid}/view?usp=sharing"
DRIVE_DOWNLOAD = "https://drive.google.com/uc?export=download&id={fid}"

# Heuristic: if a PDF yields fewer chars than this, treat it as image-only and OCR.
MIN_TEXT_CHARS = 40


# --------------------------------------------------------------------------- #
# Text extraction
# --------------------------------------------------------------------------- #
def extract_with_pypdf(pdf_path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return ""
    try:
        reader = PdfReader(str(pdf_path))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception as exc:  # noqa: BLE001
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
    except Exception as exc:  # noqa: BLE001
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
    except Exception as exc:  # noqa: BLE001
        print(f"    pdf2image failed (is poppler installed?): {exc}", file=sys.stderr)
        return ""
    out = []
    for img in images:
        try:
            out.append(pytesseract.image_to_string(img, lang="tha+eng"))
        except Exception as exc:  # noqa: BLE001
            print(f"    tesseract failed (is 'tha' data installed?): {exc}",
                  file=sys.stderr)
            return ""
    return "\n".join(out)


def extract_text(pdf_path: Path, use_ocr: bool) -> str:
    text = extract_with_pypdf(pdf_path)
    
    # Check if text is poor quality (too short or contains too many null bytes)
    pypdf_is_bad = len(text.strip()) < MIN_TEXT_CHARS or text.count('\x00') > 5
    
    if pypdf_is_bad:
        if text.count('\x00') > 5:
            print(f"    pypdf extracted text contains {text.count(chr(0))} null characters (garbled font) — trying pdfplumber fallback", file=sys.stderr)
        plumber_text = extract_with_pdfplumber(pdf_path)
        if plumber_text:
            text = plumber_text
            
    # Check if text is still poor quality after pdfplumber
    plumber_is_bad = len(text.strip()) < MIN_TEXT_CHARS or text.count('\x00') > 5
    
    if plumber_is_bad and use_ocr:
        reason = "little/no text" if len(text.strip()) < MIN_TEXT_CHARS else f"{text.count(chr(0))} null characters"
        print(f"    {reason} (garbled font) — trying OCR", file=sys.stderr)
        ocr_text = extract_with_ocr(pdf_path)
        if ocr_text:
            text = ocr_text
            
    # Clean up any remaining null bytes from the final text
    text = text.replace('\x00', '')
    return text



# --------------------------------------------------------------------------- #
# Thai tokenization
# --------------------------------------------------------------------------- #
_thai_tokenizer = None
_tokenizer_ready = None  # None = unknown, True/False once probed


def thai_tokenize(text: str) -> str:
    """Return text with word boundaries as spaces, so a JS full-text index can match.

    Uses PyThaiNLP when available. Falls back to a regex that separates Thai runs,
    Latin/number runs, so at least non-Thai keywords stay searchable.
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
        except Exception as exc:  # noqa: BLE001
            print(f"    pythainlp failed: {exc} — using fallback", file=sys.stderr)

    # Fallback: split Thai vs non-Thai segments (no true Thai word boundaries).
    parts = re.findall(r"[฀-๿]+|[A-Za-z0-9.]+", text)
    return " ".join(parts)


# --------------------------------------------------------------------------- #
# Drive download (optional, public files only)
# --------------------------------------------------------------------------- #
def download_from_drive(fid: str, dest: Path) -> bool:
    try:
        import urllib.request
    except ImportError:
        return False
    url = DRIVE_DOWNLOAD.format(fid=fid)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
        # Large files return an HTML confirmation page instead of the PDF.
        if data[:4] != b"%PDF":
            print(f"    Drive did not return a PDF for {fid} "
                  f"(file may be private or need manual download)", file=sys.stderr)
            return False
        dest.write_bytes(data)
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"    download failed for {fid}: {exc}", file=sys.stderr)
        return False


def find_pdf(entry: dict) -> Path | None:
    """Look for a local PDF named by id or drive_file_id, or an explicit 'file'."""
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
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s


def discover() -> None:
    """Scan raw/*.pdf and add a stub entry to sources.json for any new file.

    Lets you drop many PDFs into raw/ and get a pre-filled sources.json to edit
    (title is guessed from the filename; fill in org / drive_file_id / tags after).
    """
    RAW_DIR.mkdir(exist_ok=True)
    sources = json.loads(SOURCES.read_text(encoding="utf-8")) if SOURCES.exists() else []

    covered = set()
    used_ids = set()
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
            "file": pdf.name,        # exact PDF in raw/ to read
            "drive_file_id": "",     # TODO: fill in for the "เปิดเอกสาร PDF" link
            "icon": "fa-file-lines",
            "org": "",               # TODO: ชื่อหน่วยงาน
            "title": stem,           # guessed from filename — edit as needed
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


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
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
            print("    no local PDF found — metadata-only entry "
                  "(drop a PDF in catalog/raw/ and rebuild)")

        # Everything searchable, tokenized for Thai-aware matching.
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
            "url": url,
            "content": content,
            "content_tokens": content_tokens,
        })

    return index


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Catalog search index.")
    parser.add_argument("--no-ocr", action="store_true",
                        help="skip OCR even for image-only PDFs")
    parser.add_argument("--download", action="store_true",
                        help="try to fetch public Drive files into ./raw")
    parser.add_argument("--discover", action="store_true",
                        help="scan raw/*.pdf and add stub entries to sources.json, then build")
    args = parser.parse_args()

    if args.discover:
        discover()

    if not SOURCES.exists():
        sys.exit(f"missing {SOURCES} — create it first")

    index = build(use_ocr=not args.no_ocr, do_download=args.download)
    OUTPUT.write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"\nwrote {OUTPUT}  ({len(index)} entries)")


if __name__ == "__main__":
    main()
