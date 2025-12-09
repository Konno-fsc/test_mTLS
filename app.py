from flask import Flask, render_template_string
import os
import pymssql #1. データベース接続を pymssql に変更

app = Flask(__name__)

# テンプレートの定義 (HTMLをPythonコード内に直接記述)
HTML_TEMPLATE = """
<!doctype html>
<title>User Data List</title>
<h1>User Data from Azure SQL Database</h1>

<p>
    <strong>クライアント証明書 発行者 (Issuer):</strong> {{ issuer }}
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
    # Server=tcp:xxx,1433 の形式からサーバー名を取得
    server_with_port = params.get('server', '').replace('tcp:', '')
    server = server_with_port.split(',')[0] if ',' in server_with_port else server_with_port
    
    return {
        'server': server,
        'database': params.get('database'),
        'user': params.get('uid'),
        'password': params.get('pwd'),
        # ポートはpymssqlがデフォルト1433を使用するため省略可能
    }

# ----------------------------------------------------

@app.route('/')
def display_users():
    conn = None
    data = []
    error = None
    
    #2. クライアント証明書の発行者情報を取得
    cert_issuer = os.environ.get('WEBSITES_CLIENT_CERT_ISSUER', '証明書が提供されていません/取得失敗')

    #2. 確定した環境変数名 'AzureSqlDb' から接続文字列を取得
    conn_str = os.environ.get('AzureSqlDb')

    if not conn_str:
        # DB接続文字列が見つからない場合は、エラーを発行者情報なしで返す
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
        data = cursor.fetchall() 

    except Exception as ex: # 💡 pyodbc.Error ではなく、一般的な Exception でキャッチ
        # 接続またはクエリ実行エラーが発生した場合
        error = f"Database Error (pymssql): {ex}. Check authentication/connection parameters."
        print(error) # デバッグのためにログに出力

    finally:
        if conn:
            conn.close()

    if error:
        # DB接続エラーが発生した場合は、発行者情報を含めずにエラーを返す
        return f"<h1>Database Connection Failed</h1><p>{error}</p>", 500
    
    # テンプレートにデータを渡してレンダリング
    return render_template_string(HTML_TEMPLATE, data=data, issuer=cert_issuer)

if __name__ == '__main__':
    app.run(debug=True)