# app.py
from flask import Flask, render_template_string
import os
import pyodbc

app = Flask(__name__)

# テンプレートの定義 (HTMLをPythonコード内に直接記述)
HTML_TEMPLATE = """
<!doctype html>
<title>User Data List</title>
<h1>User Data from Azure SQL Database</h1>
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

@app.route('/')
def display_users():
    conn = None
    data = []
    error = None

    # Azure App Serviceの環境変数から接続文字列を取得
    # 'AzureSqlDb' はステップ2で設定した接続文字列名に依存します
    # Pythonでは、接続文字列の値は 'CUSTOMCONNSTR_AzureSqlDb' というキーで取得されます。
    conn_str = os.environ.get('CUSTOMCONNSTR_AzureSqlDb')

    if not conn_str:
        return "Error: SQL Connection string 'AzureSqlDb' not found in Web App settings.", 500

    try:
        # SQL Databaseに接続
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        # user_dataテーブルから全データを取得
        cursor.execute("SELECT ID, Name, gender, age, attribute FROM user_data")
        data = cursor.fetchall()

    except pyodbc.Error as ex:
        # 接続またはクエリ実行エラーが発生した場合
        sqlstate = ex.args[0]
        error = f"Database Error: {sqlstate}. Check firewall/connection string."
        print(error) # デバッグのためにログに出力

    finally:
        if conn:
            conn.close()

    if error:
        return f"<h1>Database Connection Failed</h1><p>{error}</p>", 500
    
    # テンプレートにデータを渡してレンダリング
    return render_template_string(HTML_TEMPLATE, data=data)

if __name__ == '__main__':
    # ローカル実行時には環境変数に接続文字列を設定する必要があります
    # 例: os.environ['CUSTOMCONNSTR_AzureSqlDb'] = '...' 
    app.run(debug=True)