from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bookings.db'
db = SQLAlchemy(app)

# 定義資料表
class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    phone = db.Column(db.String(50))
    email = db.Column(db.String(100))
    dive_date = db.Column(db.String(20))
    time_slot = db.Column(db.String(20))
    package = db.Column(db.String(100))
    divers_count = db.Column(db.Integer)
    notes = db.Column(db.String(200))
    status = db.Column(db.String(20), default="pending")

# 建立資料庫
with app.app_context():
    db.create_all()

# 固定可選時段
TIME_SLOTS = ["上午 08:00", "中午 11:00", "下午 14:00"]
# 潛水方案
PACKAGES = [
    "體驗潛水 (Try Diving)",
    "PADI Open Water Diver",
    "PADI Advanced Open Water Diver",
    "PADI Rescue Diver",
    "Fun Dive 小隊 (持證)",
    "拍照小隊 (持證 + 自備相機)",
    "PADI 潛水課程"
]

@app.route('/')
def index():
    return render_template('index.html', time_slots=TIME_SLOTS, packages=PACKAGES)

@app.route('/book', methods=['POST'])
def book():
    name = request.form['name']
    phone = request.form['phone']
    email = request.form['email']
    dive_date = request.form['dive_date']
    time_slot = request.form['time_slot']
    package = request.form['package']
    divers_count = request.form['divers_count']
    notes = request.form['notes']

    # 寫入資料庫
    booking = Booking(
        name=name, phone=phone, email=email,
        dive_date=dive_date, time_slot=time_slot,
        package=package, divers_count=divers_count,
        notes=notes
    )
    db.session.add(booking)
    db.session.commit()

    # 寄信通知教練
    try:
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        message = Mail(
            from_email='comcomdive@gmail.com',
            to_emails='comcomdive@gmail.com',  # 教練信箱
            subject='📥 新的潛水預約通知',
            html_content=f"""
            <h3>潛水預約通知</h3>
            <p><b>姓名：</b>{name}</p>
            <p><b>電話：</b>{phone}</p>
            <p><b>Email：</b>{email}</p>
            <p><b>日期：</b>{dive_date}</p>
            <p><b>時段：</b>{time_slot}</p>
            <p><b>方案：</b>{package}</p>
            <p><b>人數：</b>{divers_count}</p>
            <p><b>備註：</b>{notes}</p>
            """
        )
        response = sg.send(message)
        print("[SENDGRID] 教練信狀態：", response.status_code)
    except Exception as e:
        print("[SENDGRID] 教練信寄送失敗：", e)

    # 寄信給客戶
    try:
        customer_message = Mail(
            from_email='comcomdive@gmail.com',
            to_emails=email,
            subject='✅ 預約成功通知 - 來來潛水工作室',
            html_content=f"""
            <h2>感謝你的預約！💙</h2>
            <p>我們已收到你的潛水預約，以下是你的資訊：</p>
            <ul>
                <li><b>姓名：</b>{name}</li>
                <li><b>日期：</b>{dive_date}</li>
                <li><b>時段：</b>{time_slot}</li>
                <li><b>方案：</b>{package}</li>
                <li><b>人數：</b>{divers_count}</li>
            </ul>
            <p>若需更改或取消，請直接回覆此信件與我們聯繫。</p>
            <br>
            <b>來來潛水工作室 敬上</b>
            """
        )
        response2 = sg.send(customer_message)
        print("[SENDGRID] 客戶信狀態：", response2.status_code)
    except Exception as e:
        print("[SENDGRID] 客戶信寄送失敗：", e)

    return render_template('success.html', name=name)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
