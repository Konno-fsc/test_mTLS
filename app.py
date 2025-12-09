from flask import Flask, render_template_string, request
import os
import pymssql
import base64
from cryptography import x509
from cryptography.hazmat.backends import default_backend

app = Flask(__name__)

# テンプレートの定義 (HTMLに証明書の詳細属性を追加)
HTML_TEMPLATE = """
<!doctype html>
<title>User Data List</title>
<h1>User Data from Azure SQL Database</h1>
<h2>🔒 Client Certificate Attributes</h2>
<p>
    <strong>X-ARR-ClientCert (デバッグ):</strong> {{ arr_cert }}
    <br>
    <strong>Issuer (発行者):</strong> {{ cert_attrs.issuer }}
    <br>
    <strong>Subject (サブジェクト):</strong> {{ cert_attrs.subject }}
    <br>
    <strong>Serial Number (シリアル番号):</strong> {{ cert_attrs.serial_number }}
    <br>
    <strong>Valid Until (有効期限):</strong> {{ cert_attrs.not_valid_after }}
    <br>
    <strong>Verification Status (検証ステータス):</strong> {{ cert_attrs.verified }}
</p>

---

<h2>💾 Database Contents</h2>
<style>
    table, th, td {
        border: 1px solid black;
        border-collapse: collapse;
        padding: 8px;
        text-align: left;
    }
    th {
        background-color: #f2f2f2;
    }
</style>
<table>
    <tr>
        <th>ID</th>
        <th>Name</th>
        <th>Gender</th>
        <th>Age</th>
        <th>Attribute</th>
    </tr>
    {% for row in data %}
    <tr>
        <td>{{ row[0] }}</td>
        <td>{{ row[1] }}</td>
        <td>{{ row[2] }}</td>
        <td>{{ row[3] }}</td>
        <td>{{ row[4] }}</td>
    </tr>
    {% endfor %}
</table>
"""

# --- 接続文字列からパラメータを抽出するヘルパー関数 ---
def parse_conn_str(conn_str):
    """ODBC接続文字列からpymssqlに必要なパラメータを抽出する"""
    params = {}
    for part in conn_str.split(';'):
        if '=' in part:
            key, value = part.split('=', 1)
            params[key.strip().lower()] = value.strip()
    
    # pymssql形式に合わせてパラメータを抽出
    server = params.get('server', '').replace('tcp:', '').split(',')[0]
    port = params.get('server', '').split(',')[1] if ',' in params.get('server', '') else 1433
    
    return {
        'server': server,
        'database': params.get('database'),
        'user': params.get('uid'),
        'password': params.get('pwd'),
        'port': port
    }
# ----------------------------------------------------

# --- 証明書解析ヘルパー関数 ---
def decode_client_cert(arr_cert_b64, request_headers):
    """X-ARR-ClientCert をデコードし、証明書属性を抽出する"""
    attrs = {
        'issuer': 'N/A (証明書未提示)',
        'subject': 'N/A',
        'serial_number': 'N/A',
        'not_valid_after': 'N/A',
        'verified': request_headers.get('X-MS-CLIENT-CERT-VERIFIED', 'N/A (ヘッダーなし)')
    }
    
    if arr_cert_b64:
        # X-MS-CLIENT-CERT-VERIFIED ヘッダーが取得できた場合はその値を優先
        if attrs['verified'] == 'N/A (ヘッダーなし)':
             attrs['verified'] = 'Verification Status N/A'
             
        try:
            # 1. Base64文字列をデコード
            cert_bytes = base64.b64decode(arr_cert_b64)
            
            # 2. X.509証明書オブジェクトとしてロード
            cert = x509.load_der_x509_certificate(cert_bytes, default_backend())
            
            # 3. 各属性を抽出
            attrs['issuer'] = cert.issuer.rfc4514_string()
            attrs['subject'] = cert.subject.rfc4514_string()
            attrs['serial_number'] = hex(cert.serial_number)
            attrs['not_valid_after'] = cert.not_valid_after.strftime('%Y-%m-%d %H:%M:%S UTC')
            
        except Exception as e:
            attrs['issuer'] = f"デコードエラー: {e}"
            attrs['verified'] = 'FAILED (デコードエラー)'

    return attrs
# -----------------------------

@app.route('/')
def display_users():
    conn = None
    data = []
    error = None

    # 💡 X-ARR-ClientCert ヘッダーを取得
    arr_cert = request.headers.get('X-ARR-ClientCert')

    # 💡 証明書解析ヘルパー関数を使用して属性を取得
    cert_attrs = decode_client_cert(arr_cert, request.headers)
    
    # Base64文字列の表示調整
    arr_cert_display = arr_cert[:50] + "..." if arr_cert else "Not Found"

    # --- データベース接続処理 ---
    
    # 確定した環境変数名 'AzureSqlDb' から接続文字列を取得
    conn_str = os.environ.get('AzureSqlDb')

    if not conn_str:
        return "Error: SQL Connection string 'AzureSqlDb' not found in Web App settings.", 500

    try:
        # 接続文字列から接続パラメータを解析
        params = parse_conn_str(conn_str)

        # pymssql.connect で SQL Databaseに接続
        conn = pymssql.connect(
            server=params['server'], 
            user=params['user'], 
            password=params['password'], 
            database=params['database']
        )
        cursor = conn.cursor()

        # user_dataテーブルから全データを取得
        cursor.execute("SELECT ID, Name, gender, age, attribute FROM user_data")
        data = cursor.fetchall() 

    except Exception as ex:
        error = f"Database Error (pymssql): {ex}. Check authentication/connection parameters."
        print(error)

    finally:
        if conn:
            conn.close()

    if error:
        return f"<h1>Database Connection Failed</h1><p>{error}</p>", 500
    
    # テンプレートにデータを渡してレンダリング
    return render_template_string(HTML_TEMPLATE, 
                                  data=data, 
                                  arr_cert=arr_cert_display,
                                  cert_attrs=cert_attrs)

if __name__ == '__main__':
    app.run(debug=True)