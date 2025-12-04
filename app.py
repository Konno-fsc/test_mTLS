from flask import Flask, render_template
import pyodbc
import os

app = Flask(__name__)

# Azure Web Appsで設定された環境変数から接続文字列を取得
# Azureポータルで「構成」→「アプリケーション設定」にSQL_CONNECTION_STRINGを設定します。
CONNECTION_STRING = os.environ.get('SQL_CONNECTION_STRING') 

def get_users():
    """Azure SQL DatabaseからUsers Tableのデータを取得する関数"""
    users = []
    if not CONNECTION_STRING:
        # 接続文字列がない場合はエラーを返す
        return [("Error", "SQL_CONNECTION_STRING is not set in environment variables.")]

    try:
        # pyodbcでデータベースに接続
        # 接続文字列の例: "DRIVER={ODBC Driver 17 for SQL Server};SERVER=tcp:<server_name>.database.windows.net,1433;DATABASE=<database_name>;UID=<user>;PWD=<password>"
        # またはマネージドIDを使用する場合は別の形式
        cnxn = pyodbc.connect(CONNECTION_STRING)
        cursor = cnxn.cursor()

        # Users Tableからすべてのデータを取得
        # **注意**: 実際のテーブル名に合わせてください
        cursor.execute("SELECT * FROM Users") 

        # カラム名を取得（HTMLのヘッダーに使用）
        columns = [column[0] for column in cursor.description]
        
        # データを取得
        rows = cursor.fetchall()
        
        # 辞書のリストとしてデータを整形
        for row in rows:
            users.append(dict(zip(columns, row)))
            
        cursor.close()
        cnxn.close()
    
    except pyodbc.Error as ex:
        sqlstate = ex.args[0]
        # 接続エラーが発生した場合はエラーメッセージを返す
        print(f"Database Error: {sqlstate}")
        users = [{"Error": f"Database connection failed or query error: {sqlstate}"}]

    return users

@app.route('/')
def index():
    """ルートパスでUsers Tableのデータを表示する"""
    user_list = get_users()
    
    # データをHTMLテンプレートに渡す
    return render_template('index.html', users=user_list)

if __name__ == '__main__':
    # ローカルテスト用（本番環境では使用しない）
    app.run(debug=True)