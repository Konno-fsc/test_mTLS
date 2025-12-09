from flask import Flask, render_template_string, request
import os
import pymssql

app = Flask(__name__)

# テンプレートの定義 (HTMLにデバッグ情報として X-ARR-ClientCert を追加)
HTML_TEMPLATE = """
<!doctype html>
<title>User Data List</title>
<h1>User Data from Azure SQL Database</h1>
<p>
    <strong>Client Certificate Issuer (発行者):</strong> {{ cert_issuer_dn }}
    <br>
    <strong>X-ARR-ClientCert (デバッグ):</strong> {{ arr_cert }}
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

@app.route('/')
def display_users():
    conn = None
    data = []
    error = None

    # 💡 クライアント証明書の発行者 DN を取得
    cert_issuer_dn = request.headers.get('X-MS-CLIENT-CERT-ISSUER')
    
    # 💡 X-ARR-ClientCert ヘッダーも取得し、デバッグ用に格納
    arr_cert = request.headers.get('X-ARR-ClientCert')

    # 証明書が提供されない、または設定が無効な場合の代替テキスト
    if not cert_issuer_dn:
        cert_issuer_dn = "N/A (クライアント証明書の発行者属性が見つかりません)"
        
    if not arr_cert:
        arr_cert_display = "Not Found"
    else:
        # 表示が長くなりすぎないよう、Base64文字列の最初の50文字のみ表示
        arr_cert_display = arr_cert[:50] + "..." 
        
    # 確定した環境変数名 'AzureSqlDb' から接続文字列を取得
    conn_str = os.environ.get('AzureSqlDb')

    if not conn_str:
        return "Error: SQL Connection string 'AzureSqlDb' not found in Web App settings.", 500

    try:
        # 接続文字列から接続パラメータを解析
        params = parse_conn_str(conn_str)

        # pymssql.connect で SQL Databaseに接続 (ODBCドライバ不要)
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

    except Exception as ex: # 一般的な Exception でキャッチ
        # 接続またはクエリ実行エラーが発生した場合
        error = f"Database Error (pymssql): {ex}. Check authentication/connection parameters."
        print(error) # デバッグのためにログに出力

    finally:
        if conn:
            conn.close()

    if error:
        return f"<h1>Database Connection Failed</h1><p>{error}</p>", 500
    
    # テンプレートにデータを渡してレンダリング (cert_issuer_dn と arr_cert_display を追加)
    return render_template_string(HTML_TEMPLATE, 
                                  data=data, 
                                  cert_issuer_dn=cert_issuer_dn,
                                  arr_cert=arr_cert_display)

if __name__ == '__main__':
    app.run(debug=True)