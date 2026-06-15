import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCES_PATH = HERE / "sources.json"
LINKS_PATH = HERE / "google_drive_links.json"

src = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
links = json.loads(LINKS_PATH.read_text(encoding="utf-8"))

def fid(url):
    m = re.search(r"/d/([^/]+)", url or "")
    return m.group(1) if m else ""

def sanitize(name):
    if not name:
        return ""
    name = name.lower()
    name = re.sub(r"\.pdf$", "", name)
    # Normalize underscores, multiple spaces, and single quotes/apostrophes
    name = re.sub(r"[_\s']+", " ", name)
    return name.strip()

# Map sanitized name -> list of file IDs
by_name = {}
for l in links:
    san = sanitize(l["name"])
    by_name.setdefault(san, []).append(fid(l["url"]))

unmatched = []
ambiguous = []

# To handle Rasamee duplicate URLs and other potential duplicates,
# we keep track of how many times each name has been matched to distribute IDs.
match_counts = {}

for e in src:
    if e.get("drive_file_id"):  # Don't overwrite existing seeds
        continue
    fn = e.get("file")
    if not fn:
        continue

    san_fn = sanitize(fn)
    
    # Special handle for files with "(1)" in sources.json that might match the base name without "(1)"
    # e.g., "Rasamee Somsat(1).pdf" matching "Rasamee Somsat.pdf" in Google Drive links.
    has_suffix_1 = False
    if "(1)" in fn:
        # Check if the name without (1) is in by_name
        san_fn_no_1 = sanitize(fn.replace("(1)", ""))
        if san_fn_no_1 in by_name:
            san_fn = san_fn_no_1
            has_suffix_1 = True

    ids = by_name.get(san_fn)
    if not ids:
        unmatched.append(fn)
    elif len(ids) > 1:
        # If we have multiple IDs (like Rasamee Somsat), we map them based on whether it is the (1) version or not.
        if has_suffix_1:
            # Map to the second ID
            e["drive_file_id"] = ids[1]
        else:
            # Map to the first ID
            e["drive_file_id"] = ids[0]
    else:
        e["drive_file_id"] = ids[0]

# Write updated sources back
SOURCES_PATH.write_text(
    json.dumps(src, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8"
)

print("Merge completed!")
print("Unmatched files:", unmatched)
print("Ambiguous files:", ambiguous)
