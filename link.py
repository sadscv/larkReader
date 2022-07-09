# -*- coding: UTF-8 -*-
import json
import time
from pprint import pprint

import api
import config
import logging

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
logging.basicConfig(format=LOG_FORMAT, level=logging.INFO)

DOC_A_PATH = "document/doc_A.docx"
DOC_B_PATH = "document/doc_B.docx"
PARENT_TYPE = "explorer"
DOC_A_SIZE = 6457
DOC_B_SIZE = 6386
DOC_TYPE = 'docx'

import os
logging.info(os.getcwd())

def import_doc(client, access_token, parent_type, root_folder_token, file_size, file_path):
    fields = file_path.split("/")
    file_name = fields[-1]
    fields = file_path.split(".")
    file_extension = fields[-1]
    file_token = client.upload_file(access_token, file_name, parent_type, root_folder_token, file_size, file_path)
    ticket = client.create_import_task(access_token, file_extension, file_name, file_token, root_folder_token, 1, DOC_TYPE)
    # ticket = client.create_new_docx(access_token, root_folder_token)
    # print(ticket)
    try_times = 0
    while True:
        if try_times > 20:
            print("import document fail, file_path: %s" % file_path)
            return False, "", ""
        time.sleep(1)
        job_status, url, token = client.get_import_result(access_token, ticket)
        if job_status == 0:
            return True, url, token
        try_times = try_times + 1

def update_link(client, access_token, doc_token, blocks, target_url):
    for block in blocks:
        if block['block_type'] == 2:
            for element in block['text']['elements']:
                if 'text_run' in element:
                    if 'text_element_style' in element['text_run']:
                        if 'link' in element['text_run']['text_element_style']:
                            new_elements = block['text']['elements']
                            new_elements[0]['text_run']['text_element_style']['link']['url'] = target_url
                            client.update_block_link_url(access_token, doc_token, block['block_id'],
                                                         new_elements)
                            return
    return

def link():
    '''replace bi-directional links in documents after document data migration'''
    # init api client
    client = api.Client(config.LARK_HOST)

    # get tenant access token
    access_token = client.get_tenant_access_token(config.APP_ID, config.APP_SECRET)
    print('tenent', access_token)

    #get root folder token
    root_folder_token = client.get_root_folder_token(access_token)
    print(root_folder_token)

    # # import word to docx
    # import_success, doc_A_url, doc_A_token = import_doc(client, access_token, PARENT_TYPE, root_folder_token, DOC_A_SIZE, DOC_A_PATH)
    # if not import_success:
    #     return
    #
    # print(import_success, doc_A_url, doc_A_token)
    # import_success, doc_B_url, doc_B_token = import_doc(client, access_token, PARENT_TYPE, root_folder_token, DOC_B_SIZE, DOC_B_PATH)
    # if not import_success:
    #     return

    # get_document_blocks
    document_id = 'doxcnU011496YFc2dXIMYSsdWAd'
    infos = client.get_document_infos(access_token, document_id)
    print(infos.data.document)
    blocks = client.get_document_blocks(access_token, document_id)
    # content = client.get_document_raw_content(access_token, document_id=document_id)
    # blocks_json = json.load(blocks)
    h1_blocks = []
    for b in blocks:
        if b["block_type"] == 3:
            h1_blocks.append(b['block_id'])
    print(h1_blocks)
    latest_article = []
    switch = 0
    for b in blocks:
        if b['block_id'] == h1_blocks[0]:
            switch = 1
        if b['block_id'] == h1_blocks[1]:
            switch = 0
        if switch:
            latest_article.append(b)
    pprint(latest_article)


    # # update_docx_permission
    # client.update_docx_permission(access_token, doc_A_token)
    # client.update_docx_permission(access_token, doc_B_token)
    #
    # # update link
    # update_link(client, access_token, doc_A_token, blocks, doc_B_url)
    #
    # print(doc_A_url)

    return

if __name__ == "__main__":
    link()
