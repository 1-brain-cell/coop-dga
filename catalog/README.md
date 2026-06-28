# Catalog คู่มือเพิ่มและแก้ผลงาน

## Overview

แท็บ **Catalog** ใน `day5.html` ใช้ค้นหาผลงานผู้เรียนเก่า โดยค้นจาก filename, metadata และเนื้อหา PDF ที่ถูก index ไว้ล่วงหน้า

ระบบนี้ไม่มี backend หน้าเว็บโหลดข้อมูลจาก `catalog/catalog-index.json` โดยตรง

## Quick Rules

- แก้ metadata ที่ `catalog/sources.json` ไม่แก้ `catalog/catalog-index.json` ตรง ๆ
- เมื่อมีการแก้ที่เกี่ยวข้อง ให้ commit `catalog/sources.json`, `catalog/catalog-index.json`, `catalog/build_index.py` และ `catalog/README.md` ตามจริง
- ห้าม commit `catalog/raw/`
- `catalog/raw/` เป็น input ชั่วคราวสำหรับ extract PDF เท่านั้น
- หลัง content ถูก index แล้ว PDF เก่าใน `raw/` สามารถลบออกได้
- `id` เป็น primary key ห้ามเปลี่ยนแบบ casual edit

## Pipeline

```text
raw PDFs + sources.json -> build_index.py -> catalog-index.json -> day5.html
```

| Path | หน้าที่ | Commit? |
|---|---|---|
| `sources.json` | source of truth สำหรับ metadata ที่แก้มือ | yes |
| `build_index.py` | สคริปต์สร้าง index | commit เฉพาะเมื่อแก้ script |
| `catalog-index.json` | generated index ที่ `day5.html` โหลดไปค้น | yes |
| `raw/` | PDF ชั่วคราวสำหรับ extract ตอน build | no |
| `_archive/` | helper เก่าเก็บไว้อ้างอิง | no |

## Add A New Catalog Entry

1. วาง PDF ใหม่ใน `catalog/raw/`
2. รัน:

```bash
python catalog/build_index.py --discover
```

3. เปิด `catalog/sources.json` แล้วเติม entry ใหม่:

- `drive_url`
- `org`
- `title`
- `desc`
- `tags`
- `year`

4. รัน strict build:

```bash
python catalog/build_index.py --strict
```

5. Commit `catalog/sources.json` และ `catalog/catalog-index.json`
6. ห้าม commit `catalog/raw/`
7. หลัง index แล้ว PDF ใน `raw/` สามารถลบออกได้

## Edit Existing Metadata

1. แก้ metadata ใน `catalog/sources.json`
2. รัน:

```bash
python catalog/build_index.py --strict
```

3. Commit `catalog/sources.json` และ `catalog/catalog-index.json`

Normal build จะ preserve `content`, `content_tokens` และ `pdf_hash` ของ entry เดิม จึงใช้ได้กับงานแก้ metadata ทั่วไป

## Preserve-Safe Build Behavior

Normal build มีพฤติกรรมแบบ preserve-safe:

- โหลด `catalog-index.json` เดิมเป็น baseline
- Entry เดิมเก็บ `content`, `content_tokens` และ `pdf_hash` เดิมไว้
- PDF ของ entry เดิมไม่ถูก re-extract โดย default
- Entry ใหม่ที่มี local PDF จะถูก extract
- Entry ใหม่ที่ไม่มี local PDF จะเป็น metadata-only entry
- ID ที่ถูกลบจาก `sources.json` จะถูกลบจาก generated index
- ถ้า `pdf_hash` เปลี่ยน จะเตือนเท่านั้น ไม่ refresh content อัตโนมัติ

## Refresh Content

ใช้ refresh เฉพาะเมื่อต้องการอ่าน PDF ใหม่จริง ๆ ไม่ต้องใช้กับการแก้ metadata ปกติ

```bash
python catalog/build_index.py --refresh-content <id> --strict
python catalog/build_index.py --refresh-all-content --strict
```

ถ้า refresh แล้ว extraction ได้ค่าว่าง แต่ entry เดิมมี content อยู่ สคริปต์จะ preserve ค่าเดิมไว้

ใช้ flag นี้เฉพาะเมื่อยอมรับได้ว่าจะล้าง content เดิม:

```bash
python catalog/build_index.py --refresh-content <id> --allow-clear-content --strict
```

ถ้าต้องการข้าม OCR:

```bash
python catalog/build_index.py --no-ocr --strict
```

## Entry Structure

ตัวอย่าง entry ใน `catalog/sources.json`:

```json
{
  "id": "cat035",
  "file": "ชื่อไฟล์.pdf",
  "drive_url": "https://drive.google.com/file/d/1AbCdEfGhIjK/view?usp=sharing",
  "drive_file_id": "",
  "icon": "fa-chart-line",
  "org": "ชื่อหน่วยงาน",
  "title": "ชื่อผลงาน",
  "desc": "คำอธิบายสั้น ๆ",
  "tags": ["Tag1", "Tag2"],
  "year": 2568
}
```

| Field | Required? | หมายเหตุ |
|---|---|---|
| `id` | yes | primary key รูปแบบ `catNNN` |
| `file` | recommended | ชื่อ PDF ใน `raw/` สำหรับ extract |
| `drive_url` | recommended | URL แชร์ Drive แบบเต็ม เป็น input ปกติสำหรับ link ปุ่ม PDF |
| `drive_file_id` | optional | fallback หรือ legacy field |
| `icon` | optional | Font Awesome class เช่น `fa-chart-line` |
| `org` | yes | ชื่อหน่วยงาน ใช้ค้นหา |
| `title` | yes | ชื่อผลงาน |
| `desc` | optional | คำอธิบาย ช่วยให้ค้นเจอมากขึ้น |
| `tags` | optional | array ของ tag |
| `year` | yes | ปี พ.ศ. เช่น `2568` |
| `url` | optional | override โดยตรง ถ้ามีจะชนะ `drive_url` และ `drive_file_id` |

URL priority ตอน build:

1. `url` ใช้เป็น override
2. `drive_url` เป็น input ปกติ
3. `drive_file_id` ยังรองรับเป็น fallback หรือ legacy

ถ้าไม่มีทั้ง `url`, `drive_url` และ `drive_file_id` ปุ่ม "เปิดเอกสาร PDF" จะใช้งานไม่ได้

## ID Policy

- `id` เป็น primary key ที่ใช้จับคู่ `sources.json` กับ `catalog-index.json`
- รูปแบบ ID คือ `catNNN` เช่น `cat001`, `cat002`, `cat035`
- Entry ใหม่ใช้เลขถัดไปจาก ID สูงสุดที่มีอยู่
- การเปลี่ยน ID ต้องเป็น deliberate migration ที่อัปเดตทั้ง `sources.json` และ `catalog-index.json`
- การแก้ metadata ปกติไม่ควรเปลี่ยน `id`

## Troubleshooting

| ปัญหา | สาเหตุ | วิธีแก้ |
|---|---|---|
| ปุ่ม PDF ใช้ไม่ได้ | ไม่มี `url`, `drive_url` หรือ `drive_file_id` | เติม `drive_url` แล้วรัน strict build |
| ค้นชื่อหน่วยงานไม่เจอ | `org` ว่างหรือสะกดผิด | แก้ `org` ใน `sources.json` แล้วรัน strict build |
| ค้นเนื้อหาไฟล์ใหม่ไม่เจอ | ไม่มี PDF ใน `raw/` หรือ extract ไม่ได้ | วาง PDF ใน `raw/` แล้วรัน strict build |
| ต้องการอ่าน PDF ใหม่ | build ปกติ preserve content เดิม | ใช้ `--refresh-content <id>` |
| `pdf_hash` เปลี่ยน | local PDF เปลี่ยนจาก baseline | ตรวจ PDF แล้ว refresh เฉพาะเมื่อจำเป็น |
| Catalog ไม่โหลด | เปิดผ่าน `file://` | เปิดผ่าน local web server |

## Build Modes

Common:

```bash
python catalog/build_index.py
python catalog/build_index.py --discover
python catalog/build_index.py --strict
```

Advanced:

```bash
python catalog/build_index.py --download
python catalog/build_index.py --refresh-content <id>
python catalog/build_index.py --refresh-all-content
python catalog/build_index.py --allow-clear-content
python catalog/build_index.py --no-ocr
```

## Dependencies

Dependencies เป็น optional สคริปต์ยังรันได้แม้ติดตั้งไม่ครบ

```bash
pip install pypdf pdfplumber pythainlp
pip install pdf2image pytesseract pillow
```

สำหรับ OCR ต้องมี Tesseract, Thai traineddata และ poppler ในเครื่องด้วย

## Run The Local Web Server

จาก project root:

```bash
python -m http.server 8000
```

เปิด:

```text
http://localhost:8000/day5.html
```

แล้วไปที่แท็บ Catalog หรือใช้ live server extension ก็ได้

## Review Policy And Design Notes

- ใช้ custom substring matcher แทน FlexSearch เพราะภาษาไทยไม่มีช่องว่างระหว่างคำ และต้องการให้ substring match ทำงานได้
- `sources.json` เป็น source of truth ห้ามกลับไป hardcode card ใน HTML
- Dependencies เป็น optional เพื่อให้ contributor build ได้แม้เครื่องไม่พร้อมครบ
- Search weights: `org`, `title`, `filename`, `tags` = 3, `desc` = 2, `content` = 1
- หลายคำค้นใช้ AND behavior
