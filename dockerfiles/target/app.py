#!/usr/bin/env python3
"""
SecretVault — Internal credentials store.
This is the final target. If you can see this page, you've
successfully pivoted through all three network segments.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import socket
import datetime

FLAG = "FLAG{pivoting_master_3_networks_deep}"

HTML = f"""<!DOCTYPE html>
<html>
<head>
    <title>SecretVault — CONFIDENTIAL</title>
    <style>
        body {{
            font-family: 'Courier New', monospace;
            background: #0a0a0a;
            color: #00ff41;
            max-width: 700px;
            margin: 60px auto;
            padding: 20px;
        }}
        .banner {{
            border: 2px solid #ff0000;
            background: #1a0000;
            color: #ff4444;
            padding: 15px;
            text-align: center;
            margin-bottom: 30px;
            font-weight: bold;
        }}
        h1 {{ color: #00ff41; text-align: center; }}
        .vault {{
            background: #111;
            border: 1px solid #333;
            padding: 20px;
            margin: 20px 0;
        }}
        .vault h3 {{ color: #ffaa00; margin-top: 0; }}
        table {{ width: 100%; border-collapse: collapse; }}
        td {{
            padding: 8px 12px;
            border-bottom: 1px solid #222;
        }}
        td:first-child {{ color: #888; width: 35%; }}
        .flag-box {{
            border: 2px dashed #00ff41;
            background: #001a00;
            padding: 20px;
            text-align: center;
            margin: 30px 0;
            font-size: 1.3em;
        }}
        .footer {{
            color: #333;
            font-size: 0.8em;
            text-align: center;
            margin-top: 40px;
        }}
    </style>
</head>
<body>
    <div class="banner">
        ⚠ CLASSIFIED — AUTHORIZED PERSONNEL ONLY ⚠<br>
        All access is logged and monitored.
    </div>

    <h1>SecretVault</h1>

    <div class="vault">
        <h3>Database Credentials</h3>
        <table>
            <tr><td>DB Host</td><td>db-prod-01.internal.lab</td></tr>
            <tr><td>DB Name</td><td>customers_prod</td></tr>
            <tr><td>Username</td><td>db_admin</td></tr>
            <tr><td>Password</td><td>Pr0d_DB!_Sup3rS3cur3#2024</td></tr>
        </table>
    </div>

    <div class="vault">
        <h3>Cloud API Keys</h3>
        <table>
            <tr><td>AWS Access Key</td><td>AKIAIOSFODNN7EXAMPLE</td></tr>
            <tr><td>AWS Secret Key</td><td>wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY</td></tr>
            <tr><td>Azure Tenant</td><td>a]3f8c2e1-4b5d-6a7e-8f9c-0d1e2f3a4b5c</td></tr>
        </table>
    </div>

    <div class="vault">
        <h3>Service Accounts</h3>
        <table>
            <tr><td>Domain Admin</td><td>svc_admin : W1nt3r!sCom1ng#2024</td></tr>
            <tr><td>Backup SA</td><td>svc_backup : B4ckM3Up!N0w#2024</td></tr>
            <tr><td>Jenkins</td><td>deployer : D3pl0y_A11_Th3_Th1ngs!</td></tr>
        </table>
    </div>

    <div class="flag-box">
        🚩 {FLAG}
    </div>

    <div class="footer">
        SecretVault v1.0 — target.internal.lab (10.10.3.40)<br>
        If you reached this page, you successfully pivoted through<br>
        Net A → Net B → Net C. Congratulations!
    </div>
</body>
</html>
"""

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(HTML.encode())

    def log_message(self, format, *args):
        # Quiet logging
        pass

if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', 80), Handler)
    print(f"[*] SecretVault running on port 80")
    server.serve_forever()
