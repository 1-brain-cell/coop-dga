# Draft เนื้อหา Basic Error สำหรับ day0.html

```html
      <!-- 
        หัวข้อ: พบกับข้อผิดพลาด (Basic Errors)
        เพิ่มโดย: GEMINI CLI
        วันที่: [CURRENT_DATE_TIME]
      -->
      <div class="card">
        <div class="card-t">⚠️ พบกับข้อผิดพลาด (Basic Errors)</div>
        <div class="card-s">การเจอ Error คือส่วนหนึ่งของการเรียนรู้ ไม่ต้องตกใจ! มาดูประเภทที่พบบ่อยกัน</div>
        
        <div class="g2" style="gap:20px;">
          <!-- 1. Syntax Error -->
          <div style="display:flex;flex-direction:column;gap:8px;">
            <div class="lbl" style="color:var(--rd);">1. พิมพ์ผิด (Syntax Error / Typos)</div>
            <div style="font-size:.88rem;color:var(--tl);line-height:1.5;">
              เหมือนการเขียนสะกดคำผิดในภาษาคน ทำให้ Python อ่านไม่รู้เรื่องและหยุดทำงานทันที
            </div>
            <div class="code-preview" style="background:#fff5f5;border:1px solid #feb2b2;">
              <span class="fn">prnit</span>(<span class="st">"Hello"</span>) <span class="cm"># พิมพ์ print ผิด</span><br>
              <span class="fn">print</span>(<span class="st">"Hi"</span> <span class="cm"># ลืมปิดวงเล็บ</span>
            </div>
          </div>

          <!-- 2. Runtime Error -->
          <div style="display:flex;flex-direction:column;gap:8px;">
            <div class="lbl" style="color:var(--am);">2. ข้อผิดพลาดขณะรัน (Runtime Error)</div>
            <div style="font-size:.88rem;color:var(--tl);line-height:1.5;">
              ไวยากรณ์ถูกแต่สั่งให้ทำในสิ่งที่คอมพิวเตอร์ทำไม่ได้ในขณะนั้น
            </div>
            <div class="code-preview" style="background:#fffaf0;border:1px solid #fbd38d;">
              <span class="nm">x</span> = <span class="nm">10</span> / <span class="nm">0</span> <span class="cm"># ZeroDivisionError (หารด้วย 0)</span><br>
              <span class="fn">print</span>(<span class="nm">unknown_var</span>) <span class="cm"># NameError (เรียกตัวแปรที่ไม่มี)</span>
            </div>
          </div>

          <!-- 3. Warning -->
          <div style="display:flex;flex-direction:column;gap:8px;">
            <div class="lbl" style="color:var(--cy);">3. คำเตือน (Warning)</div>
            <div style="font-size:.88rem;color:var(--tl);line-height:1.5;">
              โปรแกรมยังทำงานได้ต่อ แต่ Python แจ้งเตือนว่ามีบางอย่าง "เสี่ยง" หรือควรปรับปรุง
            </div>
            <div class="hbox blue" style="font-size:.82rem;margin-top:4px;">
              💡 มักพบเมื่อใช้ Library ภายนอกที่เริ่มเก่า หรือใช้วิธีการที่กำลังจะเลิกใช้ (Deprecated)
            </div>
          </div>

          <!-- 4. การจัดการ Error (Try-Except) -->
          <div style="display:flex;flex-direction:column;gap:8px;">
            <div class="lbl" style="color:var(--gn);">4. การรับมือ / ข้าม (Ignore / Handling)</div>
            <div style="font-size:.88rem;color:var(--tl);line-height:1.5;">
              ใช้คำสั่ง <code>try...except</code> เพื่อดักจับ Error และสั่งให้โปรแกรมทำงานต่อได้
            </div>
            <div class="code-preview" style="background:#f0fff4;border:1px solid #9ae6b4;">
              <span class="kw">try</span>:<br>
              &nbsp;&nbsp;<span class="nm">result</span> = <span class="nm">10</span> / <span class="nm">0</span><br>
              <span class="kw">except</span>:<br>
              &nbsp;&nbsp;<span class="fn">print</span>(<span class="st">"ข้ามจุดที่หารไม่ลงตัว"</span>)
            </div>
          </div>
        </div>

        <!-- 5. File Not Found -->
        <div style="margin-top:20px;padding:16px;background:#f8fafc;border:1px dashed var(--br);border-radius:10px;">
           <div class="lbl" style="color:var(--bd);">📂 5. หาไฟล์ไม่เจอ (FileNotFoundError)</div>
           <p style="font-size:.88rem;color:var(--tl);margin:8px 0;">เกิดขึ้นเมื่อสั่งเปิดไฟล์แต่ชื่อไฟล์ผิด หรือไฟล์ไม่ได้อยู่ในโฟลเดอร์นั้น</p>
           <div class="code-preview" style="background:#edf2f7;">
             <span class="nm">f</span> = <span class="fn">open</span>(<span class="st">"data.csv"</span>) <span class="cm"># ถ้าไม่มีไฟล์ data.csv ในโฟลเดอร์จะ Error</span>
           </div>
        </div>
      </div>
```
