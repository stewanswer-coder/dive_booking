from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
import os
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bookings.db'
db = SQLAlchemy(app)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    date = db.Column(db.String(20))
    period = db.Column(db.String(20))
    plan = db.Column(db.String(50))
    people = db.Column(db.Integer)
    note = db.Column(db.String(200))

with app.app_context():
    db.create_all()

# 會把寄信結果印到 Render Logs
def send_email(to_email, subject, content):
    api_key = os.environ.get("SENDGRID_API_KEY")
    from_addr = os.environ.get("FROM_EMAIL")
    if not api_key or not from_addr:
        print("[SENDGRID] Missing SENDGRID_API_KEY or FROM_EMAIL")
        return False

    try:
        sg = sendgrid.SendGridAPIClient(api_key=api_key)
        mail = Mail(
            from_email=Email(from_addr),
            to_emails=To(to_email),
            subject=subject,
            plain_text_content=Content("text/plain", content)
        )
        resp = sg.client.mail.send.post(request_body=mail.get())
        print(f"[SENDGRID] to={to_email} status={resp.status_code}")
        # 202 表示 SendGrid 接收成功
        if resp.status_code == 202:
            return True
        else:
            print(f"[SENDGRID] body={resp.body}, headers={resp.headers}")
            return False
    except Exception as e:
        print(f"[SENDGRID] ERROR: {e}")
        return False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    name = request.form['name']
    phone = request.form['phone']
    email = request.form['email']
    date = request.form['date']
    period = request.form['period']
    plan = request.form['plan']
    people = request.form['people']
    note = request.form['note']

    # 儲存資料
    new_booking = Booking(
        name=name, phone=phone, email=email,
        date=date, period=period, plan=plan,
        people=people, note=note
    )
    db.session.add(new_booking)
    db.session.commit()

    # 管理員通知
    admin_email = os.environ.get("ADMIN_EMAIL")
    admin_content = (
        "📩 新潛水預約！\n\n"
        f"姓名：{name}\n電話：{phone}\nEmail：{email}\n"
        f"日期：{date}\n時段：{period}\n方案：{plan}\n人數：{people}\n備註：{note}\n"
    )
    send_email(admin_email, "來來潛水工作室 - 新預約通知", admin_content)

    # 客人確認信
    user_content = (
        f"親愛的 {name} 您好，感謝您的預約！\n\n"
        f"以下是您的潛水預約資訊：\n日期：{date}\n時段：{period}\n方案：{plan}\n人數：{people}\n\n"
        "我們將盡快與您聯繫確認行程！\n\n— 來來潛水工作室"
    )
    send_email(email, "來來潛水工作室 - 預約確認信", user_content)

    return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)


