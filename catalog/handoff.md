# Handoff — ระบบค้นหา Catalog (day5.html)

> เอกสารส่งต่องาน เขียนให้ **agent ใหม่ (Sonnet 4.6 / Gemini / อื่น ๆ)** อ่านแล้วทำต่อได้ทันทีโดยไม่ต้องมี context เดิม คำสั่งทั้งหมดเป็น **provider-neutral** (ไม่ผูกกับเครื่องมือเฉพาะของ Claude)

## วิธีเริ่ม (อ่าน 4 ไฟล์นี้ก่อน)
1. ไฟล์นี้ (`catalog/handoff.md`) — ภาพรวม + งานที่เหลือ
2. `catalog/build_index.py` — สคริปต์สร้าง index (อ่านให้เข้าใจ flow)
3. `catalog/sources.json` — รายการผลงาน (source of truth)
4. `day5.html` — ดูแท็บ `#tab-catalog` + JS module `CatalogSearch` (ค้นหาฝั่ง client)

ทุกคำสั่งรันใน PowerShell บน Windows ที่โฟลเดอร์:
`c:\Users\User\Code\DGA306_ac\dga306_2026_interactive_guide\catalog`

---

## เป้าหมายของงาน
แท็บ **Catalog** ใน `day5.html` เก็บผลงานนำเสนอของผู้เรียนรุ่นก่อน (PDF บน Google Drive)
ต้องการให้ **ค้นหาด้วย keyword จาก: (1) ชื่อไฟล์ (2) เนื้อหาภายในไฟล์ (3) ชื่อหน่วยงาน**
ข้อจำกัด: เว็บเป็น **static site** (ไม่มี backend), ไฟล์อยู่บน **Google Drive**, ผู้ใช้สื่อสารภาษาไทย

แผนเต็ม (เผื่ออ่านลึก): `C:\Users\User\.claude\plans\rag-catalog-sleepy-scott.md`

## สถาปัตยกรรม (3 Tier ใช้ build-time index ร่วมกัน)
- **Tier 1 — Keyword/full-text (โครงเสร็จแล้ว กำลังเก็บงาน metadata):** build-time pipeline ดึงข้อความจาก PDF → `catalog-index.json` → browser ค้น client-side ฟรี ไม่ต้องมี backend/API key
- **Tier 2 — Semantic (ยังไม่ทำ):** embedding ตอน build + transformers.js ใน browser (ยัง static)
- **Tier 3 — RAG ถาม-ตอบ (ยังไม่ทำ):** ต้องมี serverless + LLM API

---

## สถานะปัจจุบัน (ตรวจสอบล่าสุด)
- `sources.json`: **37 รายการ** (2 seed เดิม + 35 ที่ `--discover` เติมจาก `raw/`)
- `raw/`: มี PDF จริง **35 ไฟล์** (ไม่ push ขึ้น git — อยู่ใน `.gitignore` แล้ว)
- `catalog-index.json`: **37 entry**, **32 มี content แล้ว** (pypdf ทำงาน), **5 ว่าง**:
  - `agri-burn-pm25`, `pollution-waste` = seed เดิมที่ยังไม่มี PDF ใน `raw/` (มี `drive_file_id` แล้ว)
  - `data-visualization-laddawan-yeadyad`, `dds-benjaporn-ping`, `supaporn-wongniyom` = น่าจะเป็นสไลด์ภาพ → ต้อง **OCR** ถึงจะได้เนื้อหา
- **`drive_file_id` เติมแล้วเพียง 2/37** → ปุ่ม "เปิดเอกสาร PDF" ของอีก 35 ชิ้น **ยังกดไม่ได้** (url เป็น `#`)
- มีไฟล์ช่วย: **`google_drive_links.json`** / **`.md`** = แมป `ชื่อไฟล์ → Drive URL` ของทั้ง 35 ไฟล์ (ใช้เติม `drive_file_id` ได้)

### ไฟล์ในโฟลเดอร์ `catalog/`
| ไฟล์ | สถานะ | หมายเหตุ |
|---|---|---|
| `sources.json` | 37 รายการ, metadata ยังไม่ครบ | source of truth — แก้ไฟล์นี้แล้ว rebuild |
| `build_index.py` | เสร็จ | pipeline + โหมด `--discover`, `--download`, `--no-ocr` |
| `catalog-index.json` | generate แล้ว | **ไฟล์ที่เว็บโหลดไปค้น — ต้อง commit** |
| `google_drive_links.json` / `.md` | มีครบ 35 | ไฟล์ช่วยเติม `drive_file_id` (อาจ gitignore ได้ ไม่ใช่ของที่เว็บใช้) |
| `raw/` | 35 PDF | build input — **อยู่ใน .gitignore** ไม่ push |
| `README.md` | เสร็จ | คู่มือใช้งาน |

---

## งานที่ต้องทำต่อ (เรียงลำดับ)

### Task A — เติม `drive_file_id`/`url` ให้ครบ 35 ชิ้น (สำคัญสุด)
join `sources.json` (ฟิลด์ `file`) กับ `google_drive_links.json` (ฟิลด์ `name`) ด้วยชื่อไฟล์ แล้วดึง id จาก URL (`/d/<ID>/view`)
สร้างไฟล์ `catalog/merge_links.py` ตามนี้แล้วรัน `python merge_links.py`:

```python
import json, re
from pathlib import Path
HERE = Path(__file__).resolve().parent
src = json.loads((HERE/"sources.json").read_text(encoding="utf-8"))
links = json.loads((HERE/"google_drive_links.json").read_text(encoding="utf-8"))

def fid(url):
    m = re.search(r"/d/([^/]+)", url or "")
    return m.group(1) if m else ""

# แมปชื่อไฟล์ -> [id...] (เก็บเป็น list เพื่อจับชื่อซ้ำ)
by_name = {}
for l in links:
    by_name.setdefault(l["name"], []).append(fid(l["url"]))

unmatched, ambiguous = [], []
for e in src:
    if e.get("drive_file_id"):          # ไม่ทับของเดิม (seed)
        continue
    fn = e.get("file")
    if not fn:
        continue
    ids = by_name.get(fn)
    if not ids:
        unmatched.append(fn)            # ชื่อไม่ตรง (เช่นมี (1) หรืออักขระต่าง)
    elif len(ids) > 1:
        ambiguous.append(fn)            # ชื่อซ้ำหลาย URL -> ต้องเลือกมือ
    else:
        e["drive_file_id"] = ids[0]

(HERE/"sources.json").write_text(json.dumps(src, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
print("unmatched:", unmatched)
print("ambiguous:", ambiguous)
```

> ⚠️ **กับดักชื่อไฟล์** ที่ต้องแก้มือหลังรันสคริปต์:
> - ชื่อซ้ำ: `DGA306 รุ่นที่ 1 กรมทรัพยากรธรณี - Rasamee Somsat.pdf` มี 2 URL (และ `raw/` มีไฟล์ `...Somsat(1).pdf` ด้วย) → จับคู่เอง
> - อักขระถูก sanitize ตอนเซฟลงดิสก์: เช่น `raw/Farmers_ Market (1) ...` (underscore) แต่ลิงก์เป็น `Farmers' Market (1) ...` (apostrophe) → ชื่อไม่ตรง ต้องจับคู่เอง
> ดู `unmatched`/`ambiguous` ที่สคริปต์พิมพ์ออกมา แล้วเติม `drive_file_id` ในรายการเหล่านั้นใน `sources.json` ด้วยมือ

### Task B — เติม `org` และ `tags` (ทำให้ค้นด้วยชื่อหน่วยงานได้)
ตอนนี้ `org` ของ 35 ชิ้นว่าง → ค้นด้วยชื่อหน่วยงานยังไม่ครบ
ชื่อไฟล์ส่วนใหญ่มีรูปแบบ `<หัวข้อ/หน่วยงาน> - <ชื่อคน>.pdf` ใช้เป็น hint ได้ (เช่น `หยุดเผา กรมส่งเสริมการเกษตร - Ss Dd.pdf` → org = กรมส่งเสริมการเกษตร)
- เติม `org`, `tags`, และปรับ `title` ให้อ่านง่าย (ตอนนี้ title = ชื่อไฟล์)
- อาจใช้ LLM ช่วยเดา org/tags จาก `title`+`content` ใน `catalog-index.json` แล้วให้คนรีวิว

### Task C — OCR 3 ไฟล์ที่ content ว่าง (ถ้าต้องการให้ค้นเนื้อหาได้)
ไฟล์: `Data Visualization - Laddawan Yeadyad.pdf`, `กรมราชทัณฑ์_DDs - Benjaporn Ping.pdf`, `เจ้หงส์ - Supaporn Wongniyom.pdf`
- ติดตั้ง: โปรแกรม **Tesseract** (+ ภาษาไทย `tha`) และ **poppler**, แล้ว `pip install pdf2image pytesseract pillow`
- รัน `python build_index.py` (ไม่ใส่ `--no-ocr`) → จะ OCR เฉพาะไฟล์ที่ดึง text ปกติไม่ได้
- ถ้ายังไม่อยากยุ่งกับ OCR: ปล่อย content ว่างไว้ก็ได้ (ค้นจากชื่อ/หน่วยงานยังได้)

### Task D — rebuild + verify
```powershell
python build_index.py        # ไม่ต้องใส่ --discover แล้ว (ไฟล์เดิมมีครบ)
cd ..
python -m http.server 8000   # เปิด http://localhost:8000/day5.html แท็บ Catalog
```
ทดสอบ 3 อย่างให้ครบโจทย์:
1. ค้นชื่อหน่วยงาน → เจอการ์ดที่ตรง
2. ค้นคำที่อยู่ **ในเนื้อสไลด์** (ไม่ใช่ชื่อเรื่อง) → เจอ (พิสูจน์ค้นเนื้อหาในไฟล์)
3. กดปุ่ม "เปิดเอกสาร PDF" → เปิด Drive ได้จริง (พิสูจน์ Task A สำเร็จ)

### Task E — git
- **อย่า push `raw/`** (อยู่ใน `.gitignore` แล้ว)
- ต้อง commit: `sources.json`, `catalog-index.json`, `build_index.py`, `README.md`, `day5.html`, `.gitignore`
- `google_drive_links.json`/`.md` เป็นไฟล์ช่วย build เลือกได้ว่าจะ commit (เป็น reference) หรือ gitignore
- Drive ทุกไฟล์ต้องตั้งแชร์ "anyone with the link" ปุ่มถึงจะใช้ได้กับทุกคน

---

## การตัดสินใจสำคัญ (อย่ารื้อโดยไม่มีเหตุผล)
1. **ใช้ custom matcher แทน FlexSearch** — ภาษาไทยไม่มีช่องว่างระหว่างคำ ต้องค้นแบบ **substring** ถึงเจอ (เช่น `ขยะ` ใน `ขยะมูลฝอย`) custom matcher ใน `day5.html` รองรับทั้งกรณีตัดคำแล้ว/ยังไม่ตัด และไม่พึ่ง CDN — ถ้าจะเปลี่ยนไปใช้ไลบรารี ต้องมั่นใจว่ารองรับ Thai substring
2. **`sources.json` เป็น source of truth** (ไม่ใช่ HTML) — เพิ่ม/แก้ผลงานที่นี่แล้ว rebuild ห้ามกลับไป hardcode การ์ดใน HTML
3. **ทุก dependency เป็น optional** ใน `build_index.py` — รันได้แม้ lib ไม่ครบ (ข้าม + เตือน)
4. **โหมด `--discover`** = สแกน `raw/*.pdf` เติม stub ลง `sources.json` (ใช้ตอนเพิ่มไฟล์ใหม่)
5. matcher ถ่วงน้ำหนัก: org/title/filename/tags = strong(3), desc = medium(2), content/content_tokens = weak(1); หลายคำเป็น **AND**

## Gotchas
- **`fetch` ใช้ `file://` ไม่ได้** — ต้องเสิร์ฟผ่าน http (`python -m http.server`)
- **ต้องมี `drive_file_id`** ทุก entry ไม่งั้นปุ่มเปิด PDF เป็น `#`
- **สไลด์ภาพ** → content ว่าง ต้อง OCR
- **ไม่มี `pythainlp`** → ใช้ fallback tokenizer (คำไทยไม่ถูกตัด) ยังค้น substring ได้แต่จัดอันดับหยาบ แนะนำ `pip install pythainlp`
- **ชื่อไฟล์ซ้ำ/อักขระถูก sanitize** ตอน join links (ดู Task A)

## ทิศทาง Phase 2/3 (ถ้าจะทำต่อ)
- **Phase 2 (semantic, ยัง static):** ตอน build หั่น content เป็น chunk + คำนวณ embedding เก็บใน JSON; ตอน query ใช้ transformers.js (เช่น `paraphrase-multilingual-MiniLM`) embed คำค้น + cosine similarity ใน browser; hybrid กับ keyword เดิม
- **Phase 3 (ถาม-ตอบ):** serverless function (เก็บ API key ฝั่ง server) → retrieve chunk → ส่งให้ LLM ตอบพร้อมอ้างอิง
- หมายเหตุ provider: ถ้าใช้ embedding คุณภาพสูงฝั่ง build ดู Voyage AI; ถ้าจะคง static ล้วนใช้ transformers.js ในเครื่อง browser
