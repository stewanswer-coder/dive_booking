import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, date
from flask import Flask, request, render_template, redirect, url_for, Response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
import csv
from io import StringIO

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///dive_booking.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

TIME_SLOTS = ["上午（08:00-12:00）", "下午（13:00-17:00）", "夜潛（18:00-21:00）"]
PACKAGES  = ["體驗潛水（Try Dive）", "Fun Dive（已持證）", "AOW/Rescue 課程", "微距攝影課（TG / 打光）"]
CAPACITY  = int(os.getenv("CAPACITY_PER_SLOT", "8"))

class Booking(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(80), nullable=False)
    phone         = db.Column(db.String(40), nullable=False)
    email         = db.Column(db.String(120), nullable=False)
    dive_date     = db.Column(db.Date, nullable=False)
    time_slot     = db.Column(db.String(40), nullable=False)
    package       = db.Column(db.String(80), nullable=False)
    divers_count  = db.Column(db.Integer, nullable=False)
    notes         = db.Column(db.Text, nullable=True)
    status        = db.Column(db.String(20), nullable=False, default="pending")
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

def get_used_slots(dive_date, time_slot):
    total = db.session.query(db.func.coalesce(db.func.sum(Booking.divers_count), 0)) \        .filter(Booking.dive_date == dive_date) \        .filter(Booking.time_slot == time_slot) \        .filter(Booking.status.in_(["pending", "confirmed"])) \        .scalar()
    return int(total or 0)

def get_remaining_capacity(dive_date, time_slot):
    return max(CAPACITY - get_used_slots(dive_date, time_slot), 0)

SMTP_HOST     = os.getenv("SMTP_HOST")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
FROM_EMAIL    = os.getenv("FROM_EMAIL", SMTP_USERNAME)
ADMIN_EMAIL   = os.getenv("ADMIN_EMAIL")
BASE_URL      = os.getenv("BASE_URL", "")

def send_email(to_addr: str, subject: str, body: str):
    if not (SMTP_HOST and SMTP_USERNAME and SMTP_PASSWORD and FROM_EMAIL and to_addr):
        return False
    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = subject
    msg["From"] = FROM_EMAIL
    msg["To"] = to_addr
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(FROM_EMAIL, [to_addr], msg.as_string())
        return True
    except Exception as e:
        print(f"[EMAIL] Failed to send to {to_addr}: {e}")
        return False

@app.get("/")
def index():
    return render_template("index.html", time_slots=TIME_SLOTS, packages=PACKAGES, message=None)

@app.post("/book")
def book():
    f = request.form
    name  = f.get("name", "").strip()
    phone = f.get("phone", "").strip()
    email = f.get("email", "").strip()
    d_str = f.get("dive_date", "").strip()
    slot  = f.get("time_slot", "").strip()
    pkg   = f.get("package", "").strip()
    notes = f.get("notes", "").strip()

    try:
        d = datetime.strptime(d_str, "%Y-%m-%d").date()
        if d < date.today():
            raise ValueError("past")
    except Exception:
        return render_template("index.html", time_slots=TIME_SLOTS, packages=PACKAGES, message="❗ 日期錯誤或早於今天")

    try:
        count = int(f.get("divers_count", "1"))
        if count <= 0:
            raise ValueError
    except Exception:
        return render_template("index.html", time_slots=TIME_SLOTS, packages=PACKAGES, message="❗ 人數需為正整數")

    if not name or not phone or ("@" not in email):
        return render_template("index.html", time_slots=TIME_SLOTS, packages=PACKAGES, message="❗ 請填寫完整資料")

    remain = get_remaining_capacity(d, slot)
    if count > remain:
        return render_template("index.html", time_slots=TIME_SLOTS, packages=PACKAGES, message=f"⚠️ 名額不足，剩 {remain} 位")

    b = Booking(name=name, phone=phone, email=email, dive_date=d, time_slot=slot,
                package=pkg, divers_count=count, notes=notes, status="pending")
    db.session.add(b)
    db.session.commit()

    subject_user = "ComComDive 預約已收到"
    link = f"{BASE_URL}/success?bid={b.id}" if BASE_URL else "(請回到網站查看預約詳情)"
    body_user = (f"{name} 您好，\n\n"
                 f"我們已收到您的潛水預約：\n"
                 f"日期：{b.dive_date}\n時段：{b.time_slot}\n方案：{b.package}\n人數：{b.divers_count}\n\n"
                 f"預約查詢：{link}\n\n— ComComDive 團隊")
    send_email(email, subject_user, body_user)

    if ADMIN_EMAIL:
        subject_admin = f"[新預約 #{b.id}] {b.dive_date} {b.time_slot} {b.name} x{b.divers_count}"
        body_admin = (f"新預約通知：\n\nID：{b.id}\n姓名：{b.name}\n電話：{b.phone}\nEmail：{b.email}\n"
                      f"日期：{b.dive_date}\n時段：{b.time_slot}\n方案：{b.package}\n人數：{b.divers_count}\n"
                      f"備註：{b.notes or ''}\n狀態：{b.status}\n建立時間：{b.created_at}\n")
        send_email(ADMIN_EMAIL, subject_admin, body_admin)

    return redirect(url_for("success", bid=b.id))

@app.get("/success")
def success():
    b = Booking.query.get_or_404(request.args.get("bid", type=int))
    return render_template("success.html", b=b)

@app.get("/admin")
def admin_list():
    rows = Booking.query.order_by(Booking.created_at.desc()).all()
    html = ["<h2>預約列表</h2><table border=1 cellpadding=6>",
            "<tr><th>ID</th><th>日期</th><th>時段</th><th>方案</th><th>人數</th><th>姓名</th><th>電話</th><th>Email</th><th>備註</th><th>狀態</th></tr>"]
    for r in rows:
        html.append(f"<tr><td>{r.id}</td><td>{r.dive_date}</td><td>{r.time_slot}</td><td>{r.package}</td>"
                    f"<td>{r.divers_count}</td><td>{r.name}</td><td>{r.phone}</td><td>{r.email}</td>"
                    f"<td>{r.notes or ''}</td><td>{r.status}</td></tr>")
    html.append("</table><p><a href='/admin.csv'>下載 CSV</a></p>")
    return Response(''.join(html), mimetype='text/html')

@app.get("/admin.csv")
def admin_csv():
    rows = Booking.query.order_by(Booking.created_at.desc()).all()
    buf = StringIO(); w = csv.writer(buf)
    w.writerow(["id","date","slot","package","count","name","phone","email","notes","status","created_at"])
    for r in rows:
        w.writerow([r.id,r.dive_date,r.time_slot,r.package,r.divers_count,r.name,r.phone,r.email,r.notes or "",r.status,r.created_at])
    return Response(buf.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=bookings.csv"})

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
