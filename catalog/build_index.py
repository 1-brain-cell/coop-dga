#!/usr/bin/env python3
"""
Build the Catalog search index for day5.html.

Pipeline:
    sources.json + raw/*.pdf -> catalog-index.json -> day5.html

Default builds are preserve-safe: existing content fields are carried forward
from catalog-index.json, and PDF extraction runs only for new entries or
explicit refresh modes.

Optional dependencies:
    pip install pypdf pdfplumber pythainlp
    pip install pdf2image pytesseract pillow
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).resolve().parent
SOURCES = HERE / "sources.json"
RAW_DIR = HERE / "raw"
OUTPUT = HERE / "catalog-index.json"

DRIVE_VIEW = "https://drive.google.com/file/d/{fid}/view?usp=sharing"
DRIVE_DOWNLOAD = "https://drive.google.com/uc?export=download&id={fid}"

# If text extraction yields less than this, OCR may be worth trying.
MIN_TEXT_CHARS = 40


def _setup_ocr_tooling() -> None:
    """Add common Windows OCR tool locations when they are present."""
    import os

    tessdata = HERE / "tessdata"
    if (tessdata / "tha.traineddata").exists():
        os.environ.setdefault("TESSDATA_PREFIX", str(tessdata))

    extra_paths = []

    for base in [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages",
    ]:
        if base.exists():
            for exe in base.glob("oschwartz10612.Poppler*/**/pdftoppm.exe"):
                extra_paths.append(str(exe.parent))
                break

    for cand in [
        Path(r"C:\Program Files\Tesseract-OCR"),
        Path(r"C:\Program Files (x86)\Tesseract-OCR"),
    ]:
        if (cand / "tesseract.exe").exists():
            extra_paths.append(str(cand))
            break

    if extra_paths:
        os.environ["PATH"] = os.environ.get("PATH", "") + os.pathsep + os.pathsep.join(extra_paths)


_setup_ocr_tooling()


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
    """OCR a PDF (Thai + English). Needs pdf2image, pytesseract, Tesseract + poppler.

    Uses bytes input so poppler does not have to open Thai filenames directly
    on Windows.
    """
    try:
        from pdf2image import convert_from_bytes
        import pytesseract
    except ImportError:
        print("    OCR libs not installed (pdf2image/pytesseract) — skipping OCR",
              file=sys.stderr)
        return ""
    try:
        data = pdf_path.read_bytes()
        images = convert_from_bytes(data, dpi=300)
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
    return _collapse_thai_spacing("\n".join(out))


# OCR can insert spaces between Thai glyphs, which breaks substring search.
_THAI = r"฀-๿"
_THAI_GAP = re.compile(rf"(?<=[{_THAI}])\s+(?=[{_THAI}])")


def _collapse_thai_spacing(text: str) -> str:
    lines = []
    for line in text.splitlines():
        prev = None
        while prev != line:
            prev = line
            line = _THAI_GAP.sub("", line)
        lines.append(line)
    return "\n".join(lines)


def _has_little_text(text: str) -> bool:
    """Return True when a PDF likely has no useful text layer."""
    return len(text.strip()) < MIN_TEXT_CHARS


def extract_text(pdf_path: Path, use_ocr: bool) -> str:
    text = extract_with_pypdf(pdf_path)

    # Null chars usually mean a broken embedded font. pdfplumber may recover a
    # cleaner text layer; OCR is reserved for image-only PDFs because it is often
    # noisier on designed Thai slides.
    if _has_little_text(text) or text.count('\x00') > 5:
        if text.count('\x00') > 5:
            print(f"    pypdf: {text.count(chr(0))} null chars (garbled font) — trying pdfplumber",
                  file=sys.stderr)
        plumber_text = extract_with_pdfplumber(pdf_path)
        if plumber_text:
            text = plumber_text

    if _has_little_text(text) and use_ocr:
        print("    little/no text (image-only PDF) — trying OCR", file=sys.stderr)
        ocr_text = extract_with_ocr(pdf_path)
        if ocr_text:
            text = ocr_text

    return text.replace('\x00', '')


_thai_tokenizer = None
_tokenizer_ready = None  # None = unknown, True/False once probed


def thai_tokenize(text: str) -> str:
    """Return searchable text with Thai word boundaries when possible."""
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


def download_from_drive(fid: str, dest: Path) -> bool:
    """Download a public Drive PDF for local indexing."""
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


def find_pdf(entry: dict) -> Path | None:
    """Find the local PDF used as extraction input, if present."""
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


def next_catalog_id(sources: list[dict]) -> str:
    """Return the next catNNN ID without reordering sources."""
    highest = 0
    for entry in sources:
        m = re.fullmatch(r"cat(\d{3})", entry.get("id", ""))
        if m:
            highest = max(highest, int(m.group(1)))
    return f"cat{highest + 1:03d}"


def file_sha256(path: Path) -> str:
    """Hash the local PDF bytes used for extraction drift warnings."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_existing_index() -> list[dict]:
    """Load the previous generated index used as the preserve-safe baseline."""
    if not OUTPUT.exists():
        return []
    try:
        data = json.loads(OUTPUT.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"WARNING: could not read existing {OUTPUT.name}: {exc}", file=sys.stderr)
        return []
    if not isinstance(data, list):
        print(f"WARNING: existing {OUTPUT.name} is not a list; ignoring baseline", file=sys.stderr)
        return []
    return data


def make_content_tokens(entry: dict, filename: str, content: str) -> str:
    """Build the weak searchable content field used by day5.html."""
    searchable = " ".join([
        entry.get("org", ""),
        entry.get("title", ""),
        entry.get("desc", ""),
        filename,
        " ".join(entry.get("tags", [])),
        content,
    ])
    return thai_tokenize(searchable)


def extract_drive_file_id(value: str) -> str | None:
    """Extract a Drive file ID from supported share/download URL forms."""
    if not value:
        return None
    m = re.search(r"/file/d/([A-Za-z0-9_-]+)(?:/|$)", value)
    if m:
        return m.group(1)
    try:
        parsed = urlparse(value)
    except Exception:
        return None
    ids = parse_qs(parsed.query).get("id")
    if ids and re.fullmatch(r"[A-Za-z0-9_-]+", ids[0]):
        return ids[0]
    return None


def make_url(entry: dict) -> str | None:
    """Resolve the public document URL without writing normalized data back."""
    url = entry.get("url")
    if url:
        return url
    drive_url_fid = extract_drive_file_id(entry.get("drive_url", ""))
    if drive_url_fid:
        return DRIVE_VIEW.format(fid=drive_url_fid)
    if entry.get("drive_file_id"):
        return DRIVE_VIEW.format(fid=entry["drive_file_id"])
    return None


def make_filename(entry: dict, eid: str, pdf_path: Path | None,
                  existing: dict | None) -> str:
    """Keep stable filenames when only metadata is rebuilt."""
    if pdf_path:
        return pdf_path.name
    if entry.get("file"):
        return entry["file"]
    if existing and existing.get("filename"):
        return existing["filename"]
    return f"{entry.get('title', eid)}.pdf"


def discover() -> None:
    """Append catNNN stubs for PDFs not already covered by sources.json."""
    RAW_DIR.mkdir(exist_ok=True)
    sources = json.loads(SOURCES.read_text(encoding="utf-8")) if SOURCES.exists() else []

    covered: set[str] = set()
    next_id_num = int(next_catalog_id(sources)[3:])
    for e in sources:
        p = find_pdf(e)
        if p:
            covered.add(p.name)

    added = 0
    for pdf in sorted(RAW_DIR.glob("*.pdf")):
        if pdf.name in covered:
            continue
        stem = pdf.stem
        eid = f"cat{next_id_num:03d}"
        next_id_num += 1
        sources.append({
            "id": eid,
            "file": pdf.name,
            "drive_url": "",
            "drive_file_id": "",   # legacy fallback; prefer drive_url
            "icon": "fa-file-lines",
            "org": "",
            "title": stem,
            "desc": "",
            "tags": [],
            "year": "",
        })
        added += 1
        print(f"  + discovered {pdf.name}  ->  id={eid}")

    SOURCES.write_text(
        json.dumps(sources, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"discover: added {added} new entr{'y' if added == 1 else 'ies'} "
          f"to {SOURCES.name} (total {len(sources)})")


def build(use_ocr: bool, do_download: bool, refresh_ids: set[str],
          refresh_all_content: bool, allow_clear_content: bool) -> tuple[list[dict], list[str]]:
    """Build the index while preserving existing extracted content by default."""
    sources = json.loads(SOURCES.read_text(encoding="utf-8"))
    RAW_DIR.mkdir(exist_ok=True)
    existing_index = load_existing_index()
    existing_by_id = {
        item.get("id"): item
        for item in existing_index
        if item.get("id")
    }
    source_ids = {
        entry.get("id") or entry.get("drive_file_id") or entry.get("title")
        for entry in sources
    }
    removed_ids = sorted(set(existing_by_id) - source_ids)
    if removed_ids:
        print(f"removed IDs not present in {SOURCES.name}: {', '.join(removed_ids)}")

    missing_refresh_ids = sorted(refresh_ids - source_ids)
    for eid in missing_refresh_ids:
        print(f"WARNING: --refresh-content {eid} is not present in {SOURCES.name}",
              file=sys.stderr)

    index = []

    for entry in sources:
        eid = entry.get("id") or entry.get("drive_file_id") or entry.get("title")
        existing = existing_by_id.get(eid)
        is_existing = existing is not None
        print(f"[{eid}] {entry.get('title', '')}")

        pdf_path = find_pdf(entry)
        if pdf_path is None and do_download and entry.get("drive_file_id"):
            dest = RAW_DIR / f"{entry['drive_file_id']}.pdf"
            print(f"    downloading {entry['drive_file_id']} ...")
            if download_from_drive(entry["drive_file_id"], dest):
                pdf_path = dest

        filename = make_filename(entry, eid, pdf_path, existing)

        pdf_hash = existing.get("pdf_hash") if existing else None
        if pdf_path:
            pdf_hash = file_sha256(pdf_path)
            old_hash = existing.get("pdf_hash") if existing else None
            if old_hash and old_hash != pdf_hash:
                print(f"WARNING: [{eid}] local PDF hash changed; preserving existing content "
                      "until explicit refresh", file=sys.stderr)

        content = existing.get("content", "") if existing else ""
        content_tokens = existing.get("content_tokens", "") if existing else ""
        # Existing entries refresh only when explicitly requested.
        should_refresh = refresh_all_content or eid in refresh_ids or (not is_existing and pdf_path)

        if should_refresh and pdf_path:
            content = extract_text(pdf_path, use_ocr).strip()
            content_tokens = make_content_tokens(entry, filename, content)
            print(f"    extracted {len(content)} chars")
            if existing and not allow_clear_content:
                old_content = existing.get("content", "")
                old_tokens = existing.get("content_tokens", "")
                if old_content and not content:
                    content = old_content
                    content_tokens = old_tokens
                    print(f"WARNING: [{eid}] extraction returned empty content; preserved "
                          "existing content (use --allow-clear-content to clear)",
                          file=sys.stderr)
                elif old_tokens and not content_tokens:
                    content_tokens = old_tokens
                    print(f"WARNING: [{eid}] tokenization returned empty content_tokens; "
                          "preserved existing tokens (use --allow-clear-content to clear)",
                          file=sys.stderr)
        elif should_refresh:
            print("WARNING: no local PDF — metadata-only entry "
                  "(วาง PDF ใน catalog/raw/ แล้ว rebuild)", file=sys.stderr)
            if not existing:
                content_tokens = make_content_tokens(entry, filename, content)
        else:
            if is_existing:
                print("    preserved existing content")
            else:
                print("WARNING: no local PDF — metadata-only entry "
                      "(วาง PDF ใน catalog/raw/ แล้ว rebuild)", file=sys.stderr)
                content_tokens = make_content_tokens(entry, filename, content)

        item = {
            "id": eid,
            "icon": entry.get("icon", "fa-file-lines"),
            "org": entry.get("org", ""),
            "filename": filename,
            "title": entry.get("title", ""),
            "desc": entry.get("desc", ""),
            "tags": entry.get("tags", []),
            "year": entry.get("year"),
            "starred": entry.get("starred", False),
            "url": make_url(entry),
            "content": content,
            "content_tokens": content_tokens,
        }
        if pdf_hash:
            item["pdf_hash"] = pdf_hash
        index.append(item)

    return index, removed_ids


def print_summary(index: list[dict], strict: bool) -> int:
    """Print build status and return the strict-mode exit code."""
    no_url = [it for it in index if not it.get("url")]
    no_org = [it for it in index if not it.get("org")]
    no_content = [it for it in index if not it.get("content")]

    print("\n── สรุปสถานะ ──────────────────────────────────────")
    print(f"  รวม: {len(index)} entry")

    if no_url:
        print(f"\n  ⚠  ปุ่ม 'เปิดเอกสาร PDF' ใช้ไม่ได้ ({len(no_url)} entry) — ต้องเติม drive_url, drive_file_id หรือ url:")
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


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Build the Catalog search index.")
    parser.add_argument("--no-ocr", action="store_true",
                        help="ข้าม OCR แม้ PDF จะเป็นรูปภาพ")
    parser.add_argument("--download", action="store_true",
                        help="ลองดาวน์โหลดไฟล์ Drive สาธารณะลง raw/ อัตโนมัติ")
    parser.add_argument("--refresh-content", action="append", default=[],
                        metavar="ID",
                        help="extract content ใหม่เฉพาะ ID นี้ (ใช้ซ้ำได้หลายครั้ง)")
    parser.add_argument("--refresh-all-content", action="store_true",
                        help="extract content ใหม่ทุก entry ที่มี local PDF")
    parser.add_argument("--allow-clear-content", action="store_true",
                        help="อนุญาตให้ refresh ทับ content/content_tokens เดิมด้วยค่าว่าง")
    parser.add_argument("--discover", action="store_true",
                        help="สแกน raw/*.pdf เติม stub entry ลง sources.json แล้ว build")
    parser.add_argument("--strict", action="store_true",
                        help="exit code 1 ถ้ามี entry ที่ปุ่ม PDF ใช้ไม่ได้ (ใช้ก่อน commit)")
    args = parser.parse_args()

    if args.discover:
        discover()

    if not SOURCES.exists():
        sys.exit(f"missing {SOURCES} — สร้างไฟล์นี้ก่อน (หรือรัน --discover)")

    index, removed_ids = build(
        use_ocr=not args.no_ocr,
        do_download=args.download,
        refresh_ids=set(args.refresh_content),
        refresh_all_content=args.refresh_all_content,
        allow_clear_content=args.allow_clear_content,
    )
    OUTPUT.write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"\nwrote {OUTPUT}  ({len(index)} entries)")
    if removed_ids:
        print(f"removed from {OUTPUT.name}: {', '.join(removed_ids)}")

    exit_code = print_summary(index, strict=args.strict)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
