import os
from datetime import datetime, date
from flask import Flask, request, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///dive_booking.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

TIME_SLOTS = ["上午（08:00-12:00）", "下午（13:00-17:00）", "夜潛（18:00-21:00）"]
PACKAGES = ["體驗潛水（Try Dive）", "Fun Dive（已持證）", "AOW/Rescue 課程", "微距攝影課（TG / 打光）"]
CAPACITY = int(os.getenv("CAPACITY_PER_SLOT", "8"))

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    phone = db.Column(db.String(40), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    dive_date = db.Column(db.Date, nullable=False)
    time_slot = db.Column(db.String(40), nullable=False)
    package = db.Column(db.String(80), nullable=False)
    divers_count = db.Column(db.Integer, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

def get_capacity_for(dive_date, time_slot):
    return CAPACITY

def get_used_slots(dive_date, time_slot):
    total = db.session.query(func.coalesce(func.sum(Booking.divers_count), 0))\
        .filter(Booking.dive_date == dive_date)\
        .filter(Booking.time_slot == time_slot)\
        .filter(Booking.status.in_(["pending", "confirmed"]))\
        .scalar()
    return int(total or 0)

def get_remaining_capacity(dive_date, time_slot):
    return max(get_capacity_for(dive_date, time_slot) - get_used_slots(dive_date, time_slot), 0)

@app.get("/")
def index():
    return render_template("index.html", time_slots=TIME_SLOTS, packages=PACKAGES, message=None)

@app.post("/book")
def book():
    form = request.form
    name = (form.get("name") or "").strip()
    phone = (form.get("phone") or "").strip()
    email = (form.get("email") or "").strip()
    d_str = (form.get("dive_date") or "").strip()
    time_slot = (form.get("time_slot") or "").strip()
    package = (form.get("package") or "").strip()
    notes = (form.get("notes") or "").strip()
    try:
        d = datetime.strptime(d_str, "%Y-%m-%d").date()
        if d < date.today():
            raise ValueError("日期不可早於今天")
    except Exception:
        return render_template("index.html", time_slots=TIME_SLOTS, packages=PACKAGES,
                               message="❗ 日期格式錯誤或早於今天")

    if time_slot not in TIME_SLOTS or package not in PACKAGES:
        return render_template("index.html", time_slots=TIME_SLOTS, packages=PACKAGES,
                               message="❗ 時段或方案選擇錯誤")
    try:
        divers_count = int(form.get("divers_count", "1"))
        if divers_count <= 0:
            raise ValueError
    except Exception:
        return render_template("index.html", time_slots=TIME_SLOTS, packages=PACKAGES,
                               message="❗ 人數需為正整數")

    if not name or not phone or ("@" not in email):
        return render_template("index.html", time_slots=TIME_SLOTS, packages=PACKAGES,
                               message="❗ 請填寫完整資料")

    remain = get_remaining_capacity(d, time_slot)
    if divers_count > remain:
        return render_template("index.html", time_slots=TIME_SLOTS, packages=PACKAGES,
                               message=f"⚠️ 名額不足：{d} {time_slot} 剩 {remain} 位")

    b = Booking(name=name, phone=phone, email=email, dive_date=d, time_slot=time_slot,
                package=package, divers_count=divers_count, notes=notes, status="pending")
    db.session.add(b)
    db.session.commit()
    return redirect(url_for("success", bid=b.id))

@app.get("/success")
def success():
    bid = request.args.get("bid", type=int)
    b = Booking.query.get_or_404(bid)
    return render_template("success.html", b=b)

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
