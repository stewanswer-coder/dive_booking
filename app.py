from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bookings.db'
db = SQLAlchemy(app)

# -----------------------------
# 資料表定義
# -----------------------------
class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    phone = db.Column(db.String(50))
    line_id = db.Column(db.String(50))
    email = db.Column(db.String(100))
    coach = db.Column(db.String(50))
    dive_date = db.Column(db.String(20))
    time_slot = db.Column(db.String(20))
    package = db.Column(db.String(100))
    divers_count = db.Column(db.Integer)
    need_equipment = db.Column(db.String(5))
    equipment_items = db.Column(db.String(200))
    height = db.Column(db.String(10))
    weight = db.Column(db.String(10))
    shoe_size = db.Column(db.String(10))
    notes = db.Column(db.String(300))
    status = db.Column(db.String(20), default="pending")

with app.app_context():
    db.create_all()

# -----------------------------
# 固定選項
# -----------------------------
TIME_SLOTS = ["上午 08:00", "下午 13:00"]
PACKAGES = [
    "體驗潛水 (Try Diving)",
    "PADI Open Water Diver",
    "PADI Advanced Open Water Diver",
    "PADI Rescue Diver",
    "Fun Dive 小隊 (持證)",
    "拍照小隊 (持證 + 自備相機)",
    "PADI 潛水課程",
]
COACHES = ["阿行教練"]
COACH_EMAIL = {"阿行教練": "comcomdive@gmail.com"}

# -----------------------------
# Gmail SMTP 設定（用環境變數）
# Render → Environment → 新增：
# GMAIL_USER, GMAIL_APP_PASSWORD
# -----------------------------
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
GMAIL_USER = os.environ.get("GMAIL_USER")          # 例如 comcomdive@gmail.com
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")


def send_email_via_gmail(to_addr: str, subject: str, html_body: str, text_body: str = "", reply_to: str | None = None):
    """
    使用 Gmail SMTP 寄信（HTML + 文字版）。需設定 GMAIL_USER 與 GMAIL_APP_PASSWORD。
    """
    if not (GMAIL_USER and GMAIL_APP_PASSWORD):
        print("[GMAIL SMTP] 缺少 GMAIL_USER 或 GMAIL_APP_PASSWORD，略過寄信")
        return

    msg = MIMEMultipart("alternative")
    msg["From"] = f"來來潛水工作室 <{GMAIL_USER}>"
    msg["To"] = to_addr
    msg["Subject"] = subject
    if reply_to:
        msg["Reply-To"] = reply_to

    if text_body:
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
    if html_body:
        msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, [to_addr], msg.as_string())
        print(f"[GMAIL SMTP] 寄信成功 → {to_addr}")
    except Exception as e:
        print("[GMAIL SMTP] 寄送失敗：", e)


@app.route("/")
def index():
    return render_template("index.html", time_slots=TIME_SLOTS, packages=PACKAGES, coaches=COACHES)


@app.route("/book", methods=["POST"])
def book():
    # 讀取表單
    print("[DEBUG] form data:", dict(request.form))  # 方便排錯；穩定後可移除
    name = request.form["name"]
    phone = request.form["phone"]
    line_id = request.form.get("line_id", "").strip()
    email = request.form["email"]
    coach = request.form["coach"]
    dive_date = request.form["dive_date"]
    time_slot = request.form["time_slot"]
    package = request.form["package"]
    divers_count = int(request.form["divers_count"])
    need_equipment = request.form["need_equipment"]
    equipment_items = ", ".join(request.form.getlist("equipment_items"))
    height = request.form.get("height", "").strip()
    weight = request.form.get("weight", "").strip()
    shoe_size = request.form.get("shoe_size", "").strip()
    notes = request.form.get("notes", "").strip()

    # 寫入 DB
    booking = Booking(
        name=name, phone=phone, line_id=line_id, email=email, coach=coach,
        dive_date=dive_date, time_slot=time_slot, package=package,
        divers_count=divers_count, need_equipment=need_equipment,
        equipment_items=equipment_items, height=height, weight=weight,
        shoe_size=shoe_size, notes=notes
    )
    db.session.add(booking)
    db.session.commit()

    # Reply-To 設為教練信箱（回覆時會回到教練）
    reply_to = COACH_EMAIL.get(coach, GMAIL_USER)

    # ---------- 給教練 ----------
    coach_to = COACH_EMAIL.get(coach, GMAIL_USER)
    coach_subject = f"你的潛水預約新報名：{dive_date}（{time_slot}）"
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
      <p><b>裝備項目：</b>{equipment_items if equipment_items else '無'}</p>
      <p><b>身高：</b>{height} cm　<b>體重：</b>{weight} kg　<b>鞋號：</b>{shoe_size}</p>
      <p><b>備註：</b>{notes or '（無）'}</p>
      <hr>
      <p style="font-size:12px;color:#666;">來來潛水工作室｜新北市三重區重新路三段138號</p>
    </body></html>
    """
    coach_text = f"""潛水預約通知
姓名：{name}
電話：{phone}
LINE ID：{line_id or '（未填）'}
Email：{email}
教練：{coach}
日期：{dive_date}
時段：{time_slot}
方案：{package}
人數：{divers_count}
租裝備：{need_equipment}
裝備項目：{equipment_items if equipment_items else '無'}
身高：{height} cm  體重：{weight} kg  鞋號：{shoe_size}
備註：{notes or '（無）'}
"""
    send_email_via_gmail(coach_to, coach_subject, coach_html, coach_text, reply_to=reply_to)

    # ---------- 給學員 ----------
    customer_subject = f"你的潛水預約已建立：{dive_date}（{time_slot}）"
    customer_html = f"""
    <html><body>
      <h3>預約已建立</h3>
      <p>我們已收到你的潛水報名，以下是你的預約資訊：</p>
      <ul>
        <li>教練：{coach}</li>
        <li>日期：{dive_date}</li>
        <li>時段：{time_slot}</li>
        <li>方案：{package}</li>
        <li>人數：{divers_count}</li>
        <li>租裝備：{need_equipment}</li>
        <li>LINE ID：{line_id or '（未填）'}</li>
      </ul>
      <p>若需更改或取消，請直接回覆此信件與我們聯繫。</p>
      <hr>
      <p style="font-size:12px;color:#666;">來來潛水工作室｜新北市三重區重新路三段138號</p>
    </body></html>
    """
    customer_text = f"""預約已建立
教練：{coach}
日期：{dive_date}
時段：{time_slot}
方案：{package}
人數：{divers_count}
租裝備：{need_equipment}
LINE ID：{line_id or '（未填）'}
"""
    send_email_via_gmail(email, customer_subject, customer_html, customer_text, reply_to=reply_to)

    return render_template("success.html", name=name)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
