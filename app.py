from flask import Flask
import os

# Flaskアプリケーションインスタンスを作成
app = Flask(__name__)

# ルートパス（/）へのアクセスで実行される関数を定義
@app.route('/')
def hello_world():
    """
    シンプルな「Hello World!」メッセージを返します。
    """
    return '<h1>Hello World!</h1>'

# 本番環境では使用されないが、Gunicorn/WSGIサーバーがこの 'app' インスタンスを見つけます。
if __name__ == '__main__':
    # ローカルテスト用
    # ポートは環境変数から取得することが推奨されます
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)