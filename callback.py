import json

from flask import Flask, request, abort, jsonify

import config
from api import Client
from decode import AESCipher

app = Flask(__name__)


@app.route("/")
def hello_world():
    return "hello"


@app.route("/callback", methods = ['GET', 'POST'])
def callback():
    cipher = AESCipher("y6txts1jspUemqdRYJIzkgKivZc2Q064")
    challenge = None
    if request.json:
        print(json.loads(cipher.decrypt_string(request.json['encrypt'])))
        # challenge = json.loads(cipher.decrypt_string(request.json['encrypt']))['challenge']
        print(challenge)
    # if not request.json:
    #     abort(404)
    if challenge:
        result = {
            "challenge": challenge,
        }
    else:
        result = {
            'fuck': 'fuck',
        }
    return jsonify(result), 200

@app.route("/feishu_login", methods = ['GET','POST'])
def feishu_login():
    # https://open.feishu.cn/open-apis/authen/v1/user_auth_page_beta?app_id=cli_a237b7756e63500e&redirect_uri=http%3A%2F%2F150.158.195.65%3A7019%2Ffeishu_login&state=RANDOMSTATE

    client = Client(config.LARK_HOST)
    tenant_access_token = client.get_tenant_access_token(config.APP_ID, config.APP_SECRET)
    cipher = AESCipher("y6txts1jspUemqdRYJIzkgKivZc2Q064")
    challenge = None
    user_access_token = None
    if request.json:
        response = json.loads(cipher.decrypt_string(request.json['encrypt']))
        # challenge = json.loads(cipher.decrypt_string(request.json['encrypt']))['challenge']
        # print(response)
    else:
        code = request.args.get('code')
        user_access_token = client.get_user_access_token(tenant_access_token, code)
        print(user_access_token)
    if challenge:
        result = {
            "challenge": challenge,
        }
    else:
        result = {
            'user_access_token': user_access_token,
        }
    return jsonify(result), 200


