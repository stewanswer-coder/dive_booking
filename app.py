from flask import Flask, render_template, render_template_string, request
from flask_sqlalchemy import SQLAlchemy
import os, traceback, uuid, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# === 初始化 Flask 與 DB ===
app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bookings.db'
db = SQLAlchemy(app)

# === 資料表定義 ===
class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    line_id = db.Column(db.String(50))
    email = db.Column(db.String(100))
    coach = db.Column(db.String(50))
    dive_date = db.Column(db.String(50))
    time_slot = db.Column(db.String(50))
    package = db.Column(db.String(100))
    divers_count = db.Column(db.Integer)
    need_equipment = db.Column(db.String(10))
    equipment_items = db.Column(db.String(200))
    height = db.Column(db.String(10))
    weight = db.Column(db.String(10))
    shoe_size = db.Column(db.String(10))
    notes = db.Column(db.String(500))

# === 郵件設定 ===
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
COACH_EMAIL = {
    "阿行教練": os.getenv("ADMIN_EMAIL", GMAIL_USER),
    "阿丹教練": os.getenv("ADMIN_EMAIL", GMAIL_USER),
}

def send_email_via_gmail(to_email, subject, html_content, text_content, reply_to=None):
    """寄送 email via Gmail SMTP"""
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = GMAIL_USER
        msg["To"] = to_email
        msg["Subject"] = subject
        if reply_to:
            msg["Reply-To"] = reply_to

        msg.attach(MIMEText(text_content, "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.send_message(msg)

        print(f"[MAIL] 寄信成功：{to_email}")
    except Exception as e:
        print(f"[MAIL ERROR] 無法寄給 {to_email}：{e}")
        traceback.print_exc()


# === 預約表單提交 ===
@app.route("/book", methods=["POST"])
def book():
    error_id = uuid.uuid4().hex[:8]

    try:
        form = dict(request.form)
        print("[DEBUG] form data:", form)

        # ---- 取資料 ----
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        line_id = request.form.get("line_id", "").strip()
        email = request.form.get("email", "").strip()
        coach = request.form.get("coach", "阿行教練").strip()
        dive_date = request.form.get("dive_date", "").strip()
        time_slot = request.form.get("time_slot", "").strip()
        package = request.form.get("package", "").strip()
        divers_count = request.form.get("divers_count", "1").strip()
        divers_count = int(divers_count) if divers_count.isdigit() else 1
        need_equipment = request.form.get("need_equipment", "N").strip()
        equipment_items = ", ".join(request.form.getlist("equipment_items"))
        height = request.form.get("height", "").strip()
        weight = request.form.get("weight", "").strip()
        shoe_size = request.form.get("shoe_size", "").strip()
        notes = request.form.get("notes", "").strip()

        # ---- 寫入資料庫 ----
        try:
            booking = Booking(
                name=name, phone=phone, line_id=line_id, email=email, coach=coach,
                dive_date=dive_date, time_slot=time_slot, package=package,
                divers_count=divers_count, need_equipment=need_equipment,
                equipment_items=equipment_items, height=height, weight=weight,
                shoe_size=shoe_size, notes=notes
            )
            db.session.add(booking)
            db.session.commit()
        except Exception:
            print("[DB] 寫入失敗：")
            traceback.print_exc()
            db.session.rollback()

        # ---- 寄信階段 ----
        try:
            reply_to = COACH_EMAIL.get(coach, GMAIL_USER)
            coach_to = COACH_EMAIL.get(coach, GMAIL_USER)

            coach_subject = f"新的潛水預約：{dive_date}（{time_slot}）"
            coach_html = f"""
            <html><body>
              <h3>潛水預約通知</h3>
              <p><b>姓名：</b>{name}</p>
              <p><b>電話：</b>{phone}</p>
              <p><b>LINE ID：</b>{line_id or '（未填）'}</p>
              <p><b>Email：</b>{email}</p>
              <p><b>教練：</b>{coach}</p>
              <p><b>日期：</b>{dive_date}</p>
              <p><b>時段：</b>{time_slot}</p>
              <p><b>方案：</b>{package}</p>
              <p><b>人數：</b>{divers_count}</p>
              <p><b>租裝備：</b>{need_equipment}</p>
              <p><b>裝備項目：</b>{equipment_items or '無'}</p>
              <p><b>身高：</b>{height} cm　<b>體重：</b>{weight} kg　<b>鞋號：</b>{shoe_size}</p>
              <p><b>備註：</b>{notes or '（無）'}</p>
            </body></html>
            """
            coach_text = f"""潛水預約通知
姓名：{name}
電話：{phone}
LINE ID：{line_id or '（未填）'}
Email：{email}
教練：{coach}
日期：{dive_date}  時段：{time_slot}
方案：{package}  人數：{divers_count}
租裝備：{need_equipment}
裝備項目：{equipment_items or '無'}
身高：{height} cm  體重：{weight} kg  鞋號：{shoe_size}
備註：{notes or '（無）'}
"""
            send_email_via_gmail(coach_to, coach_subject, coach_html, coach_text, reply_to=reply_to)

            # 回信給客戶
            customer_subject = f"你的潛水預約已建立：{dive_date}（{time_slot}）"
            customer_html = f"""
            <html><body>
              <h3>預約已建立</h3>
              <p>教練：{coach}</p>
              <p>日期：{dive_date}</p>
              <p>時段：{time_slot}</p>
              <p>方案：{package}</p>
              <p>人數：{divers_count}</p>
              <p>租裝備：{need_equipment}</p>
              <p>LINE ID：{line_id or '（未填）'}</p>
              <p>若需更改或取消，請直接回覆此信件與我們聯繫。</p>
            </body></html>
            """
            customer_text = f"""預約已建立
教練：{coach}  日期：{dive_date}  時段：{time_slot}
方案：{package}  人數：{divers_count}  租裝備：{need_equipment}
LINE ID：{line_id or '（未填）'}"""

            send_email_via_gmail(email, customer_subject, customer_html, customer_text, reply_to=reply_to)

        except Exception:
            print("[EMAIL] 發信階段出錯：")
            traceback.print_exc()

        # ---- 回傳成功頁 ----
        try:
            return render_template("success.html", name=name)
        except Exception:
            html = f"""<!doctype html><meta charset="utf-8">
                       <h2>預約已完成 ✅</h2>
                       <p>{name}，我們已收到你的預約，稍後會以 Email 與你聯絡。</p>
                       <a href="/">回首頁</a>"""
            return render_template_string(html)

    except Exception:
        print(f"[ERROR #{error_id}] 預約流程中斷")
        traceback.print_exc()
        return render_template_string(f"""
        <!doctype html><meta charset="utf-8">
        <h2>系統忙線中</h2>
        <p>預約送出時遇到錯誤（代碼 {error_id}）。請稍後重試。</p>
        <a href="/">回首頁</a>
        """)


# === 首頁（假設有 index.html） ===
@app.route("/")
def index():
    return render_template("index.html")


# === 啟動伺服器 ===
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
