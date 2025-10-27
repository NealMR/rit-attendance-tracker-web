from flask import Flask, render_template, request, jsonify, send_file
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
import pandas as pd
import numpy as np
import os
import time
from datetime import datetime
from bs4 import BeautifulSoup
import io
import json

app = Flask(__name__)

# URLs to try
RIT_URLS = [
    "http://210.212.171.172/ritcms/Default.aspx",
    "http://172.22.4.115/ritcms/Default.aspx",
    "http://ritage.ritindia.edu/RITCMS/Default.aspx"
]

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
    chrome_options.add_argument('--disable-software-rasterizer')
    
    # For Render.com deployment
    chrome_options.binary_location = '/usr/bin/chromium'
    
    driver = None
    try:
        driver = webdriver.Chrome(options=chrome_options)
        
        # Try connecting to RIT CMS
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
            return {"error": "Failed to connect to RIT CMS portal"}
        
        # Login
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
        
        # Check for login error
        try:
            error_msg = driver.find_element(By.ID, "lbl_err")
            if error_msg.is_displayed() and "Invalid" in error_msg.text:
                return {"error": "Invalid credentials"}
        except:
            pass
        
        # Check if dashboard loaded
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//img[@src='../images/attendance1.jpg']"))
            )
        except:
            return {"error": "Login failed - Dashboard not loaded"}
        
        # Click on Attendance Dashboard
        attendance_image = driver.find_element(By.XPATH, "//img[@src='../images/attendance1.jpg']")
        attendance_image.click()
        time.sleep(3)
        
        # Extract attendance data
        select_buttons = driver.find_elements(By.XPATH, "//input[@type='button' and @value='Select']")
        num_subjects = len(select_buttons)
        
        subject_stats = []
        
        for i in range(num_subjects):
            select_buttons = driver.find_elements(By.XPATH, "//input[@type='button' and @value='Select']")
            select_buttons[i].click()
            time.sleep(2.5)
            
            try:
                tables = pd.read_html(driver.page_source, attrs={'id': 'GridViewAttendedance'})
                if tables:
                    df = tables[0]
                    df.columns = ['StaffCode', 'SubjectCode', 'TheoryPractical', 'AttenDate', 'LectureTime', 'Attendance']
                    
                    # Get subject name
                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    caption = soup.find('table', {'id': 'GridViewAttendedance'}).find('caption')
                    subject_name = caption.text.strip() if caption else "Unknown"
                    
                    # Parse dates
                    df['AttenDate'] = pd.to_datetime(df['AttenDate'], format='%d/%m/%Y', errors='coerce')
                    latest_date = df['AttenDate'].max()
                    
                    # Calculate stats (REMOVED classes needed/can miss calculations)
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
            
            # Click Back
            try:
                back_buttons = driver.find_elements(By.XPATH, "//input[@type='button' and @value='Back']")
                if back_buttons:
                    back_buttons[0].click()
                    time.sleep(1.8)
            except:
                pass
        
        # Calculate overall stats
        if subject_stats:
            summary_df = pd.DataFrame(subject_stats)
            total_classes = int(summary_df['TotalClasses'].sum())
            total_present = int(summary_df['Present'].sum())
            total_absent = int(summary_df['Absent'].sum())
            overall_percentage = float((total_present / total_classes * 100) if total_classes > 0 else 0)
            
            result = {
                "success": True,
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
            return {"error": "No attendance data found"}
            
    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}
    finally:
        if driver:
            driver.quit()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scrape', methods=['POST'])
def scrape():
    data = request.get_json()
    user_id = data.get('user_id')
    password = data.get('password')
    
    if not user_id or not password:
        return jsonify({"error": "User ID and Password are required"}), 400
    
    result = get_attendance_data(user_id, password)
    return jsonify(result)

@app.route('/download', methods=['POST'])
def download():
    data = request.get_json()
    subjects = data.get('subjects', [])
    
    if not subjects:
        return jsonify({"error": "No data to download"}), 400
    
    df = pd.DataFrame(subjects)
    
    # Create CSV in memory
    output = io.BytesIO()
    df.to_csv(output, index=False)
    output.seek(0)
    
    return send_file(
        io.BytesIO(output.getvalue()),
        mimetype='text/csv',
        as_attachment=True,
        download_name='attendance_summary.csv'
    )

if __name__ == '__main__':
    # Disable dotenv loading to prevent UTF-8 encoding errors
    app.run(host='127.0.0.1', port=5000, debug=True, load_dotenv=False)
