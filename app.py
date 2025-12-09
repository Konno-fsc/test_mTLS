# app.py (証明書デコードロジック追加版)

from flask import Flask, render_template_string, request
import os
import pymssql
import base64
from cryptography import x509
from cryptography.hazmat.backends import default_backend

app = Flask(__name__)

# テンプレートの定義 (HTMLは変更なし)
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
# ... (省略) ...
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
        'port': port
    }
# ----------------------------------------------------

@app.route('/')
def display_users():
    conn = None
    data = []
    error = None

    # App Serviceが生成する発行者ヘッダーをまず取得
    cert_issuer_dn = request.headers.get('X-MS-CLIENT-CERT-ISSUER')
    arr_cert = request.headers.get('X-ARR-ClientCert')

    # 手動デコード用の発行者変数
    decoded_issuer = "証明書情報なし"

    if arr_cert:
        # 💡 Base64から証明書オブジェクトへの変換と発行者抽出 💡
        try:
            # 1. Base64文字列をデコード
            cert_bytes = base64.b64decode(arr_cert)
            
            # 2. X.509証明書オブジェクトとしてロード
            cert = x509.load_der_x509_certificate(cert_bytes, default_backend())
            
            # 3. 発行者DN (Distinguished Name) を抽出
            decoded_issuer = cert.issuer.rfc4514_string()

            # 💡 X-MS-CLIENT-CERT-ISSUER が見つからない場合は、デコードした値を使用
            if not cert_issuer_dn:
                cert_issuer_dn = f"手動デコード: {decoded_issuer}"
                
        except Exception as e:
            decoded_issuer = f"デコードエラー: {e}"
            if not cert_issuer_dn:
                 cert_issuer_dn = f"検証失敗: {e}"

    # 表示が長くなりすぎないよう、Base64文字列の最初の50文字のみ表示
    arr_cert_display = arr_cert[:50] + "..." if arr_cert else "Not Found"
    
    if not cert_issuer_dn or cert_issuer_dn.startswith("N/A"):
        # 元々 N/A だった場合に、手動デコードの結果を表示する
        if decoded_issuer not in ["証明書情報なし", "デコードエラー"]:
             cert_issuer_dn = f"手動デコード: {decoded_issuer}"
        else:
             cert_issuer_dn = f"N/A ({decoded_issuer})"


    # 確定した環境変数名 'AzureSqlDb' から接続文字列を取得 (以下、DB接続処理は省略)
    # ...
    conn_str = os.environ.get('AzureSqlDb')
    if not conn_str:
        return "Error: SQL Connection string 'AzureSqlDb' not found in Web App settings.", 500

    try:
        # 接続文字列から接続パラメータを解析
        params = parse_conn_str(conn_str)
        conn = pymssql.connect(
            server=params['server'], user=params['user'], 
            password=params['password'], database=params['database']
        )
        cursor = conn.cursor()
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
                                  cert_issuer_dn=cert_issuer_dn,
                                  arr_cert=arr_cert_display)

if __name__ == '__main__':
    # 環境変数設定がない場合のためのダミー設定 (開発環境でのみ使用)
    # os.environ['AzureSqlDb'] = "Driver={ODBC Driver 17 for SQL Server};Server=tcp:yourserver.database.windows.net,1433;Database=yourdb;Uid=youruser;Pwd=yourpassword;"
    app.run(debug=True)