# app.py (修正後)

from flask import Flask, render_template_string, request #request をインポート
import os
import pymssql

app = Flask(__name__)

# テンプレートの定義 (HTMLは変更なし)
HTML_TEMPLATE = """
<!doctype html>
<title>User Data List</title>
<h1>User Data from Azure SQL Database</h1>
<p>
    <strong>Client Certificate Issuer (発行者):</strong> {{ cert_issuer_dn }}
</p>
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

# --- 接続文字列からパラメータを抽出するヘルパー関数 (省略) ---
# ... (parse_conn_str 関数は変更なし) ...
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
        'port': port # pymssql はデフォルトで1433を使うため、ここでは使用しないが抽出
    }
# ----------------------------------------------------

@app.route('/')
def display_users():
    conn = None
    data = []
    error = None

    # クライアント証明書の発行者 DN を取得
    # Azure App Service が設定で有効化されている場合に提供するヘッダー
    # ヘッダー名は Flask で自動的に 'X-MS-CLIENT-CERT-ISSUER' -> 'X_MS_CLIENT_CERT_ISSUER' のように変換されるか、
    # request.headers.get('X-Ms-Client-Cert-Issuer') で取得可能です。
    cert_issuer_dn = request.headers.get('X-MS-CLIENT-CERT-ISSUER')
    
    #証明書が提供されない、または設定が無効な場合の代替テキスト
    if not cert_issuer_dn:
        cert_issuer_dn = "N/A (クライアント証明書は提供されていないか、App Serviceの設定が無効です)"

    #確定した環境変数名 'AzureSqlDb' から接続文字列を取得
    conn_str = os.environ.get('AzureSqlDb')
# ... (残りのデータベース接続処理は変更なし) ...

    if not conn_str:
        return "Error: SQL Connection string 'AzureSqlDb' not found in Web App settings.", 500

    try:
        #接続文字列から接続パラメータを解析
        params = parse_conn_str(conn_str)

        #pymssql.connect で SQL Databaseに接続 (ODBCドライバ不要)
        conn = pymssql.connect(
            server=params['server'], 
            user=params['user'], 
            password=params['password'], 
            database=params['database']
        )
        cursor = conn.cursor()

        # user_dataテーブルから全データを取得
        cursor.execute("SELECT ID, Name, gender, age, attribute FROM user_data")
        
        # pymssql は row[0] ではなく tuple のリストを返すため、fetchall() はそのまま使用可能
        data = cursor.fetchall() 

    except Exception as ex: #pyodbc.Error ではなく、一般的な Exception でキャッチ
        # 接続またはクエリ実行エラーが発生した場合
        error = f"Database Error (pymssql): {ex}. Check authentication/connection parameters."
        print(error) # デバッグのためにログに出力

    finally:
        if conn:
            conn.close()

    if error:
        return f"<h1>Database Connection Failed</h1><p>{error}</p>", 500
    
    #テンプレートにデータを渡してレンダリング (cert_issuer_dn を追加)
    return render_template_string(HTML_TEMPLATE, data=data, cert_issuer_dn=cert_issuer_dn)

if __name__ == '__main__':
    app.run(debug=True)