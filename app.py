from flask import Flask, render_template_string, request
from flask_sqlalchemy import SQLAlchemy
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bookings.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 資料表
class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    date = db.Column(db.String(20))
    time_slot = db.Column(db.String(50))
    plan = db.Column(db.String(50))
    divers_count = db.Column(db.Integer)

with app.app_context():
    db.create_all()

# 首頁表單
@app.route('/')
def index():
    return render_template_string('''
    <h1>潛水預約表單</h1>
    <form action="/book" method="post">
      姓名：<input type="text" name="name" required><br><br>
      日期：<input type="date" name="date" required><br><br>
      時段：
      <select name="time_slot" required>
        <option value="上午（08:00-12:00）">上午（08:00-12:00）</option>
        <option value="下午（13:00-17:00）">下午（13:00-17:00）</option>
      </select><br><br>
      方案：
      <select name="plan" required>
        <option value="體驗潛水（Try Dive）">體驗潛水（Try Dive）</option>
        <option value="Fun Dive（已持證）">Fun Dive（已持證）</option>
      </select><br><br>
      人數：<input type="number" name="divers_count" value="1" min="1" required><br><br>
      <button type="submit">送出預約</button>
    </form>
    ''')

# 處理預約
@app.route('/book', methods=['POST'])
def book():
    name = request.form['name']
    date = request.form['date']
    time_slot = request.form['time_slot']
    plan = request.form['plan']
    divers_count = int(request.form['divers_count'])

    new_booking = Booking(name=name, date=date, time_slot=time_slot, plan=plan, divers_count=divers_count)
    db.session.add(new_booking)
    db.session.commit()

    # ✅ 寄送通知信
    try:
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        msg = Mail(
            from_email='comcomdive@gmail.com',
            to_emails='comcomdive@gmail.com',
            subject='📩 新預約通知',
            html_content=f'''
            <h3>新的預約來了：</h3>
            <ul>
                <li><b>姓名：</b>{name}</li>
                <li><b>日期：</b>{date}</li>
                <li><b>時段：</b>{time_slot}</li>
                <li><b>方案：</b>{plan}</li>
                <li><b>人數：</b>{divers_count}</li>
            </ul>
            ''')
        response = sg.send(msg)
        print(f"[SENDGRID] 寄信狀態：{response.status_code}")
    except Exception as e:
        print(f"[SENDGRID] 寄信失敗：{e}")

    return render_template_string(f'''
    <h2>✅ 預約成功！</h2>
    <p>我們已收到你的預約，以下是資訊：</p>
    <ul>
      <li>日期：{date}</li>
      <li>時段：{time_slot}</li>
      <li>方案：{plan}</li>
      <li>人數：{divers_count}</li>
      <li>姓名：{name}</li>
    </ul>
    <a href="/">回首頁</a>
    ''')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
