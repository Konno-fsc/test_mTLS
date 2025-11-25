from flask import Flask, request, abort
import base64
import OpenSSL.crypto

app = Flask(__name__)

# --- 許可リスト ---
ALLOWED_CERT_CN = [
   "4f0000008fe385c0fb1076426400040000008f"
]
# ------------------

def extract_cn_from_cert_header(cert_header):
    """X-ARR-ClientCertヘッダーからCNを取得する"""
    if not cert_header:
        return None

    try:
        cert_data = base64.b64decode(cert_header)
        cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_ASN1, cert_data)
        
        # サブジェクト情報からCNを抽出
        subject = dict(cert.get_subject().get_components())
        cn = subject.get(b'CN', None)
        
        return cn.decode('utf-8') if cn else None

    except Exception:
        # 証明書が不正な形式の場合など
        return None

@app.before_request
def check_client_certificate():
    """リクエストがルーティングされる前に証明書を検証する"""
    
    # 1. ヘッダーから証明書全体を取得
    cert_header = request.headers.get('X-ARR-ClientCert')
    
    if not cert_header:
        # Azure設定 (Require) により、このコードに到達する前に拒否される可能性が高いですが、念のためチェック
        return abort(403, description="Client certificate is missing.")

    # 2. CNを抽出
    client_cn = extract_cn_from_cert_header(cert_header)
    
    if not client_cn:
        # 証明書が提供されたが、解析できなかった場合 (不正な形式など)
        return abort(403, description="Invalid client certificate format.")

    # 3. 許可リストと照合して検証
    if client_cn in ALLOWED_CERT_CN:
        # 許可された証明書 -> リクエストの処理を続行
        print(f"Access granted for CN: {client_cn}")
        return # Noneを返すと処理を続行
    else:
        # 許可されていない証明書 -> アクセス拒否
        print(f"Access DENIED for CN: {client_cn}")
        return abort(403, description="Client certificate is not authorized.")

@app.route('/')
def hello_world():
    # check_client_certificate() を通過したリクエストのみがここに到達します。
    client_cn = extract_cn_from_cert_header(request.headers.get('X-ARR-ClientCert'))
    return f"<h1>Hello_World!</h1><p>Access authorized for: <strong>{client_cn}</strong></p>"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)