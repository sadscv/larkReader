# -*- coding: UTF-8 -*-
import json
from utils import request


class Client(object):
    def __init__(self, lark_host):
        self._host = lark_host

    def get_tenant_access_token(self, app_id, app_secret):
        url = self._host + "/open-apis/auth/v3/app_access_token/internal/"
        headers = {
            'Content-Type': 'application/json; charset=utf-8'
        }
        payload = {
            'app_id': app_id,
            'app_secret': app_secret
        }
        resp = request("POST", url, headers, payload)
        return resp['tenant_access_token']

    def get_user_access_token(self, app_access_token, code):
        url = self._host + "/open-apis/authen/v1/access_token"
        headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'Authorization': 'Bearer ' + app_access_token
        }
        payload = {
            'grant_type': "authorization_code",
            'code': code,
        }
        resp = request("POST", url, headers, payload)
        return resp['data']['access_token']

    def get_login_code(self, tenant_access_token, app_id, session_id):
        url = self._host + "/open-apis/mina/v2/login"
        headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'Authorization': 'Bearer ' + tenant_access_token
        }
        payload = {
            "appid": app_id,
            "sessionid": session_id
        }
        resp = request("POST", url, headers, payload)
        return resp['data']['code']

    # def get_user_access_token(self, app_id, code):
    #     url = self._host + "/open-apis/mina/loginValidate"
    #     headers = {
    #         'Content-Type': 'application/json; charset=utf-8'
    #     }
    #     payload = {
    #         "appid": app_id,
    #         # "secret": secret,
    #         "code": code
    #     }
    #     resp = request("GET", url, headers, payload)
    #     print('resp', resp)
    #     return resp['access_token']

    def get_root_folder_token(self, access_token):
        url = self._host + "/open-apis/drive/explorer/v2/root_folder/meta"
        headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'Authorization': 'Bearer ' + access_token
        }
        resp = request("GET", url, headers)
        return resp['data']['token']

    def upload_file(self, access_token, file_name, parent_type, parent_node, size, file_path):
        url = self._host + "/open-apis/drive/v1/files/upload_all"
        headers = {
            'Authorization': 'Bearer ' + access_token
        }
        payload = {'file_name': file_name,
                   'parent_type': parent_type,
                   'parent_node': parent_node,
                   'size': size}
        files = [
            ('file', (file_name, open(file_path, 'rb'),
                      'application/vnd.openxmlformats-officedocument.wordprocessingml.document'))
        ]
        resp = request("POST", url, headers, payload, files)
        return resp['data']['file_token']

    def create_import_task(self, access_token, file_extension, file_name, file_token, mount_key, mount_type, doc_type):
        url = self._host + "/open-apis/drive/v1/import_tasks"
        headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'Authorization': 'Bearer ' + access_token
        }
        payload = {
            "file_name": file_name,
            "file_extension": file_extension,
            "file_token": file_token,
            "point": {
                "mount_key": mount_key,
                "mount_type": mount_type
            },
            "type": doc_type,
        }
        resp = request('POST', url, headers, payload)
        return resp['data']['ticket']

    def create_new_docx(self, access_token, folder_token, content_type='doc'):
        url = self._host + "/open-apis/drive/explorer/v2/file/" + folder_token
        headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'Authorization': 'Bearer ' + access_token
        }
        payload = {
            "title": 'testv1.0',
            "type": content_type,
        }
        resp = request('POST', url, headers, payload)
        print(resp)
        return resp['data']['ticket']

    def get_import_result(self, access_token, ticket):
        url = self._host + "/open-apis/drive/v1/import_tasks/" + ticket
        headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'Authorization': 'Bearer ' + access_token
        }
        resp = request('GET', url, headers)
        if resp['data']['result']['job_status'] == 0:
            return 0, resp['data']['result']['url'], resp['data']['result']['token']
        else:
            return 1, "", ""

    def get_document_raw_content(self, access_token, document_id):
        url = self._host + "/open-apis/doc/v2/" + document_id + "/raw_content"
        headers = {
            'Authorization': 'Bearer ' + access_token
        }
        resp = request("GET", url, headers)
        return resp['data']['content']

    def get_document_infos(self, access_token, document_id):
        url = self._host + "/open-apis/docx/v1/documents/" + document_id
        headers = {
            'Authorization': 'Bearer ' + access_token
        }
        resp = request("GET", url, headers)
        return resp['data']

    def get_document_blocks(self, access_token, document_id, page_token=None):
        print(access_token, document_id)
        if page_token:
            url = self._host + "/open-apis/docx/v1/documents/" + document_id + "/blocks" + "?page_token={}".format(page_token)
        else:
            url = self._host + "/open-apis/docx/v1/documents/" + document_id + "/blocks"
        headers = {
            'Authorization': 'Bearer ' + access_token
        }
        resp = request("GET", url, headers)
        return resp['data']

    def create_document_block(self, access_token, document_id, root_block_id, index, children):
        url = self._host + "/open-apis/docx/v1/documents/" + document_id + "/blocks/" + root_block_id + "/children"
        headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'Authorization': 'Bearer ' + access_token
        }
        payload = {
            "index": index,
            "children": children,
        }
        print(payload)
        resp = request("POST", url, headers, payload)
        return resp

    def update_block_link_url(self, access_token, document_id, block_id, elements, revision_id=-1):
        url = self._host + "/open-apis/docx/v1/documents/" + document_id + "/blocks/" + block_id + "?document_revision_id={}".format(revision_id)
        headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'Authorization': 'Bearer ' + access_token,
        }
        payload = {
            "update_text_elements": {
                "elements": elements,
            }
        }

        resp = request("PATCH", url, headers, payload)
        return resp['data']

    def update_docx_permission(self, access_token, doc_token):
        url = self._host + "/open-apis/drive/v1/permissions/" + doc_token + "/public?type=docx"
        headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'Authorization': 'Bearer ' + access_token
        }
        payload = {
            "external_access": True,
            "security_entity": "anyone_can_view",
            "comment_entity": "anyone_can_view",
            "share_entity": "anyone",
            "link_share_entity": "tenant_editable",
            "invite_external": True
        }
        _ = request("PATCH", url, headers, payload)
        return

    def translate(self, tenant_access_token, source_language, source_text, target_language):
        url = self._host + "/open-apis/translation/v1/text/translate"
        headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'Authorization': 'Bearer ' + tenant_access_token
        }
        payload = {
            "source_language": source_language,
            "text": source_text,
            "target_language": target_language,
        }
        resp = request("POST", url, headers, payload)
        return resp['data']['text']
