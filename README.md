# 🎓 RIT Attendance Tracker (Flask + Selenium)

A Flask-based web application that scrapes and displays attendance data from the RIT CMS portal using Selenium automation.  
Includes an **admin dashboard** to monitor logs, system stats, and user sessions in real time.

---

## 🚀 Features

- **User Interface** – Simple front-end built with Flask templates.
- **Attendance Scraper** – Uses Selenium and BeautifulSoup to fetch attendance from multiple RIT CMS URLs.
- **Live Logging** – Real-time logging of user actions (login, scrape, download).
- **Admin Dashboard** – Password-protected interface showing:
  - Real-time server logs (via Server-Sent Events)
  - Unique user tracking
  - System stats (CPU, Memory, Disk)
- **Excel Export** – Download attendance data in `.xlsx` format.
- **Proxy & Reverse Proxy Support** – Works on Render, Replit, or local servers.

---

## 🧰 Tech Stack

| Component | Technology |
|------------|-------------|
| Backend | Flask (Python) |
| Web Scraping | Selenium + BeautifulSoup |
| Data Handling | Pandas, NumPy |
| Frontend | HTML + Flask Templates |
| Logging | Python Logging + Thread-safe Queue |
| Deployment | Works on Render / Replit / Localhost |

---

## ⚙️ Installation

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/rit-attendance-tracker.git
cd rit-attendance-tracker
2️⃣ Create a Virtual Environment
bash
Copy code
python -m venv venv
venv\Scripts\activate   # For Windows
# or
source venv/bin/activate  # For macOS/Linux
3️⃣ Install Dependencies
bash
Copy code
pip install -r requirements.txt
If you don’t have requirements.txt, create one:

bash
Copy code
pip install flask selenium pandas numpy beautifulsoup4 psutil
pip freeze > requirements.txt
4️⃣ Run Locally
bash
Copy code
python app.py
App runs on:
👉 http://127.0.0.1:5000
Admin Dashboard:
🔐 http://127.0.0.1:5000/admin?password=password

🧩 Folder Structure
pgsql
Copy code
rit-attendance-tracker/
│
├── app.py
├── templates/
│   ├── index.html
│   └── admin.html
├── static/
│   ├── style.css
│   └── script.js
├── requirements.txt
└── README.md
🔒 Admin Dashboard
You can view logs, system stats, and connected users:

/admin?password=password

/admin/logs

/admin/stats

/admin/users

To secure your app:

Change ADMIN_PASSWORD in app.py.



🪪 License
This project is licensed under the MIT License — feel free to use and modify it.
