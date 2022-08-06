# -*- coding: UTF-8 -*-
import json
import logging
import requests

class LarkException(Exception):
    def __init__(self, code=0, msg=None):
        self.code = code
        self.msg = msg

    def __str__(self) -> str:
        return "{}:{}".format(self.code, self.msg)

    __repr__ = __str__

def request(method, url, headers, payload={}, files=-1):
    if files != -1:
        response = requests.request(method, url, headers=headers, data=payload, files=files)
    else:
        response = requests.request(method, url, headers=headers, json=payload)
    logging.info("URL: " + url)
    logging.info("headers:\n"+json.dumps(headers,indent=2, ensure_ascii=False))
    logging.info("payload:\n"+json.dumps(payload,indent=2, ensure_ascii=False))
    resp = {}
    if response.text[0] == '{':
        resp = response.json()
        # logging.info("response:\n"+json.dumps(resp,indent=2, ensure_ascii=False))
    else:
        logging.info("response:\n"+response.text)
    code = resp.get("code", -1)
    if code == -1:
        code = resp.get("StatusCode", -1)
        if code == -1:
            base_resp = resp.get("BaseResp", -1)
            if base_resp != -1:
                code = base_resp.get("StatusCode", -1)
    if code == -1 and response.status_code != 200:
         response.raise_for_status()
    if code != 0:
        raise LarkException(code=code, msg=resp.get("msg", ""))
    return resp