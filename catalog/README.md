# Catalog คู่มือเพิ่มและแก้ผลงาน

## Overview

หน้า `catalog.html` ใช้แสดงและค้นหาผลงาน Final Project จากไฟล์ `catalog/catalog-index.json`

**ระบบนี้ไม่มี backend หน้าเว็บไม่ได้อ่าน `catalog/sources.json` โดยตรง ดังนั้นถ้าแก้ `sources.json` แล้วไม่รัน build หน้าเว็บจะยังไม่เห็นข้อมูลใหม่**

## Must Know

- แก้ metadata ที่ `catalog/sources.json`
- ห้ามแก้ `catalog/catalog-index.json` ด้วยมือ
- หลังแก้ `sources.json` ต้องรัน:

```bash
python catalog/build_index.py --strict
```

- Commit `catalog/sources.json` และ `catalog/catalog-index.json` คู่กัน
- Commit `catalog/build_index.py` เฉพาะเมื่อแก้ script
- Commit `catalog/README.md` เฉพาะเมื่อแก้คู่มือนี้
- ไม่ต้อง commit `catalog/raw/`
- `catalog/raw/` เป็น input ชั่วคราวสำหรับ extract PDF เท่านั้น
- หลัง extract เสร็จแล้วลบ PDF ใน `catalog/raw/` ออกได้
- `id` เป็น primary key ห้ามเปลี่ยนถ้าไม่ได้ตั้งใจ migrate


## Pipeline and files
<details>
<summary>Pipeline and files</summary>

```text
raw PDFs + sources.json -> build_index.py -> catalog-index.json -> catalog.html
```

| Path | หน้าที่ | Commit? |
|---|---|---|
| `catalog/sources.json` | source of truth สำหรับ metadata | yes |
| `catalog/catalog-index.json` | generated index ที่หน้าเว็บโหลดไปค้น | yes |
| `catalog/build_index.py` | script สร้าง index | เฉพาะเมื่อแก้ script |
| `catalog/raw/` | PDF ชั่วคราวสำหรับ extract ตอน build | no |
| `catalog/_archive/` | ของเก่าเก็บไว้อ้างอิง | no |

</details>

## Add New Entries

ใช้ flow นี้เมื่อมี PDF ใหม่และทำงานในเครื่องเดียวกัน

1. สร้าง `catalog/raw/` ถ้ายังไม่มี
2. วาง PDF ใหม่ใน `catalog/raw/`
3. อย่า commit ไฟล์ใน `catalog/raw/`
4. รัน discover:

```bash
python catalog/build_index.py --discover
```

5. เปิด `catalog/sources.json` แล้วเติม metadata ใน stub entry ที่ script สร้างให้

ควรเติมอย่างน้อย:

- `drive_file_id` หรือ `drive_url`
- `org`
- `title`
- `desc`
- `tags`
- `year`

6. รัน strict build:

```bash
python catalog/build_index.py --strict
```

7. ดู summary ตอนท้าย ต้องไม่มี URL error
8. หลัง extract เสร็จแล้วลบ PDF ใน `catalog/raw/` ออกได้
9. Commit `catalog/sources.json` และ `catalog/catalog-index.json`

> [!TIP]
> ใน flow นี้ปกติไม่ต้องแก้ชื่อไฟล์เอง เพราะ `--discover` จะใส่ชื่อ PDF จริงลง field `file` ให้อัตโนมัติ

## Edit Existing Metadata

ใช้ flow นี้เมื่อแก้ชื่อเรื่อง, หน่วยงาน, description, tags, year, starred หรือ link

1. แก้ `catalog/sources.json`
2. รัน:

```bash
python catalog/build_index.py --strict
```

3. ตรวจ summary
4. Commit `catalog/sources.json` และ `catalog/catalog-index.json`

> [!NOTE]
> Build ปกติจะ preserve `content`, `content_tokens` และ `pdf_hash` ของ entry เดิม จึงใช้กับงานแก้ metadata ได้

## If sources.json Was Committed Without Rebuild

ใช้เคสนี้เมื่อมีคนแก้หรือ commit `sources.json` มาแล้ว แต่ยังไม่ได้รัน build หรือย้ายมาทำบนเครื่องใหม่แล้ว `catalog-index.json` ยังไม่ตรงกับ `sources.json`

1. ตรวจว่า `catalog/sources.json` มี entry ที่ต้องการแล้ว
2. ถ้าต้องการ extract content จาก PDF ใหม่ ให้วาง PDF ใน `catalog/raw/`
3. เช็คชื่อไฟล์ตามหัวข้อ Raw PDF Matching
4. รัน:

```bash
python catalog/build_index.py --strict
```

> [!NOTE]
> ถ้าไม่มี PDF ใน `raw/` หรือชื่อไม่ match entry ใหม่จะยังถูกเขียนเข้า `catalog-index.json` ได้ แต่จะเป็น metadata-only และค้นเนื้อหาใน PDF ไม่ได้

## Raw PDF Matching

> [!TIP]
> ถ้าเพิ่ม PDF ด้วย `--discover` ในเครื่องเดียวกัน ปกติไม่ต้องเช็คชื่อไฟล์เอง เพราะ script จะใส่ชื่อ PDF จริงลง `file` ให้อัตโนมัติ

ต้องเช็คชื่อไฟล์เองเฉพาะตอน rebuild จาก `sources.json` ที่มีอยู่แล้ว เช่น มีคน commit metadata มาแต่ยังไม่ได้ build index, ย้ายเครื่อง, copy PDF เข้ามาทีหลัง หรือ download raw file แล้วชื่อไม่ตรง

ตอน build script จะหา PDF จากชื่อเหล่านี้:

1. `catalog/raw/<file>`
2. `catalog/raw/<id>.pdf`
3. `catalog/raw/<drive_file_id>.pdf`

<details>
<summary>What happens if the file does not match</summary>

> [!NOTE]
> ถ้าไม่ตรงกับสามแบบนี้ entry จะยังเข้า index ได้ แต่จะเป็น metadata-only

> [!NOTE]
> `pdf_hash` ไม่ได้ใช้จับคู่ PDF กับ entry มันถูกใช้หลังจากหา PDF เจอแล้ว เพื่อเตือนว่าไฟล์เปลี่ยนจาก baseline เดิม

</details>

## Refresh One Entry

ใช้เมื่อต้องการ extract content ใหม่เฉพาะ entry เดิม

ก่อน refresh ให้เช็คว่า PDF อยู่ใน `catalog/raw/` และชื่อ match rule ด้านบน

ตัวอย่าง:

```bash
python catalog/build_index.py --refresh-content cat037 --strict
```

> [!NOTE]
> ถ้า refresh แล้ว extraction ได้ค่าว่าง แต่ entry เดิมมี content อยู่ script จะ preserve content เดิมไว้

ใช้ flag นี้เฉพาะเมื่อยอมรับได้ว่าจะล้าง content เดิม:

```bash
python catalog/build_index.py --refresh-content cat037 --allow-clear-content --strict
```

## Download From Drive

ใช้เมื่อ entry มี `drive_file_id` และต้องการให้ script ลอง download PDF เข้า `catalog/raw/`

```bash
python catalog/build_index.py --download --strict
```

<details>
<summary>Download notes</summary>

> [!NOTE]
> `--download` ใช้ `drive_file_id` และใช้ได้กับไฟล์ Drive ที่เข้าถึงได้จริง ถ้า Drive ตอบกลับเป็นหน้า HTML หรือไฟล์ private script จะ download ไม่สำเร็จ

> [!TIP]
> PDF ที่ download ลง `catalog/raw/` ไม่ต้อง commit

</details>

## Entry Fields

<details>
<summary>Field reference</summary>

ตัวอย่าง entry ใน `catalog/sources.json`:

```json
{
  "id": "cat035",
  "file": "ชื่อไฟล์.pdf",
  "drive_file_id": "1AbCdEfGhIjK",
  "drive_url": "",
  "icon": "fa-file-lines",
  "org": "ชื่อหน่วยงาน",
  "title": "ชื่อผลงาน",
  "desc": "คำอธิบายสั้น ๆ",
  "tags": ["Tag1", "Tag2"],
  "year": 2569,
  "starred": true
}
```

| Field | Required? | หมายเหตุ |
|---|---|---|
| `id` | yes | primary key รูปแบบ `catNNN` |
| `file` | recommended | ชื่อ PDF ใน `raw/` สำหรับ extract |
| `drive_file_id` | recommended | ใช้สร้าง URL และใช้กับ `--download` |
| `drive_url` | optional | URL แชร์ Drive แบบเต็ม |
| `url` | optional | override link โดยตรง |
| `icon` | optional | Font Awesome class เช่น `fa-file-lines` |
| `org` | yes | ชื่อหน่วยงาน ใช้ค้นหา |
| `title` | yes | ชื่อผลงาน |
| `desc` | recommended | คำอธิบายสั้น ๆ ช่วยให้ค้นเจอ |
| `tags` | recommended | array ของ tag |
| `year` | yes | ปี พ.ศ. เช่น `2568`, `2569` |
| `starred` | optional | ถ้า `true` จะแสดงเป็นงานแนะนำ ถ้าไม่มีจะถือว่า `false` |

URL priority ตอน build:

1. `url`
2. `drive_url`
3. `drive_file_id`

> [!NOTE]
> ถ้าไม่มีทั้งสามแบบ ปุ่ม "เปิดเอกสาร PDF" จะใช้ไม่ได้ และ `--strict` จะ fail

</details>

## ID Policy

- `id` ใช้จับคู่ `sources.json` กับ `catalog-index.json`
- รูปแบบคือ `catNNN` เช่น `cat001`, `cat035`
- Entry ใหม่ใช้เลขถัดไปจาก ID สูงสุดที่มีอยู่
- การแก้ metadata ปกติไม่ควรเปลี่ยน `id`
- ถ้าต้องเปลี่ยน `id` ให้ถือเป็น migration และต้องตรวจทั้ง `sources.json` กับ `catalog-index.json`

## Troubleshooting

| ปัญหา | สาเหตุที่พบบ่อย | วิธีแก้ |
|---|---|---|
| Entry ใหม่ไม่ขึ้นหน้าเว็บ | แก้ `sources.json` แต่ไม่ได้ build index | รัน `python catalog/build_index.py --strict` |
| ค้น metadata เจอ แต่ค้นเนื้อหา PDF ไม่เจอ | entry เป็น metadata-only หรือ `content` ว่าง | วาง PDF ให้ชื่อ match แล้วรัน `--refresh-content <id> --strict` |
| Script บอก no local PDF | ชื่อไฟล์ใน `raw/` ไม่ตรงกับ `file`, `id.pdf`, หรือ `drive_file_id.pdf` | เปลี่ยนชื่อไฟล์หรือแก้ field `file` ให้ตรง |
| ปุ่ม PDF ใช้ไม่ได้ | ไม่มี `url`, `drive_url`, หรือ `drive_file_id` | เติม link แล้วรัน strict build |
| ค้นชื่อหน่วยงานไม่เจอ | `org` ว่างหรือสะกดผิด | แก้ `org` แล้วรัน strict build |
| Catalog ไม่โหลด | เปิดผ่าน `file://` | เปิดผ่าน local web server/live server |


## Technical Notes

<details>
<summary>Preserve-safe build behavior</summary>

> [!NOTE]
> Build ปกติเป็น preserve-safe:
>
> - โหลด `catalog-index.json` เดิมเป็น baseline
> - Entry เดิมเก็บ `content`, `content_tokens` และ `pdf_hash` เดิมไว้
> - PDF ของ entry เดิมไม่ถูก re-extract ถ้าไม่ได้สั่ง refresh
> - Entry ใหม่ที่มี local PDF จะถูก extract
> - Entry ใหม่ที่ไม่มี local PDF จะเป็น metadata-only
> - ID ที่ถูกลบจาก `sources.json` จะถูกลบจาก generated index
> - ถ้า `pdf_hash` เปลี่ยน จะเตือน แต่ไม่ refresh content อัตโนมัติ

</details>

<details>
<summary>Search behavior</summary>

> [!NOTE]
> Search behavior:
>
> - ใช้ custom substring matcher แทน FlexSearch เพราะภาษาไทยไม่มีช่องว่างระหว่างคำสม่ำเสมอ
> - หลายคำค้นใช้ AND behavior
> - Search weights: `org`, `title`, `filename`, `tags` = 3, `desc` = 2, `content` = 1
> - หน้าเว็บค้นจากทั้ง `content_tokens` และ `content`

</details>

<details>
<summary>Optional dependencies</summary>

```bash
pip install pypdf pdfplumber pythainlp
pip install pdf2image pytesseract pillow
```

> [!NOTE]
> สำหรับ OCR ต้องมี Tesseract, Thai traineddata และ poppler ในเครื่องด้วย

</details>

<details>
<summary>Advanced commands</summary>

```bash
python catalog/build_index.py --refresh-all-content --strict
python catalog/build_index.py --no-ocr --strict
```

</details>


## Current Snapshot
<details>
<summary>Current snapshot</summary>

- ตอนนี้ catalog มี 42 entries
- ปี 2568 มี 34 entries
- ปี 2569 มี 8 entries
- `starred` ตอนนี้มี 7 entries: `cat001`, `cat011`, `cat028`, `cat030`, `cat031`, `cat041`, `cat042`

> [!NOTE]
> ค่าพวกนี้เป็น snapshot เพื่อช่วยเช็คคร่าว ๆ ถ้าเพิ่มข้อมูลใหม่ ตัวเลขจะเปลี่ยนได้ตามปกติ

</details>
