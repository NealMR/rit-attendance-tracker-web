# 🎓 RIT Attendance Tracker Web

A robust Flask-based web application designed to automatically fetch and analyze attendance data from the RIT CMS portal using **Selenium automation**.  
Includes a password-protected **Admin Dashboard** to monitor user activity, system performance, and real-time logs.

---

## 🧭 Overview

The **RIT Attendance Tracker** simplifies attendance management for students and administrators by automating the retrieval and visualization of attendance data.  
It provides detailed analytics, secure user tracking, and a streamlined interface for monitoring activity.

---

## ✨ Key Features

### 🧑‍🎓 Student Portal
- Securely fetches attendance data directly from RIT CMS.
- Displays subject-wise attendance summary with total, present, and absent counts.
- Allows users to **download reports in Excel format**.

### 🛠️ Automation & Scraping
- Uses **Selenium WebDriver** for browser automation.
- Parses attendance data with **BeautifulSoup** and **Pandas**.
- Supports multiple CMS URLs for reliability and fallback.

### 🧩 Admin Dashboard
- Password-protected admin access.
- Real-time system stats (CPU, memory, disk).
- Live log streaming via **Server-Sent Events (SSE)**.
- Tracks unique users and session history.

### 📊 Logging & Analytics
- Detailed user activity logs (scrape, download, new user, etc.).
- Thread-safe, in-memory logging using Python `deque`.
- Live update view on the admin panel.

---

## 🧰 Tech Stack

| Category | Technology |
|-----------|-------------|
| **Backend** | Flask (Python) |
| **Web Scraping** | Selenium, BeautifulSoup |
| **Data Handling** | Pandas, NumPy |
| **Frontend** | HTML, CSS (Flask Templates) |
| **System Monitoring** | psutil |
| **Logging** | Python logging module + LiveLogHandler |
| **Concurrency** | threading, deque |
| **File Export** | Excel (.xlsx) via Pandas and XlsxWriter |

---

## ⚙️ Installation & Setup

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/NealMR/rit-attendance-tracker-web.git
cd rit-attendance-tracker-web
```
###2️⃣ Create a Virtual Environment
```bash
Copy code
python -m venv venv
venv\Scripts\activate   # For Windows
# or
source venv/bin/activate   # For macOS/Linux
```
###3️⃣ Install Dependencies
```bash
Copy code
pip install -r requirements.txt
If you don’t have requirements.txt, generate it:
```
```bash
Copy code
pip install flask selenium pandas numpy beautifulsoup4 psutil xlsxwriter
pip freeze > requirements.txt
```
###4️⃣ Run the Application
```bash
Copy code
python app.py
```
App will start locally at:


Copy code
```
http://127.0.0.1:5000
```
🗂️ Project Structure
csharp
Copy code
rit-attendance-tracker-web/
│
├── app.py                     # Main Flask application
├── templates/
│   ├── index.html             # User portal
│   └── admin.html             # Admin dashboard
├── static/
│   ├── style.css              # Stylesheet
│   └── script.js              # Frontend interactivity
├── requirements.txt
└── README.md
🔒 Security Notes
The admin dashboard is protected with a password defined in app.py:

python
Copy code
```
ADMIN_PASSWORD = "password"
```
🔐 Change this immediately before using in production.

All user activities and requests are logged with timestamps and IP addresses.

The scraper uses headless Chrome for automation.

🧑‍💻 Author
   NealMR
 

🪪 License
This project is released under the MIT License.
You’re free to use, modify, and distribute it with attribution.

