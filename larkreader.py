# -*- coding: UTF-8 -*-
import logging
import time
from datetime import datetime
from threading import Timer
from typing import List

import api
import config
from ecdict.stardict import LemmaDB, StarDict, convert_dict

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
logging.basicConfig(format=LOG_FORMAT, level=logging.ERROR)
# logging.basicConfig(format=LOG_FORMAT, level=logging.INFO)

import os

logging.info(os.getcwd())


class LarkReader:
    def __init__(self, document_id):
        self.document_id = document_id
        self.client = api.Client(config.LARK_HOST)
        self.lemma = LemmaDB()
        self.lemma.load('./ecdict/lemma.en.txt')
        self.dict = self.load_dict()
        self.base_time = datetime.now()

        self.tenant_access_token = None
        self.fetch_tenant_access_token()

        self.latest_article = None
        self.recent_revision_id = None
        self.item_children = []
        self.root_block_id = None
        self.pending_update_blocks = {}

    def fetch_tenant_access_token(self):
        self.tenant_access_token = self.client.get_tenant_access_token(config.APP_ID, config.APP_SECRET)
        Timer(5400, self.fetch_tenant_access_token).start()

    def load_dict(self):
        db = os.path.join(os.path.dirname(__file__), 'test.db')
        if len(StarDict(db)) < 10:
            convert_dict(db, './ecdict/ecdict.csv')
        return StarDict(db)

    def reload_blocks(self):
        self.pending_update_blocks = {}

    def parse_document_retrive_new_article(self):
        """
        解析文档，并返回最近一天的文章
        :return:
        """
        self.base_time = datetime.now()
        infos = self.client.get_document_infos(self.tenant_access_token, self.document_id)

        revision_id = infos['document']['revision_id']
        if revision_id and revision_id == self.recent_revision_id:
            return False
        elif revision_id and revision_id != self.recent_revision_id:
            self.recent_revision_id = revision_id

        blocks_data = self.client.get_document_blocks(self.tenant_access_token, self.document_id)
        blocks_item = blocks_data['items']
        h1_blocks = []
        self.item_children = blocks_item[0]['children']
        self.root_block_id = blocks_item[0]['block_id']
        for b in blocks_item:
            if b["block_type"] == 3:
                h1_blocks.append(b['block_id'])
            # if len(h1_blocks) > 3:
            #     break
        latest_article = []
        switch = 0
        for b in blocks_item:
            if b['block_id'] == h1_blocks[0]:
                switch = 1
            if b['block_id'] == h1_blocks[1]:
                switch = -1
            if switch == 1:
                latest_article.append(b)
            if switch == -1:
                break

        print('parse document spent:', datetime.now() - self.base_time)
        return latest_article

    def get_updated_textrun_elements(self, article):
        marked_texrun_list = []
        for new_block in article:
            if new_block['block_id']:
                for latest_block in self.latest_article:
                    if latest_block['block_id'] == new_block['block_id']:
                        if new_block != latest_block:
                            # Todo 等待更新的块太多了，仅筛选有需要的块
                            marked_texrun_list = self.diff_block(latest_block, new_block)
                            if marked_texrun_list:
                                self.pending_update_blocks[new_block['block_id']] = new_block
        self.latest_article = article
        return marked_texrun_list

    def diff_block(self, old_block, new_block):
        marked_textrun_list = []
        old_textrun_list = self.get_marked_textrun_list(old_block)
        new_textrun_list = self.get_marked_textrun_list(new_block)
        for textrun in new_textrun_list:
            if textrun not in old_textrun_list:
                marked_textrun_list.append(
                    {
                        'block_id': new_block['block_id'],
                        'type': 'add',
                        'text': textrun,
                    }
                )
        for textrun in old_textrun_list:
            if textrun not in new_textrun_list:
                marked_textrun_list.append(
                    {
                        'block_id': new_block['block_id'],
                        'type': 'remove',
                        'text': textrun,
                    }
                )
        return marked_textrun_list

    def update_modified_blocks(self):
        try:
            for block_id in self.pending_update_blocks:
                elements = self.pending_update_blocks[block_id]['text']['elements']
                resp = self.client.update_block_link_url(
                    self.tenant_access_token, self.document_id, block_id, elements, self.recent_revision_id)
                print('update modified blocks spent:', datetime.now() - self.base_time)
        except KeyError:
            pass
        return True

    @staticmethod
    def get_marked_textrun_list(block, color=1, underline=True):
        marked_textrun = []
        if 'text' in block:
            for element in block['text']['elements']:
                style = element['text_run']['text_element_style']
                # if 'text_color' in style and style['text_color'] == color:
                if 'underline' in style and style['underline'] == underline:
                    marked_textrun.append(element)
        return marked_textrun

    def process_patch_blocks(self, block_id, new_textrun_element):
        processed_elements = []
        for textrun_element in self.pending_update_blocks[block_id]['text']['elements']:
            if textrun_element['text_run']['content'] == new_textrun_element['text_run']['content']:
                new_textrun_element['text_run']['text_element_style']["bold"] = True
                new_textrun_element['text_run']['text_element_style']["text_color"] = 1
                new_textrun_element['text_run']['text_element_style']["underline"] = False
                processed_elements.append(new_textrun_element)
            else:
                processed_elements.append(textrun_element)
        self.pending_update_blocks[block_id]['text']['elements'] = processed_elements

    def lookup_quote_block_positions(self, new_article, updated_elements):
        insert_list = []
        for ele in updated_elements:
            start_lookup = 0
            # 增加标红
            if ele['type'] == 'add':
                for block in new_article:
                    if ele['block_id'] == block['block_id']:
                        start_lookup = 1
                    if start_lookup:
                        if 'text' in block and block['text']["elements"][0]["text_run"]["content"] != "":
                            pass
                        else:
                            start_lookup = 0
                            index = self.item_children.index(block['block_id'])
                            insert_list.append((index, ele['text']))

            # 删除标红
            else:
                pass
        return insert_list

    def insert_quote_block(self, new_article, updated_elements):
        insert_list = self.lookup_quote_block_positions(new_article, updated_elements)
        for index, textrun in insert_list:
            if self.get_lemma_text(textrun['text_run']['content'].split()):
                lemma_text = self.get_lemma_text(textrun['text_run']['content'].split())
            else:
                lemma_text = textrun['text_run']['content'].split()
            translation = self.get_translated_result(lemma_text)
            payload = [
                {
                    "block_type": 2,
                    "text": {
                        "elements": [
                            {
                                "text_run": {
                                    "content": lemma_text,
                                    "text_element_style": {
                                        "bold": True,
                                    }
                                }
                            },
                            {
                                "text_run": {
                                    "content": ': ' + translation,
                                    "text_element_style": {
                                        # "text_color": 5
                                    }
                                }
                            },
                        ],
                        "style": {}
                    }
                }
            ]

            self.client.create_document_block(
                self.tenant_access_token, self.document_id, self.root_block_id, index, payload)
        self.reload_blocks()
        print('insert translations spent:', datetime.now() - self.base_time)

    def get_translated_result(self, source_text, source_language='en', target_language='zh'):
        local_translation = self.retrieve_local_translation(source_text)
        if local_translation:
            if 'cet6' in local_translation['tag']:
                return '【cet6】' + local_translation['translation'].replace('\n', '; ')
            elif local_translation['frq'] > 0 and (local_translation['frq'] // 470) < 25:
                frq = '【前' + str(local_translation['frq'] // 470) + '%】'
                return frq + local_translation['translation'].replace('\n', '; ')
            else:
                return local_translation['translation'].replace('\n', '; ')
        else:
            return self.client.translate(self.tenant_access_token, source_language, source_text, target_language)

    def get_lemma_text(self, source_text):
        lemma_text = []
        for t in source_text:
            lemma_text.append(self.lemma.word_stem(t)[0] if self.lemma.word_stem(t) else t)
        return ' '.join(lemma_text)

    def retrieve_local_translation(self, lemma_text):
        if self.dict.match(lemma_text):
            return self.dict.query(lemma_text)
        else:
            return False


if __name__ == "__main__":
    document_id = 'doxcnU011496YFc2dXIMYSsdWAd'
    reader = LarkReader(document_id)
    while True:
        new_article = reader.parse_document_retrive_new_article()
        if not reader.latest_article:
            reader.latest_article = new_article
        if new_article:
            updated_elements = reader.get_updated_textrun_elements(new_article)
            for e in updated_elements:
                reader.process_patch_blocks(e['block_id'], e['text'])
            reader.update_modified_blocks()
            reader.insert_quote_block(new_article, updated_elements)

        # time.sleep(0.6)
