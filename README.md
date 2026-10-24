# 🎓 Smart IoT Attendance System (NFC + Face Verification)

[فارسی](README.fa.md) | **English**

An IoT-based attendance system for universities and workplaces. Users tap an **RFID/NFC card** on an **ESP32** reader, the server captures a **camera photo** for face verification, logs the entry or exit, and automatically calculates working hours and salary. Everything is managed through a **Flask web dashboard**.

---

## ✨ Features

- 🪪 Entry/exit logging by tapping an RFID/NFC card
- 🙂 Face verification stage after the card scan
- 📸 Automatic photo capture from the camera on every entry and exit
- ⏱ Automatic calculation of the duration of each session
- 💰 Total working hours and salary per user, based on an hourly rate
- 👥 User registration and editing (name, personnel code, national ID, birth date, user type, hourly rate, profile photo)
- 📊 Dashboard statistics: total, present, and absent users
- 📟 Live feedback on an OLED display (welcome, goodbye, work time, errors)
- 🔄 JSON API for the 20 latest logs
- 🔐 Password-protected admin panel with password change

---

## 🏗 System Architecture

```
┌────────────────┐   UID    ┌───────────────┐  HTTP POST   ┌─────────────────────┐
│ RFID/NFC card  │ ───────► │     ESP32     │ ───────────► │    Flask server     │
└────────────────┘          │ + RC522 + OLED│ /rfid_scan   │                     │
                            └───────────────┘ ◄─────────── │ • Entry/exit log    │
                                   ▲            JSON reply │ • Camera capture    │
                                   │                       │ • Face verification │
                          Status shown on OLED             │ • SQLite database   │
                                                           └──────────┬──────────┘
                                         ┌──────────────┐             ▼
                                         │  USB webcam  │     ┌───────────────┐
                                         │   (OpenCV)   │     │ Admin dashboard│
                                         └──────────────┘     └───────────────┘
```

**Workflow**
1. The user taps a card on the RC522 reader.
2. The ESP32 sends the card UID to the server over Wi-Fi.
3. The server captures a photo and verifies the identity.
4. If the user has an open session (entry without exit), an **exit** is logged; otherwise a new **entry** is created.
5. The server replies with the user's name, status, and session duration, which the ESP32 shows on the OLED.

---

## 🧰 Hardware

| Component | Purpose |
|-----------|---------|
| ESP32 | Wi-Fi connection and sending UIDs to the server |
| RC522 (MFRC522) RFID module | Reading cards over SPI |
| SSD1306 OLED display (128×64) | Showing status and messages over I2C |
| USB webcam | Photo capture and face verification |
| Computer / server | Runs the Flask application |

**Wiring**

| Part | Pin |
|------|-----|
| RC522 – SDA (SS) | GPIO 5 |
| RC522 – RST | GPIO 4 |
| RC522 – SCK / MOSI / MISO | Default ESP32 SPI pins |
| SSD1306 – SDA / SCL | Default ESP32 I2C pins (address `0x3C`) |

---

## 🛠 Tech Stack

- **Python 3**, **Flask**, **Flask-SQLAlchemy**
- **SQLite**
- **OpenCV** (camera capture and image processing)
- **ESP32 / Arduino (C++)** with `MFRC522`, `Adafruit_SSD1306`, `Adafruit_GFX`, `ArduinoJson`
- HTML / CSS / JavaScript for the dashboard

---

## 📁 Project Structure

```
IOT_Project/
├── app.py                      # Flask application
├── requirements.txt
├── templates/
│   ├── admin_panel.html        # Admin dashboard
│   ├── login.html              # Login page
│   ├── register.html           # User registration
│   ├── index.html
│   ├── mobile.html
│   └── charge_receipt.html
├── static/
│   ├── style.css
│   ├── photos/                 # Entry/exit photos (not committed)
│   └── profile_pics/           # Profile pictures (not committed)
├── arduino/
│   └── rfid_client/
│       └── rfid_client.ino     # ESP32 firmware
├── .gitignore
├── LICENSE
└── README.md
```

---

## 🚀 Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/<username>/<repo-name>.git
cd <repo-name>
```

### 2. Create a virtual environment and install dependencies
```bash
python -m venv venv
venv\Scripts\activate           # Windows
# source venv/bin/activate      # Linux / macOS

pip install flask flask-sqlalchemy opencv-python
```

### 3. Create the database
```python
from app import app, db
with app.app_context():
    db.create_all()
```

### 4. Run the server
`app.py` should end with:

```python
if __name__ == '__main__':
    threading.Thread(target=cam_thread, daemon=True).start()
    app.run(host='0.0.0.0', port=5001, debug=False)
```

```bash
python app.py
```

Open the dashboard at `http://<server-ip>:5001`.

> ⚠️ The camera code uses `cv2.CAP_DSHOW`, which is **Windows-only**. On Linux/macOS use `cv2.VideoCapture(0)`.

### 5. Flash the ESP32
1. Install the libraries from the Arduino Library Manager: `MFRC522`, `Adafruit GFX Library`, `Adafruit SSD1306`, `ArduinoJson`.
2. Open `arduino/rfid_client/rfid_client.ino` and set:
   ```cpp
   const char* ssid = "WIFI_NAME";
   const char* pass = "WIFI_PASSWORD";
   String laptop_ip = "192.168.1.2";   // IP of the computer running the server
   ```
3. Upload to the ESP32. The ESP32 and the server must be on the same network.

---

## 🔌 API

### `POST /rfid_scan`
Sent by the ESP32 whenever a card is scanned.

**Request**
```json
{ "uid": "A1B2C3D4" }
```

**Responses**

| Case | Example |
|------|---------|
| Entry | `{"status":"Enter","name":"Ali","msg_fa":"ورود موفق","dur":"-"}` |
| Exit | `{"status":"Exit","name":"Ali","msg_fa":"خروج موفق","dur":"8:15:30"}` |
| Unknown card | `{"status":"Unknown","name":"Unknown","msg_fa":"کارت ناشناس","dur":"-"}` |

### Other routes

| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Admin dashboard |
| `/login` | GET/POST | Admin login |
| `/logout` | GET | Log out |
| `/change_pass` | POST | Change the admin password |
| `/register_user` | POST | Create or update a user |
| `/api/get_logs` | GET | Latest 20 logs as JSON |

---

## 🗄 Database Schema

**Users**

| Field | Description |
|-------|-------------|
| `uid` | Unique card ID |
| `name` | Full name |
| `p_code` | Personnel / student code |
| `type` | User type |
| `photo` | Profile photo |
| `balance` | Account balance |
| `hourly_rate` | Hourly pay rate |
| `national_id` | National ID |
| `birth_date` | Birth date |

**Log**

| Field | Description |
|-------|-------------|
| `uid` | Card ID |
| `date` | Date |
| `entry_time` / `exit_time` | Entry / exit time |
| `duration` | Session duration (`H:MM:SS`) |
| `entry_pic` / `exit_pic` | Entry / exit photos |

---

## 🔐 Security Notes

Before using this in a real environment:

- Move `secret_key` and the default admin password out of the source code and into **environment variables**.
- Store the admin password **hashed** (e.g. `werkzeug.security`).
- Protect `/api/get_logs`, `/change_pass` and `/register_user` with a session check.
- Protect `/rfid_scan` with an **API token** shared with the ESP32.
- Never commit Wi-Fi credentials, the database, or user photos. They contain personal data.

Recommended `.gitignore`:
```
venv/
__pycache__/
*.db
instance/
static/photos/*
static/profile_pics/*
!static/photos/.gitkeep
!static/profile_pics/.gitkeep
.env
```

---

## 📸 Screenshots

_Add screenshots of the dashboard, the OLED display, and the hardware setup here._

```
docs/dashboard.png
docs/hardware.jpg
```

---

## 🗺 Roadmap

- [ ] Excel / PDF export for attendance and salary reports
- [ ] Live camera view in the dashboard
- [ ] Role-based access (admin, operator)
- [ ] Late and absence notifications
- [ ] More accurate face recognition
- [ ] Docker support

---

## 🤝 Contributing

Issues and pull requests are welcome. Fork the repository, create a feature branch, and open a pull request.

## 📄 License

Released under the **MIT License**.

## 👤 Author

Amin Yavari — [GitHub]https://github.com/aminyvri
