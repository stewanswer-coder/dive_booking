from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bookings.db'
db = SQLAlchemy(app)

# 資料表定義
class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    phone = db.Column(db.String(50))
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

# 初始化資料庫
with app.app_context():
    db.create_all()

# 固定選項
TIME_SLOTS = ["上午 08:00", "下午 13:00"]
PACKAGES = [
    "體驗潛水 (Try Diving)",
    "PADI Open Water Diver",
    "PADI Advanced Open Water Diver",
    "PADI Rescue Diver",
    "Fun Dive 小隊 (持證)",
    "拍照小隊 (持證 + 自備相機)",
    "PADI 潛水課程"
]
COACHES = ["阿行教練"]

@app.route('/')
def index():
    return render_template('index.html', time_slots=TIME_SLOTS, packages=PACKAGES, coaches=COACHES)

@app.route('/book', methods=['POST'])
def book():
    # 接收表單資料
    name = request.form['name']
    phone = request.form['phone']
    email = request.form['email']
    coach = request.form['coach']
    dive_date = request.form['dive_date']
    time_slot = request.form['time_slot']
    package = request.form['package']
    divers_count = request.form['divers_count']
    need_equipment = request.form['need_equipment']
    equipment_items = ", ".join(request.form.getlist('equipment_items'))
    height = request.form.get('height', '')
    weight = request.form.get('weight', '')
    shoe_size = request.form.get('shoe_size', '')
    notes = request.form['notes']

    # 寫入資料庫
    booking = Booking(
        name=name, phone=phone, email=email, coach=coach,
        dive_date=dive_date, time_slot=time_slot,
        package=package, divers_count=divers_count,
        need_equipment=need_equipment, equipment_items=equipment_items,
        height=height, weight=weight, shoe_size=shoe_size, notes=notes
    )
    db.session.add(booking)
    db.session.commit()

    # --- 寄信通知教練 ---
    try:
       from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email

message = Mail(
    from_email=Email('noreply@sendgrid.net', name='來來潛水工作室'),
    to_emails=email,
    subject='潛水預約確認通知',
    html_content=email_content
)

# ✅ 新增這行！
message.reply_to = Email('comcomdive@gmail.com', name='阿行教練')

            <h3>潛水預約通知</h3>
            <p><b>姓名：</b>{name}</p>
            <p><b>電話：</b>{phone}</p>
            <p><b>Email：</b>{email}</p>
            <p><b>教練：</b>{coach}</p>
            <p><b>日期：</b>{dive_date}</p>
            <p><b>時段：</b>{time_slot}</p>
            <p><b>方案：</b>{package}</p>
            <p><b>人數：</b>{divers_count}</p>
            <p><b>是否租裝備：</b>{need_equipment}</p>
            <p><b>裝備項目：</b>{equipment_items if equipment_items else '無'}</p>
            <p><b>身高：</b>{height} cm</p>
            <p><b>體重：</b>{weight} kg</p>
            <p><b>鞋號：</b>{shoe_size}</p>
            <p><b>備註：</b>{notes}</p>
            """
        )
        response = sg.send(message)
        print("[SENDGRID] 教練信狀態：", response.status_code)
    except Exception as e:
        print("[SENDGRID] 教練信寄送失敗：", e)

    # --- 寄信給客戶 ---
    try:
        customer_message = Mail(
            from_email='comcomdive@gmail.com',
            to_emails=email,
            subject='✅ 預約成功通知 - 來來潛水工作室',
            html_content=f"""
            <h2>感謝你的預約！💙</h2>
            <p>我們已收到你的潛水預約，以下是你的報名資訊：</p>
            <ul>
                <li><b>姓名：</b>{name}</li>
                <li><b>教練：</b>{coach}</li>
                <li><b>日期：</b>{dive_date}</li>
                <li><b>時段：</b>{time_slot}</li>
                <li><b>方案：</b>{package}</li>
                <li><b>人數：</b>{divers_count}</li>
                <li><b>租裝備：</b>{need_equipment}</li>
                <li><b>裝備項目：</b>{equipment_items if equipment_items else '無'}</li>
                <li><b>身高：</b>{height} cm　<b>體重：</b>{weight} kg　<b>鞋號：</b>{shoe_size}</li>
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
