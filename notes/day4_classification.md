# 🎯 Classification & Logistic Regression

Logistic Regression เป็นอัลกอริทึมที่ใช้สำหรับ **Classification** โดยจะคำนวณความน่าจะเป็น (Probability) ที่ข้อมูลจะอยู่ในแต่ละกลุ่ม ก่อนตัดสินใจเลือกผลลัพธ์สุดท้าย

> ⚠️ แม้ชื่อจะมีคำว่า "Regression" แต่ Logistic Regression ใช้สำหรับ **Classification** ไม่ใช่ Regression เพราะผลลัพธ์สุดท้ายเป็น "กลุ่ม" ไม่ใช่ค่าตัวเลขต่อเนื่อง

---

## 📈 1. Sigmoid Function (S-Curve)

โมเดลจะนำค่าที่คำนวณได้จากสมการเชิงเส้นมาแปลงผ่าน **Sigmoid Function** เพื่อให้ผลลัพธ์อยู่ในช่วง 0 ถึง 1

* 0 = โอกาสเกิดต่ำ
* 1 = โอกาสเกิดสูง

> ความน่าจะเป็นต้องอยู่ระหว่าง 0 และ 1 เสมอ จึงไม่สามารถใช้สมการเส้นตรงปกติได้โดยตรง

---

## 🛑 2. Decision Boundary

เมื่อได้ค่าความน่าจะเป็นแล้ว โมเดลจะใช้เกณฑ์ตัดสินใจ (Threshold) เพื่อเลือกคลาส

ตัวอย่าง Threshold = 0.5

* Probability ≥ 0.5 → Class 1
* Probability < 0.5 → Class 0

---

### 🌍 ตัวอย่าง

การทำนายโรคเบาหวาน

* Probability = 0.82 → มีความเสี่ยง (Class 1)
* Probability = 0.27 → ไม่มีความเสี่ยง (Class 0)

---

อันนี้จะเหลือแค่ 3 แนวคิดที่ผู้เรียนต้องจำ

1. Logistic Regression ใช้กับ **Classification**
2. Sigmoid แปลงค่าให้เป็น **Probability (0–1)**
3. Decision Boundary ใช้ตัดสินใจว่าอยู่ **Class ไหน**

แค่นี้ก็พอสำหรับ Intro แล้ว ส่วนสมการคณิตศาสตร์หรือกราฟ Sigmoid ค่อยให้ Interactive ด้านล่างเป็นคนสอนต่อครับ.
