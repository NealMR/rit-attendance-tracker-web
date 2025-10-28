from flask import Flask, render_template, request, jsonify, send_file, g, Response
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
from werkzeug.middleware.proxy_fix import ProxyFix
import pandas as pd
import numpy as np
import os
import time
from datetime import datetime
from bs4 import BeautifulSoup
import io
from io import StringIO
import json
import logging
from logging.config import dictConfig
import psutil
from collections import deque
import threading

# Global log storage for live dashboard
live_logs = deque(maxlen=500)
log_lock = threading.Lock()

# Track unique users who have used the website
unique_users = set()
user_lock = threading.Lock()

# Track user sessions with timestamps
user_sessions = {}
session_lock = threading.Lock()

# Admin password - CHANGE THIS!
ADMIN_PASSWORD = "password"

# Custom handler to capture logs
class LiveLogHandler(logging.Handler):
    def emit(self, record):
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S'),
            'level': record.levelname,
            'message': self.format(record)
        }
        with log_lock:
            live_logs.append(log_entry)

# Configure detailed user activity logging
dictConfig({
    'version': 1,
    'formatters': {
        'user_activity': {
            'format': '%(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout',
            'formatter': 'user_activity',
            'level': 'INFO'
        },
        'live': {
            '()': LiveLogHandler,
            'formatter': 'user_activity',
            'level': 'INFO'
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console', 'live']
    }
})

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

# Disable werkzeug request logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Configure ProxyFix for port forwarding / reverse proxy
app.wsgi_app = ProxyFix(
    app.wsgi_app,
    x_for=1,
    x_proto=1,
    x_host=1,
    x_prefix=1
)

# URLs to try
RIT_URLS = [
    "http://210.212.171.172/ritcms/Default.aspx",
    "http://172.22.4.115/ritcms/Default.aspx",
    "http://ritage.ritindia.edu/RITCMS/Default.aspx"
]

# Track admin stats requests to log only once
admin_stats_logged = False

def add_user(user_id, ip):
    """Add user to tracking system"""
    with user_lock:
        is_new = user_id not in unique_users
        unique_users.add(user_id)
    
    with session_lock:
        user_sessions[user_id] = {
            'last_seen': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'ip': ip
        }
    
    return is_new

# Request timing and monitoring hooks
@app.before_request
def before_request():
    """Start timer and capture system stats before request"""
    if request.path.startswith('/admin'):
        return
    
    g.start_time = time.time()
    g.cpu_before = psutil.cpu_percent(interval=0.1)
    g.memory_before = psutil.virtual_memory().percent

@app.after_request
def after_request(response):
    """Log request time and system load after request"""
    if request.path.startswith('/admin'):
        return response
    
    if hasattr(g, 'start_time'):
        elapsed_time = (time.time() - g.start_time) * 1000
        cpu_after = psutil.cpu_percent(interval=0.1)
        memory_after = psutil.virtual_memory().percent
        real_ip = get_real_ip()
        
        if response.status_code >= 200 and response.status_code < 300:
            status = "SUCCESS"
        elif response.status_code >= 400 and response.status_code < 500:
            status = "CLIENT_ERROR"
        elif response.status_code >= 500:
            status = "SERVER_ERROR"
        else:
            status = "REDIRECT"
        
        app.logger.info(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
            f"REQUEST: {request.method} {request.path} | "
            f"IP: {real_ip} | "
            f"STATUS: {status} ({response.status_code}) | "
            f"TIME: {elapsed_time:.2f}ms | "
            f"CPU: {cpu_after:.1f}% | "
            f"MEMORY: {memory_after:.1f}%"
        )
    
    return response

def get_real_ip():
    """Get the real IP address of the client, even behind proxy/port forwarding"""
    if 'X-Forwarded-For' in request.headers:
        ip = request.headers['X-Forwarded-For'].split(',')[0].strip()
        return ip
    
    if 'X-Real-IP' in request.headers:
        return request.headers['X-Real-IP']
    
    return request.remote_addr

def get_system_stats():
    """Get current system statistics"""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return {
        'cpu_percent': cpu_percent,
        'memory_percent': memory.percent,
        'memory_used_gb': memory.used / (1024 ** 3),
        'memory_total_gb': memory.total / (1024 ** 3),
        'disk_percent': disk.percent,
        'disk_used_gb': disk.used / (1024 ** 3),
        'disk_total_gb': disk.total / (1024 ** 3)
    }

def convert_to_native_types(data):
    """Convert numpy/pandas types to native Python types"""
    if isinstance(data, dict):
        return {k: convert_to_native_types(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_to_native_types(item) for item in data]
    elif isinstance(data, (np.integer, np.int64)):
        return int(data)
    elif isinstance(data, (np.floating, np.float64)):
        return float(data)
    elif isinstance(data, np.ndarray):
        return data.tolist()
    else:
        return data

def get_attendance_data(user_id, password):
    """Scrape attendance data and return results"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    
    driver = None
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        
        connected = False
        current_url = None
        
        for url in RIT_URLS:
            try:
                driver.get(url)
                driver.set_page_load_timeout(8)
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.ID, "txt_UserId"))
                )
                connected = True
                current_url = url
                break
            except:
                continue
        
        if not connected:
            return {"error": "Failed to connect to RIT CMS portal", "status": "CONNECTION_FAILED"}
        
        time.sleep(1)
        username_field = driver.find_element(By.ID, "txt_UserId")
        username_field.clear()
        username_field.send_keys(user_id)
        
        password_field = driver.find_element(By.ID, "txt_password")
        password_field.clear()
        password_field.send_keys(password)
        
        login_button = driver.find_element(By.ID, "cmd_LogIn")
        login_button.click()
        time.sleep(3)
        
        try:
            error_msg = driver.find_element(By.ID, "lbl_err")
            if error_msg.is_displayed() and "Invalid" in error_msg.text:
                return {"error": "Invalid credentials", "status": "AUTH_FAILED"}
        except:
            pass
        
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//img[@src='../images/attendance1.jpg']"))
            )
        except:
            return {"error": "Login failed - Dashboard not loaded", "status": "LOGIN_FAILED"}
        
        attendance_image = driver.find_element(By.XPATH, "//img[@src='../images/attendance1.jpg']")
        attendance_image.click()
        time.sleep(3)
        
        select_buttons = driver.find_elements(By.XPATH, "//input[@type='button' and @value='Select']")
        num_subjects = len(select_buttons)
        subject_stats = []
        
        for i in range(num_subjects):
            select_buttons = driver.find_elements(By.XPATH, "//input[@type='button' and @value='Select']")
            select_buttons[i].click()
            time.sleep(2.5)
            
            try:
                tables = pd.read_html(StringIO(driver.page_source), attrs={'id': 'GridViewAttendedance'})
                
                if tables:
                    df = tables[0]
                    df.columns = ['StaffCode', 'SubjectCode', 'TheoryPractical', 'AttenDate', 'LectureTime', 'Attendance']
                    
                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    caption = soup.find('table', {'id': 'GridViewAttendedance'}).find('caption')
                    subject_name = caption.text.strip() if caption else "Unknown"
                    
                    df['AttenDate'] = pd.to_datetime(df['AttenDate'], format='%d/%m/%Y', errors='coerce')
                    latest_date = df['AttenDate'].max()
                    
                    total_classes = int(len(df))
                    present_count = int(len(df[df['Attendance'] == 'P']))
                    absent_count = int(len(df[df['Attendance'] == 'A']))
                    percentage = float((present_count / total_classes * 100) if total_classes > 0 else 0)
                    
                    subject_stats.append({
                        'Subject': subject_name,
                        'SubjectCode': str(df['SubjectCode'].iloc[0]) if len(df) > 0 else 'N/A',
                        'TotalClasses': total_classes,
                        'Present': present_count,
                        'Absent': absent_count,
                        'AttendancePercentage': round(percentage, 2),
                        'LatestAttendanceDate': latest_date.strftime('%d/%m/%Y') if pd.notna(latest_date) else 'N/A'
                    })
                    
            except Exception as e:
                continue
            
            try:
                back_buttons = driver.find_elements(By.XPATH, "//input[@type='button' and @value='Back']")
                if back_buttons:
                    back_buttons[0].click()
                    time.sleep(1.8)
            except:
                pass
        
        if subject_stats:
            summary_df = pd.DataFrame(subject_stats)
            total_classes = int(summary_df['TotalClasses'].sum())
            total_present = int(summary_df['Present'].sum())
            total_absent = int(summary_df['Absent'].sum())
            overall_percentage = float((total_present / total_classes * 100) if total_classes > 0 else 0)
            
            result = {
                "success": True,
                "status": "COMPLETED",
                "overall": {
                    "total_classes": total_classes,
                    "present": total_present,
                    "absent": total_absent,
                    "percentage": round(overall_percentage, 2)
                },
                "subjects": subject_stats
            }
            
            return convert_to_native_types(result)
        else:
            return {"error": "No attendance data found", "status": "NO_DATA"}
            
    except Exception as e:
        return {"error": f"An error occurred: {str(e)}", "status": "SYSTEM_ERROR"}
    
    finally:
        if driver:
            driver.quit()

# ==================== ADMIN ROUTES ====================

@app.route('/admin')
def admin_dashboard():
    """Admin dashboard - password protected"""
    global admin_stats_logged
    password = request.args.get('password', '')
    if password != ADMIN_PASSWORD:
        return "<h1>Access Denied</h1><p>Invalid password</p>", 403
    
    if not admin_stats_logged:
        app.logger.info(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
            f"ðŸ” ADMIN_ACCESS | IP: {get_real_ip()}"
        )
        admin_stats_logged = True
    
    return render_template('admin.html')

@app.route('/admin/logs')
def admin_logs():
    """Get logs for admin dashboard"""
    password = request.args.get('password', '')
    if password != ADMIN_PASSWORD:
        return jsonify({"error": "Access denied"}), 403
    
    with log_lock:
        return jsonify(list(live_logs))

@app.route('/admin/stats')
def admin_stats():
    """Get system stats for admin dashboard"""
    password = request.args.get('password', '')
    if password != ADMIN_PASSWORD:
        return jsonify({"error": "Access denied"}), 403
    
    stats = get_system_stats()
    return jsonify(stats)

@app.route('/admin/users')
def admin_users():
    """Get list of unique users who have used the website"""
    password = request.args.get('password', '')
    if password != ADMIN_PASSWORD:
        return jsonify({"error": "Access denied"}), 403
    
    with user_lock:
        users_list = sorted(list(unique_users))
    
    with session_lock:
        users_data = []
        for user_id in users_list:
            user_info = user_sessions.get(user_id, {})
            users_data.append({
                'user_id': user_id,
                'last_seen': user_info.get('last_seen', 'N/A'),
                'ip': user_info.get('ip', 'N/A')
            })
    
    return jsonify({
        'total_users': len(users_list),
        'users': users_data
    })

@app.route('/admin/stream')
def admin_stream():
    """Server-Sent Events stream for real-time logs"""
    password = request.args.get('password', '')
    if password != ADMIN_PASSWORD:
        return "Access Denied", 403
    
    def event_stream():
        last_index = len(live_logs)
        while True:
            time.sleep(1)
            with log_lock:
                current_logs = list(live_logs)
            
            if len(current_logs) > last_index:
                new_logs = current_logs[last_index:]
                for log in new_logs:
                    yield f"data: {json.dumps(log)}\n\n"
                last_index = len(current_logs)
    
    return Response(event_stream(), mimetype='text/event-stream')

# ==================== USER ROUTES ====================

@app.route('/')
def index():
    real_ip = get_real_ip()
    app.logger.info(
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
        f"ðŸŒ USER_ACCESS | IP: {real_ip}"
    )
    return render_template('index.html')

@app.route('/scrape', methods=['POST'])
def scrape():
    data = request.get_json()
    user_id = data.get('user_id')
    password = data.get('password')
    
    if not user_id or not password:
        return jsonify({"error": "User ID and Password are required"}), 400
    
    real_ip = get_real_ip()
    
    # Track user
    is_new_user = add_user(user_id, real_ip)
    
    # Log with IP and User ID side by side
    if is_new_user:
        with user_lock:
            total_users = len(unique_users)
        app.logger.info(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
            f"ðŸ†• NEW_USER | IP: {real_ip} | USER: {user_id} | TOTAL_USERS: {total_users}"
        )
    
    app.logger.info(
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
        f"ðŸ”„ SCRAPE_STARTED | IP: {real_ip} | USER: {user_id}"
    )
    
    scrape_start_time = time.time()
    result = get_attendance_data(user_id, password)
    scrape_duration = (time.time() - scrape_start_time) * 1000
    
    status = result.get('status', 'UNKNOWN')
    
    if result.get('success'):
        overall = result.get('overall', {})
        subjects_count = len(result.get('subjects', []))
        attendance_pct = overall.get('percentage', 0)
        
        app.logger.info(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
            f"âœ… SCRAPE_SUCCESS | IP: {real_ip} | USER: {user_id} | "
            f"STATUS: {status} | DURATION: {scrape_duration:.0f}ms | "
            f"SUBJECTS: {subjects_count} | ATTENDANCE: {attendance_pct}% | "
            f"PRESENT: {overall.get('present', 0)}/{overall.get('total_classes', 0)}"
        )
    else:
        error_msg = result.get('error', 'Unknown error')
        app.logger.info(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
            f"âŒ SCRAPE_FAILED | IP: {real_ip} | USER: {user_id} | "
            f"STATUS: {status} | DURATION: {scrape_duration:.0f}ms | ERROR: {error_msg}"
        )
    
    return jsonify(result)

@app.route('/download', methods=['POST'])
def download():
    data = request.get_json()
    subjects = data.get('subjects', [])
    
    if not subjects:
        return jsonify({"error": "No data to download"}), 400
    
    real_ip = get_real_ip()
    subjects_count = len(subjects)
    
    app.logger.info(
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
        f"ðŸ“¥ DOWNLOAD | IP: {real_ip} | SUBJECTS: {subjects_count}"
    )
    
    df = pd.DataFrame(subjects)
    
    column_order = [
        'Subject',
        'SubjectCode',
        'TotalClasses',
        'Present',
        'Absent',
        'AttendancePercentage',
        'LatestAttendanceDate'
    ]
    df = df[column_order]
    
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Attendance Summary', index=False)
        
        workbook = writer.book
        worksheet = writer.sheets['Attendance Summary']
        
        for idx, col in enumerate(df.columns):
            max_len = max(
                df[col].astype(str).apply(len).max(),
                len(str(col))
            )
            worksheet.set_column(idx, idx, max_len + 2)
    
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='attendance_summary.xlsx'
    )

if __name__ == '__main__':
    stats = get_system_stats()
    print("=" * 70)
    print("Flask Attendance Tracker - User Activity Monitor")
    print("Server: http://127.0.0.1:5000")
    print(f"Admin Dashboard: http://127.0.0.1:5000/admin?password={ADMIN_PASSWORD}")
    print("-" * 70)
    print(f"SYSTEM STATUS:")
    print(f"  CPU: {stats['cpu_percent']:.1f}%")
    print(f"  Memory: {stats['memory_percent']:.1f}% ({stats['memory_used_gb']:.2f}GB / {stats['memory_total_gb']:.2f}GB)")
    print(f"  Disk: {stats['disk_percent']:.1f}% ({stats['disk_used_gb']:.2f}GB / {stats['disk_total_gb']:.2f}GB)")
    print("=" * 70)
    
    app.run(host='127.0.0.1', port=5000, debug=True, load_dotenv=False, threaded=True)