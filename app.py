# app.py
from flask import Flask

# Flaskアプリケーションのインスタンスを作成
app = Flask(__name__)

# ルートURL ("/")にアクセスがあった場合の処理を定義
@app.route('/')
def hello_world():
    # 'Hello_World!'というテキストを返す
    return 'Hello_World!'

# このファイルが直接実行された場合にサーバーを起動
if __name__ == '__main__':
    # 開発モードで実行
    app.run(debug=True)