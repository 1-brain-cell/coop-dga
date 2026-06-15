# Catalog search index

ระบบค้นหาผลงานผู้เรียนเก่าในแท็บ **Catalog** ของ `day5.html`
ค้นได้จาก **ชื่อไฟล์ / เนื้อหาภายในไฟล์ / ชื่อหน่วยงาน** โดยไม่ต้องมี backend

## ไฟล์ในโฟลเดอร์นี้

| ไฟล์ | หน้าที่ |
|---|---|
| `sources.json` | รายการผลงาน (single source of truth) — แก้ไฟล์นี้เพื่อเพิ่ม/แก้ผลงาน |
| `build_index.py` | สคริปต์สร้าง index: ดึงข้อความจาก PDF → OCR (ถ้าจำเป็น) → ตัดคำไทย → JSON |
| `catalog-index.json` | index ที่เว็บโหลดไปใช้ (สร้างจากสคริปต์ — commit ไฟล์นี้ด้วย) |
| `raw/` | (สร้างอัตโนมัติ) วาง PDF ต้นฉบับไว้ที่นี่เพื่อให้ดึงเนื้อหาได้ |

## วิธีเพิ่มผลงานใหม่

1. เพิ่ม object ใน `sources.json` หนึ่งชิ้นต่อหนึ่งผลงาน:
   ```json
   {
     "id": "unique-id",
     "drive_file_id": "ไอดีไฟล์บน Google Drive",
     "icon": "fa-chart-line",
     "org": "ชื่อหน่วยงาน",
     "title": "ชื่อผลงาน",
     "desc": "คำอธิบายสั้น",
     "tags": ["Tag1", "Tag2"]
   }
   ```
   - `icon` = ชื่อ Font Awesome (เช่น `fa-cloud-rain`, `fa-trash`, `fa-chart-line`)
   - ใส่ `"url"` เองได้ ถ้าไม่ใส่ จะสร้างลิงก์ Drive จาก `drive_file_id` ให้อัตโนมัติ
   - ลิงก์ Drive ต้องตั้งแชร์เป็น **"anyone with the link"** เพื่อให้ปุ่ม "เปิดเอกสาร PDF" ใช้ได้

2. (เพื่อให้ค้นจาก **เนื้อหาภายในไฟล์** ได้) วาง PDF ต้นฉบับไว้ที่ `raw/`
   ตั้งชื่อเป็น `<id>.pdf` หรือ `<drive_file_id>.pdf`
   ถ้าไม่วาง จะได้ entry แบบ metadata อย่างเดียว (ค้นจากชื่อ/หน่วยงาน/คำอธิบายได้ แต่ไม่ค้นเนื้อหาในไฟล์)

3. รัน build:
   ```bash
   python build_index.py
   ```

4. commit `sources.json` + `catalog-index.json` (และ `raw/` ถ้าต้องการเก็บต้นฉบับ)

## เพิ่มทีละหลายไฟล์ (เช่น 35 ไฟล์)

1. ก๊อป PDF ทั้งหมดลงโฟลเดอร์ `raw/`
2. สแกน + สร้างรายการอัตโนมัติ + build ในคำสั่งเดียว:
   ```bash
   python build_index.py --discover --no-ocr
   ```
   `--discover` จะเติม entry ให้ทุก PDF ที่ยังไม่มีใน `sources.json` (เดา `title` จากชื่อไฟล์)
3. เปิด `sources.json` เติมให้แต่ละชิ้น: `org` (ชื่อหน่วยงาน), `drive_file_id` (จาก URL แชร์ Drive),
   `tags`, แก้ `title`/`desc` ตามต้องการ
   > ถ้าไม่เติม `drive_file_id` (และไม่ใส่ `url`) ปุ่ม "เปิดเอกสาร PDF" จะกดไม่ไปไหน
4. build อีกครั้ง (ไม่ต้องใส่ `--discover` แล้ว):
   ```bash
   python build_index.py
   ```

## Dependencies (ติดตั้งเฉพาะที่ต้องใช้)

สคริปต์ทำงานได้แม้ไม่มี library ครบ (จะข้ามขั้นที่ขาดและเตือน) แต่ถ้าต้องการดึงเนื้อหา/ตัดคำไทยเต็มประสิทธิภาพ:

```bash
pip install pypdf pdfplumber pythainlp      # ดึงข้อความ PDF + ตัดคำไทย
pip install pdf2image pytesseract pillow     # OCR สำหรับสไลด์ที่เป็นรูปภาพ
```

OCR ต้องมีโปรแกรม **Tesseract** + ชุดภาษาไทย (`tha`) และ **poppler** (สำหรับ `pdf2image`) ติดตั้งในเครื่องด้วย

> ถ้าไม่ติดตั้ง `pythainlp` สคริปต์จะใช้ตัวตัดคำสำรอง (แยกไทย/อังกฤษเป็นช่วง) — ฝั่งเว็บยังค้นแบบ substring ได้ แต่การจัดอันดับ/ตัดคำจะแม่นน้อยลง แนะนำให้ติดตั้ง `pythainlp`

## ตัวเลือกของสคริปต์

```bash
python build_index.py            # ปกติ: อ่าน PDF จาก raw/ (หรือ metadata อย่างเดียว)
python build_index.py --download # ลองดาวน์โหลดไฟล์ Drive สาธารณะลง raw/ อัตโนมัติ
python build_index.py --no-ocr   # ข้าม OCR แม้ไฟล์จะเป็นรูปภาพ
```

> `--download` ใช้ได้กับไฟล์สาธารณะขนาดเล็กเท่านั้น ไฟล์ใหญ่/ไฟล์ส่วนตัวให้ดาวน์โหลดมือใส่ `raw/`

## รันเว็บเพื่อทดสอบ

เปิด `day5.html` ผ่านเว็บเซิร์ฟเวอร์ (ไม่ใช่ `file://` เพราะ `fetch` จะถูกบล็อก):

```bash
# จากโฟลเดอร์ dga306_2026_interactive_guide
python -m http.server 8000
# เปิด http://localhost:8000/day5.html แล้วไปแท็บ Catalog
```
