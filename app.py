# --- کتابخانه‌های مورد نیاز ---
import cv2, os, time, threading, datetime, socket
from flask import Flask, render_template, Response, request, jsonify, redirect, session
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = 'AdminSecretKey'

# --- تنظیمات دیتابیس ---
# از نسخه 3 دیتابیس استفاده می‌کنیم تا همه فیلدها را داشته باشد
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///UniversityDB_V3.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# پوشه عکس‌ها
PHOTO_PATH = 'static/photos'
if not os.path.exists(PHOTO_PATH): os.makedirs(PHOTO_PATH)

# متغیرهای سراسری
frame_cam = None 
lock = threading.Lock()
admin_pass = "12345" 
last_scanned_card = "" 

# ----------------------------------------
# 🗄️ بخش مدل‌ها (دیتابیس)
# ----------------------------------------
class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String(50), unique=True)
    name = db.Column(db.String(100))
    p_code = db.Column(db.String(50))
    type = db.Column(db.String(50))
    photo = db.Column(db.String(100))
    balance = db.Column(db.Integer, default=0)
    hourly_rate = db.Column(db.Integer, default=0)
    national_id = db.Column(db.String(20), nullable=True)
    birth_date = db.Column(db.String(20), nullable=True)

class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String(50))
    date = db.Column(db.String(20))
    entry_time = db.Column(db.String(20))
    exit_time = db.Column(db.String(20))
    duration = db.Column(db.String(20))
    entry_pic = db.Column(db.String(100))
    exit_pic = db.Column(db.String(100))

# ----------------------------------------
# 📷 بخش دوربین و محاسبات
# ----------------------------------------
def cam_thread():
    global frame_cam
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    while True:
        ret, frame = cap.read()
        if ret:
            with lock: frame_cam = frame.copy()
        time.sleep(0.03)

def calculate_salary_data():
    users = Users.query.all()
    salary_list = []
    for u in users:
        logs = Log.query.filter_by(uid=u.uid).filter(Log.duration != None).all()
        total_seconds = 0
        for l in logs:
            try:
                h, m, s = map(int, l.duration.split(':'))
                total_seconds += h*3600 + m*60 + s
            except: pass
        total_hours = round(total_seconds / 3600, 2)
        total_pay = int(total_hours * u.hourly_rate)
        salary_list.append({
            "name": u.name, "uid": u.uid, "type": u.type, "rate": u.hourly_rate,
            "total_hours": total_hours, "total_pay": "{:,}".format(total_pay)
        })
    return salary_list

# ----------------------------------------
# 🧠 ارتباط با آردوینو
# ----------------------------------------
@app.route('/rfid_scan', methods=['POST'])
def rfid():
    global last_scanned_card
    uid = request.json.get('uid').strip().upper()
    last_scanned_card = uid 
    
    current_pic_name = f"{uid}_{int(time.time())}.jpg"
    with lock:
        if frame_cam is not None: cv2.imwrite(os.path.join(PHOTO_PATH, current_pic_name), frame_cam)

    u = Users.query.filter_by(uid=uid).first()
    if not u:
        return jsonify({"status": "Unknown", "name": "Unknown", "msg_fa": "کارت ناشناس", "dur": "-"}), 200

    now = datetime.datetime.now()
    d_str = now.strftime("%Y/%m/%d")
    t_str = now.strftime("%H:%M:%S")

    log = Log.query.filter_by(uid=uid, date=d_str, exit_time=None).first()

    if log:
        log.exit_time = t_str
        log.exit_pic = current_pic_name
        t1 = datetime.datetime.strptime(log.entry_time, "%H:%M:%S")
        t2 = datetime.datetime.strptime(t_str, "%H:%M:%S")
        seconds = (t2 - t1).total_seconds()
        log.duration = str(datetime.timedelta(seconds=int(seconds)))
        db.session.commit()
        return jsonify({"status": "Exit", "name": u.name.split()[0], "msg_fa": "خروج موفق", "dur": log.duration}), 200
    else:
        new_log = Log(uid=uid, date=d_str, entry_time=t_str, entry_pic=current_pic_name)
        db.session.add(new_log)
        db.session.commit()
        return jsonify({"status": "Enter", "name": u.name.split()[0], "msg_fa": "ورود موفق", "dur": "-"}), 200

# ----------------------------------------
# 🌐 روت‌های وب (پنل مدیریت)
# ----------------------------------------
@app.route('/')
def index():
    if not session.get('logged_in'): return redirect('/login')
    
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    logs = db.session.query(Log, Users).outerjoin(Users, Log.uid == Users.uid).order_by(Log.id.desc()).all()
    salary_data = calculate_salary_data()
    total_users = Users.query.count()
    today = datetime.datetime.now().strftime("%Y/%m/%d")
    present_today = Log.query.filter_by(date=today).count()
    
    return render_template('admin_panel.html', 
                           logs=logs, users=Users.query.all(), salary_data=salary_data,
                           stat={"total": total_users, "present": present_today, "absent": total_users - present_today},
                           my_ip=local_ip)

@app.route('/api/get_logs')
def get_logs_api():
    logs = db.session.query(Log, Users).outerjoin(Users, Log.uid == Users.uid).order_by(Log.id.desc()).limit(20).all()
    data = []
    for l, u in logs:
        data.append({
            "u_photo": u.photo if u else "", "l_entry_pic": l.entry_pic, "l_exit_pic": l.exit_pic,
            "name": u.name if u else "ناشناس", "p_code": u.p_code if u else "-",
            "entry": l.entry_time, "exit": l.exit_time if l.exit_time else "---",
            "dur": l.duration if l.duration else "---", "is_out": True if l.exit_time else False
        })
    return jsonify(data)

@app.route('/login', methods=['GET', 'POST'])
def login():
    global admin_pass
    if request.method == 'POST':
        if request.form['password'] == admin_pass:
            session['logged_in'] = True
            return redirect('/')
        else: return "رمز اشتباه است! <a href='/login'>بازگشت</a>"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect('/login')

@app.route('/change_pass', methods=['POST'])
def change_pass():
    global admin_pass
    if session.get('logged_in'): admin_pass = request.form['new_pass']
    return redirect('/')

@app.route('/register_user', methods=['POST'])
def register_user():
    uid = request.form['uid']
    name = request.form['name']
    p_code = request.form['p_code']
    u_type = request.form['type']
    try: h_rate = int(request.form['hourly_rate'])
    except: h_rate = 0
    nid = request.form.get('national_id', '')
    bdate = request.form.get('birth_date', '')

    pic_name = None
    with lock:
        if frame_cam is not None: 
            pic_name = f"Profile_{uid}.jpg"
            cv2.imwrite(os.path.join(PHOTO_PATH, pic_name), frame_cam)

    existing = Users.query.filter_by(uid=uid).first()
    if existing:
        existing.name = name; existing.p_code = p_code; existing.type = u_type; existing.hourly_rate = h_rate
        existing.national_id = nid; existing.birth_date = bdate
        if pic_name: existing.photo = pic_name
    else:
        if not pic_name: pic_name = "default.jpg"
        db.session.add(Users(uid=uid, name=name, p_code=p_code, type=u_type, photo=pic_name, hourly_rate=h_rate, national_id=nid, birth_date=bdate))
    db.session.commit()
    return redirect('/')

@app.route('/delete_user/<uid>')
def delete_user(uid):
    Users.query.filter_by(uid=uid).delete()
    db.session.commit()
    return redirect('/')

@app.route('/video_feed')
def video_feed():
    def gen():
        while True:
            with lock:
                if frame_cam is not None:
                    yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + cv2.imencode('.jpg', frame_cam)[1].tobytes() + b'\r\n')
            time.sleep(0.05)
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/get_last_card')
def get_last_card():
    return jsonify({"card": last_scanned_card}) 

# ==========================================
# 📱 بخش موبایل و کیف پول و رسید
# ==========================================
@app.route('/charge_wallet', methods=['POST'])
def charge_wallet():
    uid = request.form.get('uid')
    try: amount = int(request.form['amount'])
    except: amount = 0
    
    if uid: uid = uid.replace(":", "").replace(" ", "").upper()

    u = Users.query.filter_by(uid=uid).first()
    if u:
        u.balance += amount
        db.session.commit()
        
        # اگر از موبایل بود، رسید را نشان بده
        if request.form.get('source') == 'mobile':
            # فرمت بندی پول (سه رقم سه رقم)
            fmt_amount = "{:,}".format(amount)
            fmt_balance = "{:,}".format(u.balance)
            return render_template('charge_receipt.html', name=u.name, amount=fmt_amount, balance=fmt_balance)

    return redirect('/')

@app.route('/mobile')
def mobile_app():
    users = Users.query.all()
    return render_template('mobile.html', users=users)

if __name__ == '__main__':
    with app.app_context(): db.create_all()
    threading.Thread(target=cam_thread, daemon=True).start()
    print("--- System Started ---")
    app.run(host='0.0.0.0', port=5001, debug=False, threaded=True)