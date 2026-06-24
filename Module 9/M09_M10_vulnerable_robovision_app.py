#!/usr/bin/env python3
"""
RoboVision Controller — VULNERABLE VERSION FOR SECURITY LABS
============================================================
Module 9 (CWE Top 25) and Module 10 (SAST Lab) training exercise.

DO NOT deploy this application. It is intentionally vulnerable
and designed to trigger GitLab security scanner findings.

Vulnerabilities present (by CWE/OWASP):
  CWE-89  / A03 — SQL Injection (login, robot query)
  CWE-78  / A03 — Command Injection (diagnostic endpoint)
  CWE-22  / A05 — Path Traversal (log download)
  CWE-798 / A07 — Hardcoded Credentials (API key, DB password)
  CWE-327 / A02 — Weak Cryptography (MD5 password hashing)
  CWE-502 / A08 — Unsafe Deserialization (session restore)
  CWE-79  / A03 — XSS (status display)
  CWE-918 / A10 — SSRF (webhook endpoint)
  CWE-306 / A07 — Missing Authentication (admin endpoint)
  CWE-312 / A02 — Sensitive data in logs

WARNING: This file is intentionally insecure.
GitLab SAST should flag multiple findings.
Students fix each vulnerability in the SAST lab (Module 10).
"""

import hashlib
import os
import pickle
import subprocess
import sqlite3
import requests
from flask import Flask, request, jsonify, session

app = Flask(__name__)

# ============================================================
# CWE-798: HARDCODED CREDENTIALS
# GitLab Secret Detection and SAST will flag these
# ============================================================
app.secret_key = "super-secret-key-123"                    # CWE-798
DB_PASSWORD = "RoboVision2024!"                            # CWE-798
API_KEY = "sk-robovision-prod-abc123xyz789secret"          # CWE-798 (Secret Detection)
AWS_SECRET_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLE"  # CWE-798 (Secret Detection)

# Database setup (SQLite for lab simplicity)
DB_PATH = "robovision.db"

def get_db():
    return sqlite3.connect(DB_PATH)


# ============================================================
# CWE-89: SQL INJECTION — Login
# A03: Injection
# SAST will flag: string concatenation in SQL query
# ============================================================
@app.route('/api/login', methods=['POST'])
def login():
    """
    VULNERABLE: SQL Injection in authentication.

    Attack: username = "admin'--"
    Query becomes: SELECT * FROM users WHERE username='admin'--' AND password=...
    The -- comments out the password check → login without password
    """
    username = request.json.get('username', '')
    password = request.json.get('password', '')

    # CWE-327: MD5 is not suitable for password hashing
    password_hash = hashlib.md5(password.encode()).hexdigest()  # CWE-327

    db = get_db()
    # CWE-89: SQL Injection — string concatenation in query
    query = "SELECT * FROM users WHERE username='" + username + "' AND password_hash='" + password_hash + "'"
    cursor = db.execute(query)
    user = cursor.fetchone()

    if user:
        session['user_id'] = user[0]
        session['username'] = username
        # CWE-312: Logging sensitive information
        app.logger.info(f"Login success: {username}, password_hash: {password_hash}")
        return jsonify({'status': 'ok', 'user': username})

    return jsonify({'error': 'Invalid credentials'}), 401


# ============================================================
# CWE-89: SQL INJECTION — Robot Query
# ============================================================
@app.route('/api/robots/search', methods=['GET'])
def search_robots():
    """
    VULNERABLE: SQL Injection in search.

    Attack: robot_id = "1 OR 1=1"
    Returns ALL robots regardless of ownership
    """
    robot_id = request.args.get('robot_id', '')

    db = get_db()
    # CWE-89: SQL Injection — f-string in SQL query
    query = f"SELECT * FROM robots WHERE id = {robot_id}"
    cursor = db.execute(query)
    robots = cursor.fetchall()

    return jsonify({'robots': robots})


# ============================================================
# CWE-78: COMMAND INJECTION — Diagnostic
# A03: Injection
# SAST will flag: shell=True with user input
# ============================================================
@app.route('/api/diagnostic/ping', methods=['POST'])
def ping_diagnostic():
    """
    VULNERABLE: OS Command Injection.

    Attack: host = "8.8.8.8; cat /etc/passwd; echo"
    The semicolon chains additional commands after ping.
    In a robot controller: host = "8.8.8.8; systemctl stop robot-controller"
    """
    host = request.json.get('host', '')

    # CWE-78: shell=True with user-controlled input
    result = subprocess.run(
        f"ping -c 3 {host}",    # Command injection here
        shell=True,              # SAST flags: shell=True with variable
        capture_output=True,
        text=True,
        timeout=10
    )
    return jsonify({'output': result.stdout})


# ============================================================
# CWE-22: PATH TRAVERSAL — Log Download
# A01: Broken Access Control (also Path Traversal)
# SAST will flag: os.path.join with user-supplied path
# ============================================================
@app.route('/api/logs/<log_name>', methods=['GET'])
def get_log(log_name):
    """
    VULNERABLE: Path Traversal.

    Attack: log_name = "../../etc/passwd"
    os.path.join('/var/app/logs', '../../etc/passwd')
    Resolves to: /etc/passwd

    An attacker can read any file readable by the application process.
    """
    # CWE-22: No path validation before opening file
    log_path = os.path.join('/var/app/logs', log_name)
    try:
        with open(log_path, 'r') as f:
            return jsonify({'content': f.read()})
    except FileNotFoundError:
        return jsonify({'error': 'Log not found'}), 404


# ============================================================
# CWE-502: UNSAFE DESERIALIZATION — Session Restore
# A08: Software and Data Integrity Failures
# SAST will flag: pickle.loads() on user-supplied data
# ============================================================
@app.route('/api/session/restore', methods=['POST'])
def restore_session():
    """
    VULNERABLE: Unsafe deserialization with pickle.

    Attack: Send crafted pickle payload that executes arbitrary code.
    Python pickle's __reduce__ allows arbitrary code execution.

    Proof of concept:
        import pickle, base64, os
        class Exploit:
            def __reduce__(self):
                return (os.system, ('id > /tmp/pwned',))
        payload = base64.b64encode(pickle.dumps(Exploit())).decode()
    """
    import base64
    data = request.json.get('session_data', '')

    # CWE-502: Deserializing untrusted data with pickle
    try:
        session_obj = pickle.loads(base64.b64decode(data))  # CRITICAL: RCE vector
        session.update(session_obj)
        return jsonify({'status': 'session restored'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


# ============================================================
# CWE-79: CROSS-SITE SCRIPTING — Status Display
# A03: Injection
# ============================================================
@app.route('/api/robot/status/display', methods=['GET'])
def display_status():
    """
    VULNERABLE: Reflected XSS.

    Attack: message = "<script>document.cookie</script>"
    The script executes in the victim's browser context.

    Note: This is more commonly relevant in template rendering;
    included here for SAST detection demonstration.
    """
    robot_name = request.args.get('name', 'Unknown')
    status_msg = request.args.get('status', '')

    # CWE-79: User input rendered without encoding
    # In a real template: return render_template_string("<b>{{name}}</b>: {{status}}", ...)
    # This raw string construction is the vulnerability
    html_response = f"<html><body><h1>Robot: {robot_name}</h1><p>Status: {status_msg}</p></body></html>"
    return html_response, 200, {'Content-Type': 'text/html'}


# ============================================================
# CWE-918: SERVER-SIDE REQUEST FORGERY — Webhook
# A10: SSRF
# SAST will flag: requests.get() with user-controlled URL
# ============================================================
@app.route('/api/webhook/register', methods=['POST'])
def register_webhook():
    """
    VULNERABLE: Server-Side Request Forgery.

    Attack: callback_url = "http://169.254.169.254/latest/meta-data/iam/security-credentials/"
    The server fetches the AWS metadata endpoint, returning IAM credentials.

    Also valid: callback_url = "file:///etc/passwd"
    Or: callback_url = "http://internal-service.company.local/admin"
    """
    callback_url = request.json.get('callback_url', '')
    event_type = request.json.get('event_type', 'robot.status')

    # CWE-918: Making HTTP request to user-supplied URL
    response = requests.get(callback_url, timeout=5)  # SSRF vulnerability
    
    return jsonify({
        'registered': True,
        'url': callback_url,
        'probe_status': response.status_code
    })


# ============================================================
# CWE-306: MISSING AUTHENTICATION — Admin Endpoint
# A07: Authentication Failures
# SAST/DAST will flag: sensitive operation with no auth check
# ============================================================
@app.route('/admin/reset-all-robots', methods=['POST'])
def reset_all_robots():
    """
    VULNERABLE: Critical function with NO authentication.

    Any network-accessible caller can reset all robots.
    In a real system: this could trigger emergency stops on
    all robots simultaneously — dangerous in a factory setting.
    """
    # CWE-306: No authentication check on destructive operation
    db = get_db()
    db.execute("UPDATE robots SET state='reset', last_command=NULL")
    db.commit()
    app.logger.warning(f"ALL ROBOTS RESET by {request.remote_addr}")
    return jsonify({'status': 'all robots reset', 'count': db.execute("SELECT COUNT(*) FROM robots").fetchone()[0]})


# ============================================================
# Helper — deliberately also has a weakness for completeness
# ============================================================
@app.route('/api/robot/command', methods=['POST'])
def send_command():
    """
    Partially secure command endpoint — has input validation but
    logs the full command including any sensitive parameters.
    """
    command = request.json.get('command', '')
    robot_id = request.json.get('robot_id', '')
    params = request.json.get('params', {})

    valid_commands = ['move', 'stop', 'rotate', 'extend']
    if command not in valid_commands:
        return jsonify({'error': 'Invalid command'}), 400

    # CWE-312: Logging sensitive operation details
    app.logger.info(f"Command sent: {command}, robot: {robot_id}, params: {params}, auth_token: {request.headers.get('Authorization')}")

    return jsonify({'accepted': True, 'command': command})


if __name__ == '__main__':
    # CWE-16 / A05: Debug mode enabled — exposes interactive debugger
    app.run(debug=True, host='0.0.0.0', port=5000)  # debug=True in production!
