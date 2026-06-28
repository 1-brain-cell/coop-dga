# Catalog — คู่มือเพิ่มและแก้ผลงาน

ระบบค้นหาผลงานผู้เรียนเก่าในแท็บ **Catalog** ของ `day5.html`
ค้นได้จาก **ชื่อไฟล์ / เนื้อหาภายในไฟล์ / ชื่อหน่วยงาน** โดยไม่ต้องมี backend

## Pipeline

```
raw/*.pdf  +  sources.json   ──build_index.py──►  catalog-index.json   ──►  day5.html
 (PDF ต้นฉบับ)  (source of truth)   (สร้าง index)      (เว็บโหลดไปค้น)
```

| ไฟล์/โฟลเดอร์ | หน้าที่ | ต้อง commit? |
|---|---|---|
| `sources.json` | รายการผลงาน — **แก้ที่นี่** | ✓ |
| `build_index.py` | สคริปต์สร้าง index | ✓ |
| `catalog-index.json` | index ที่เว็บโหลด (generate อัตโนมัติ) | ✓ |
| `raw/` | PDF ต้นฉบับ (build input เท่านั้น) | ✗ |
| `_archive/` | สคริปต์ helper เก่า ไว้อ้างอิง | ✗ |

> **กฎเหล็ก:** แก้ข้อมูลที่ `sources.json` เสมอ — ห้ามแก้ `catalog-index.json` ตรง ๆ เพราะมันถูก generate จาก `sources.json`

## Preserve-safe build workflow

`sources.json` เป็น source of truth สำหรับ metadata ที่แก้มือได้ ส่วน `catalog-index.json` เป็น generated search index ที่เก็บ `content` และ `content_tokens` จาก PDF ด้วย

Build ปกติเป็นแบบ preserve-safe:

```bash
python build_index.py --strict
```

พฤติกรรมของ build ปกติ:

- โหลด `catalog-index.json` เดิมเป็น baseline
- อัปเดต metadata จาก `sources.json`
- เก็บ `content` และ `content_tokens` เดิมของ entry ที่มีอยู่แล้ว
- ไม่ extract PDF ซ้ำสำหรับ entry เดิม
- extract content เฉพาะ entry ใหม่ที่มี PDF ใน `raw/`
- ถ้า entry ใหม่ไม่มี PDF จะสร้าง metadata-only entry และเตือน
- ถ้า ID ถูกลบออกจาก `sources.json` จะถูกลบจาก `catalog-index.json` และรายงานท้าย build
- เพิ่ม `pdf_hash` ให้ entry ที่มี local PDF
- ถ้า `pdf_hash` เปลี่ยน จะเตือนเท่านั้น ไม่ refresh หรือ clear content อัตโนมัติ

เมื่อต้องการ refresh เนื้อหา PDF ให้ทำแบบชัดเจน:

```bash
python build_index.py --refresh-content unique-kebab-id --strict
python build_index.py --refresh-all-content --strict
```

ถ้า refresh แล้ว extraction ได้ค่าว่าง แต่ entry เดิมมี `content` หรือ `content_tokens` อยู่ สคริปต์จะ preserve ค่าเดิมไว้ เพื่อไม่ให้ OCR-derived content หายโดยไม่ตั้งใจ

ใช้ flag นี้เฉพาะเมื่อยอมรับได้จริง ๆ ว่าจะล้าง content เดิม:

```bash
python build_index.py --refresh-content unique-kebab-id --allow-clear-content --strict
```

---

## เพิ่มผลงานใหม่ (checklist)

```
1. วาง PDF ลง catalog/raw/
   └─ ตั้งแชร์ Drive เป็น "anyone with the link" ก่อน

2. python build_index.py --discover
   └─ สร้าง stub entry ใน sources.json (title เดาจากชื่อไฟล์)

3. เปิด sources.json แก้ entry ใหม่:
   └─ drive_file_id  ← เอา ID จาก URL Drive: .../d/<ID>/view
   └─ org            ← ชื่อหน่วยงาน (บังคับ)
   └─ title          ← ชื่อผลงานที่อ่านแล้วเข้าใจ
   └─ desc, tags     ← optional แต่ช่วยให้ค้นเจอ

4. python build_index.py --strict
   └─ build แบบ preserve-safe + extract เฉพาะ entry ใหม่ + ตรวจว่าครบ

5. commit: sources.json + catalog-index.json
   └─ ห้าม commit raw/
```

---

## โครงสร้าง entry ใน `sources.json`

```json
{
  "id": "unique-kebab-id",
  "file": "ชื่อไฟล์.pdf",
  "drive_file_id": "1AbCdEfGhIjK...",
  "icon": "fa-chart-line",
  "org": "ชื่อหน่วยงาน",
  "title": "ชื่อผลงาน",
  "desc": "คำอธิบายสั้น ๆ",
  "tags": ["Tag1", "Tag2"],
  "year": 2568
}
```

| Field | บังคับ? | หมายเหตุ |
|---|---|---|
| `id` | ✓ | ต้องไม่ซ้ำ, kebab-case, `--discover` สร้างให้อัตโนมัติ |
| `drive_file_id` | ✓* | เอาจาก URL: `drive.google.com/file/d/**<ID>**/view` |
| `org` | ✓ | ชื่อหน่วยงาน — ใช้ค้นหาด้วยชื่อหน่วยงาน |
| `title` | ✓ | ชื่อผลงาน |
| `year` | ✓ | ปี พ.ศ. ที่ผลิตผลงาน เช่น `2568` — แสดงใน card และใช้กับ filter chip; chip ปีจะขึ้นอัตโนมัติเมื่อมีข้อมูล ถ้าอยากให้ chip ขึ้นล่วงหน้าก่อนมีข้อมูล ให้เพิ่มเลขปีเข้าไปใน `KNOWN_YEARS` ใน `day5.html` |
| `file` | แนะนำ | ชื่อ PDF ใน `raw/` — ถ้าไม่มีจะค้นได้แค่ metadata |
| `desc` | optional | คำอธิบาย — ช่วยค้นเจอมากขึ้น |
| `tags` | optional | array ของ tag เช่น `["Health", "Statistics"]` |
| `icon` | optional | Font Awesome class เช่น `fa-chart-line`, `fa-leaf` |
| `url` | optional | ใส่เองถ้าไม่ใช่ Drive, ไม่ใส่ก็สร้างจาก drive_file_id |

*ถ้าไม่มี `drive_file_id` และไม่มี `url` ปุ่ม "เปิดเอกสาร PDF" จะกดไม่ได้

---

## แก้ข้อมูลที่ผิด (เช่น org ผิด)

1. เปิด `sources.json` หา entry ตาม `id` หรือ `file`
2. แก้ค่าที่ต้องการ
3. `python build_index.py --strict`
4. commit `sources.json` + `catalog-index.json`

---

## Troubleshooting

| ปัญหา | สาเหตุ | วิธีแก้ |
|---|---|---|
| ปุ่ม "เปิดเอกสาร PDF" กดไม่ได้ | `drive_file_id` ว่างหรือไม่มี `url` | เติม `drive_file_id` ใน `sources.json` แล้ว rebuild |
| ค้นชื่อหน่วยงานไม่เจอ | `org` ว่าง | เติม `org` ใน `sources.json` แล้ว rebuild |
| ค้นเนื้อหาในไฟล์ไม่ได้สำหรับ entry ใหม่ | ไม่มี PDF ใน `raw/` หรือเป็นสไลด์รูปภาพ | วาง PDF ลง `raw/` แล้ว rebuild (ถ้าเป็นรูปภาพต้องติดตั้ง OCR ก่อน) |
| ต้องการอ่าน PDF ใหม่สำหรับ entry เดิม | build ปกติ preserve `content` เดิม | ใช้ `--refresh-content <id>` หรือ `--refresh-all-content` |
| `pdf_hash` เปลี่ยน | local PDF เปลี่ยนจาก baseline | ตรวจว่า PDF ถูกต้อง แล้วใช้ `--refresh-content <id>` ถ้าต้องการ update content |
| เปิดเว็บแล้ว Catalog ไม่โหลด | เปิดผ่าน `file://` | ต้องเปิดผ่าน HTTP: `python -m http.server 8000` |

---

## โหมดของ `build_index.py`

```bash
python build_index.py                  # build ปกติ
python build_index.py --discover       # เติม stub entry จาก raw/*.pdf
python build_index.py --link-drive     # เติม drive_file_id จาก google_drive_links.json
python build_index.py --strict         # build + exit code 1 ถ้า URL ไม่ครบ
python build_index.py --download       # ลองดาวน์โหลด PDF จาก Drive อัตโนมัติ
python build_index.py --refresh-content <id>      # extract content ใหม่เฉพาะ ID
python build_index.py --refresh-all-content       # extract content ใหม่ทุก entry ที่มี PDF
python build_index.py --allow-clear-content       # อนุญาตให้ refresh ล้าง content เดิมถ้า extract ได้ค่าว่าง
python build_index.py --no-ocr         # ข้าม OCR
```

## Dependencies (ติดตั้งตามต้องการ)

```bash
pip install pypdf pdfplumber pythainlp      # ดึงข้อความ PDF + ตัดคำไทย
pip install pdf2image pytesseract pillow     # OCR สำหรับสไลด์ที่เป็นรูปภาพ
```

OCR ต้องมีโปรแกรม **Tesseract** + ชุดภาษาไทย (`tha`) และ **poppler** ติดตั้งในเครื่องด้วย

---

## รันเว็บเพื่อทดสอบ

```bash
# จากโฟลเดอร์ dga306_2026_interactive_guide
python -m http.server 8000
# เปิด http://localhost:8000/day5.html → แท็บ Catalog
```

---

## เบื้องหลัง — การตัดสินใจสำคัญ (อย่ารื้อโดยไม่มีเหตุผล)

1. **ใช้ custom substring matcher แทน FlexSearch** — ภาษาไทยไม่มีช่องว่างระหว่างคำ ต้องค้นแบบ substring (`ขยะ` เจอใน `ขยะมูลฝอย`) ถ้าจะเปลี่ยนไลบรารีต้องมั่นใจว่ารองรับ Thai substring
2. **`sources.json` เป็น source of truth** — ห้ามกลับไป hardcode การ์ดใน HTML
3. **ทุก dependency เป็น optional** — สคริปต์ยังรันได้แม้ไม่มี lib ครบ (ข้าม + เตือน)
4. **ถ่วงน้ำหนักค้นหา:** org/title/filename/tags = 3, desc = 2, content = 1; หลายคำเป็น AND
