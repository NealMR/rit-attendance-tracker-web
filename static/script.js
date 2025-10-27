let attendanceData = null;

// Realistic progress matching actual scraping operations
function realisticProgress() {
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    const progressStatus = document.getElementById('progressStatus');
    
    // Based on actual code flow from attendance_scraper.py
    const stages = [
        { percent: 3, duration: 300, message: "Initializing Chrome browser..." },
        { percent: 8, duration: 800, message: "Connecting to RIT CMS portal..." },
        { percent: 15, duration: 1500, message: "Attempting connection (210.212.171.172)..." },
        { percent: 20, duration: 500, message: "Waiting for login page to load..." },
        { percent: 25, duration: 1000, message: "Entering credentials..." },
        { percent: 30, duration: 800, message: "Submitting login form..." },
        { percent: 38, duration: 3000, message: "Verifying credentials..." },
        { percent: 42, duration: 1200, message: "Checking authentication..." },
        { percent: 48, duration: 1500, message: "Loading student dashboard..." },
        { percent: 52, duration: 800, message: "Waiting for dashboard elements..." },
        { percent: 58, duration: 1000, message: "Opening attendance section..." },
        { percent: 62, duration: 2500, message: " Processing data..." },
        { percent: 68, duration: 1000, message: "Extracting subject list..." },
        { percent: 72, duration: 1500, message: "Found subjects - Processing data..." },
        { percent: 78, duration: 2000, message: " Processing data..." },
        { percent: 82, duration: 2500, message: "Reading attendance table..." },
        { percent: 86, duration: 1500, message: "Parsing dates and calculating stats..." },
        { percent: 90, duration: 1800, message: "Processing remaining subjects..." },
        { percent: 94, duration: 1000, message: "Calculating overall attendance..." },
        { percent: 97, duration: 800, message: "Generating summary..." }
    ];
    
    let currentStage = 0;
    
    function updateProgress() {
        if (currentStage < stages.length) {
            const stage = stages[currentStage];
            progressFill.style.width = stage.percent + '%';
            progressText.textContent = stage.percent + '%';
            progressStatus.textContent = stage.message;
            
            currentStage++;
            setTimeout(updateProgress, stage.duration);
        }
    }
    
    updateProgress();
}

// Show inline error message on the form
function showInlineError(message) {
    const form = document.getElementById('attendanceForm');
    
    // Remove any existing error messages
    const existingError = document.querySelector('.form-error');
    if (existingError) {
        existingError.remove();
    }
    
    // Create error message element
    const errorDiv = document.createElement('div');
    errorDiv.className = 'form-error';
    errorDiv.innerHTML = `
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <circle cx="10" cy="10" r="9" stroke="currentColor" stroke-width="2"/>
            <path d="M10 6v4M10 14h.01" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        </svg>
        <span>${message}</span>
    `;
    
    // Insert error before the submit button
    const submitBtn = form.querySelector('button[type="submit"]');
    form.insertBefore(errorDiv, submitBtn);
    
    // Shake animation
    errorDiv.style.animation = 'shake 0.5s';
}

document.getElementById('attendanceForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const userId = document.getElementById('userId').value;
    const password = document.getElementById('password').value;
    
    // Show loading with progress
    document.getElementById('loginForm').style.display = 'none';
    document.getElementById('loading').style.display = 'block';
    document.getElementById('error').style.display = 'none';
    
    // Reset progress
    document.getElementById('progressFill').style.width = '0%';
    document.getElementById('progressText').textContent = '0%';
    document.getElementById('progressStatus').textContent = 'Starting browser...';
    
    // Start realistic progress
    realisticProgress();
    
    try {
        const response = await fetch('/scrape', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ user_id: userId, password: password })
        });
        
        const data = await response.json();
        
        if (data.error) {
            // Return to login page with error message
            document.getElementById('loading').style.display = 'none';
            document.getElementById('loginForm').style.display = 'block';
            
            // Show inline error on the form
            showInlineError(data.error);
        } else {
            // Only NOW set to 100% when data is actually received
            document.getElementById('progressFill').style.width = '100%';
            document.getElementById('progressText').textContent = '100%';
            document.getElementById('progressStatus').textContent = 'Complete! Summary generated.';
            
            setTimeout(() => {
                attendanceData = data;
                displayResults(data);
            }, 800);
        }
    } catch (error) {
        // Return to login page on network error
        document.getElementById('loading').style.display = 'none';
        document.getElementById('loginForm').style.display = 'block';
        showInlineError('Network error. Please check your connection and try again.');
    }
});

function displayResults(data) {
    document.getElementById('loading').style.display = 'none';
    document.getElementById('results').style.display = 'block';
    
    // Display overall stats
    const overall = data.overall;
    const statusIcon = overall.percentage >= 75 ? '✅' : '⚠️';
    const statusMessage = overall.percentage >= 75 
        ? '✅ Great! You have maintained above 75% attendance' 
        : '⚠️ Your attendance is below 75% threshold';
    
    const overallHtml = `
        <h3>${statusIcon} Overall Attendance</h3>
        <div class="stat-grid">
            <div class="stat-item">
                <span class="stat-value">${overall.percentage}%</span>
                <span class="stat-label">Attendance</span>
            </div>
            <div class="stat-item">
                <span class="stat-value">${overall.present}</span>
                <span class="stat-label">Present</span>
            </div>
            <div class="stat-item">
                <span class="stat-value">${overall.total_classes}</span>
                <span class="stat-label">Total</span>
            </div>
            <div class="stat-item">
                <span class="stat-value">${overall.absent}</span>
                <span class="stat-label">Absent</span>
            </div>
        </div>
        <div class="alert-message">${statusMessage}</div>
    `;
    document.getElementById('overallStats').innerHTML = overallHtml;
    
    // Display subjects
    const subjectsHtml = data.subjects.map(subject => {
        const statusClass = subject.AttendancePercentage < 75 ? 'warning' : 'success';
        const statusIcon = subject.AttendancePercentage < 75 ? '⚠️' : '✅';
        
        return `
            <div class="subject-card ${statusClass}">
                <div class="subject-header">
                    <span class="subject-name">${statusIcon} ${subject.Subject}</span>
                    <span class="subject-percentage ${statusClass}">${subject.AttendancePercentage}%</span>
                </div>
                <div class="subject-details">
                    <div class="detail-item"><strong>Code:</strong> ${subject.SubjectCode}</div>
                    <div class="detail-item"><strong>Present:</strong> ${subject.Present}/${subject.TotalClasses}</div>
                    <div class="detail-item"><strong>Absent:</strong> ${subject.Absent}</div>
                    <div class="detail-item"><strong>Latest:</strong> ${subject.LatestAttendanceDate}</div>
                </div>
            </div>
        `;
    }).join('');
    
    document.getElementById('subjectsList').innerHTML = subjectsHtml;
}

function showError(message) {
    document.getElementById('loading').style.display = 'none';
    document.getElementById('loginForm').style.display = 'block';
    document.getElementById('error').style.display = 'flex';
    document.getElementById('errorMessage').textContent = message;
}

function closeError() {
    document.getElementById('error').style.display = 'none';
}

document.getElementById('downloadBtn').addEventListener('click', async () => {
    if (!attendanceData || !attendanceData.subjects) {
        alert('No data to download');
        return;
    }
    
    try {
        const response = await fetch('/download', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ subjects: attendanceData.subjects })
        });
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'attendance_summary.csv';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    } catch (error) {
        alert('Failed to download CSV');
    }
});

document.getElementById('backBtn').addEventListener('click', () => {
    document.getElementById('results').style.display = 'none';
    document.getElementById('loginForm').style.display = 'block';
    document.getElementById('attendanceForm').reset();
    
    // Remove any error messages when going back
    const existingError = document.querySelector('.form-error');
    if (existingError) {
        existingError.remove();
    }
    
    attendanceData = null;
});

// Clear error message when user starts typing
document.getElementById('userId').addEventListener('input', () => {
    const existingError = document.querySelector('.form-error');
    if (existingError) {
        existingError.remove();
    }
});

document.getElementById('password').addEventListener('input', () => {
    const existingError = document.querySelector('.form-error');
    if (existingError) {
        existingError.remove();
    }
});
