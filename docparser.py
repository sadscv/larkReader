import os
import re

import requests

from larkreader import LarkReader
from paragraphDict import ParagraphDict


class DocParser(LarkReader):
    def __init__(self, document_id, lookup_doc_id=None):
        super(DocParser, self).__init__(document_id, lookup_doc_id)
        self.backup_path = './archive/'
        self.img_path = './archive/img/'
        self.img_tokens = set()

    def download_all_images(self):
        for token in self.img_tokens:
            file_name = f'{token}.png'
            file_path = f'{self.img_path}{file_name}'
            if os.path.exists(file_path):
                continue
            else:
                with open(f'{self.img_path}{file_name}', "wb") as file:
                    url = f'https://open.feishu.cn/open-apis/drive/v1/medias/{token}/download'
                    print(f'Downloading image {token}')
                    resp = requests.get(url, headers={
                        'Authorization': f'Bearer {self.tenant_access_token}'
                    })
                    file.write(resp.content)
        return True

    def convert2md(self, article):
        blocks = article['content']
        article_index = {
            'H1': None,
            'subtitle': None,
            'paragraph': []
        }

        processing_paragraph = None

        def get_new_paragraph_dict(last_dict=None):
            if last_dict:
                article_index['paragraph'].append(last_dict)
            para_dict = {
                'para_text': [],
                'words': [],
                'others': [],
            }
            return para_dict

        for i in range(len(blocks)):
            block_type, block_text = self.walk(blocks[i])
            if i < 5 and block_type == 3:
                article_index['H1'] = i
                processing_paragraph = get_new_paragraph_dict(processing_paragraph)
                processing_paragraph['para_text'] = [i]
                continue
            if block_type == 2:
                if not block_text:
                    continue
                if i - article_index['H1'] == 1 and block_text.startswith('**') and block_text.endswith('**'):
                    article_index['subtitle'] = i
                    processing_paragraph['para_text'].append(i)
                    continue
                # 不含中文的长段落，筛选段落文本
                if not self.is_include_chinese(block_text) and len(block_text.strip()) > 15:
                    if block_text[0].isdigit():
                        processing_paragraph = get_new_paragraph_dict(processing_paragraph)
                        processing_paragraph['para_text'] = [i]
                    if not block_text[0].isdigit():
                        if i - processing_paragraph['para_text'][-1] == 1 and not self.similar_to_words(block_text):
                            processing_paragraph['para_text'].append(i)
                        else:
                            processing_paragraph['words'].append(i)
                elif self.similar_to_words(block_text):
                    processing_paragraph['words'].append(i)
            else:
                processing_paragraph['others'].append(i)

        # 最后收尾
        get_new_paragraph_dict(processing_paragraph)

        self.dump_article_to_md(article, article_index)

    def dump_article_to_md(self, article, article_index):

        def new_para_dict_with_words():
            para_dict = {
                'para_text': '',
                'para_words': '',
                'new_words': set(),
                'para_raw':[]
            }
            return para_dict

        paragraph_dict_list = []

        text = ''
        blocks = article['content']
        print(article['day'], article_index)
        heading_index, subtitle_index = article_index['H1'], article_index['subtitle']
        if subtitle_index:
            subtitle_raw_text = self.get_block_raw_text(blocks[subtitle_index])
            # _, subtitle_text = self.walk(blocks[subtitle_index])
            text = '''---\ndescription: {}\n---\n'''.format(subtitle_raw_text)
            text += '\n'
        _, heading_text = self.walk(blocks[heading_index])
        text += heading_text
        text += '\n'

        # 第0段处理

        para_dict = new_para_dict_with_words()

        if article_index['paragraph'][0]['para_text']:
            for para_text_idx in article_index['paragraph'][0]['para_text']:
                _, para_text = self.walk(blocks[para_text_idx])
                para_dict['para_text'] += (para_text + '\n')

        if article_index['paragraph'][0]['words']:
            for para_word_idx in article_index['paragraph'][0]['words']:
                _, para_word = self.walk(blocks[para_word_idx])
                text += '> ' + para_word
                text += '\n '
                text += '> \n'
                para_dict['para_words'] += para_word + '\n ' + '> \n'
            text += '\n'

        if article_index['paragraph'][0]['others']:
            for para_other_idx in article_index['paragraph'][0]['others']:
                _, para_other = self.walk(blocks[para_other_idx])
                if para_other:
                    text += para_other
                    text += '\n'
            text += '\n'

        paragraph_dict_list.append(self.parse_para_dict(para_dict))

        # 第1段及之后处理
        for paragraph in article_index['paragraph'][1:]:
            para_dict = new_para_dict_with_words()

            if paragraph['para_text']:
                for para_text_idx in paragraph['para_text']:
                    _, para_text = self.walk(blocks[para_text_idx])
                    text += para_text
                    text += '\n'
                    para_dict['para_text'] += para_text + '\n'
                    para_dict['para_raw'].append(blocks[para_text_idx])
                text += '\n'

            if paragraph['words']:
                for para_word_idx in paragraph['words']:
                    _, para_word = self.walk(blocks[para_word_idx])
                    text += '> ' + para_word
                    text += '\n'
                    text += '>\n'
                    para_dict['para_words'] += para_word + '\n ' + '>\n'
                    # print(blocks[para_word_idx])
                    para_dict['para_raw'].append(blocks[para_word_idx])
                text += '\n'
            if paragraph['others']:
                for para_other_idx in paragraph['others']:
                    _, para_other = self.walk(blocks[para_other_idx])
                    if para_other:
                        text += para_other
                        text += '\n'
                text += '\n'

            print(para_dict['para_raw'])
            paragraph_dict_list.append(self.parse_para_dict(para_dict))

        os.makedirs(self.backup_path, exist_ok=True)
        # filename = '_'.join(article['title'].split())
        with open(self.backup_path + '【' + article['day'] + '】' + '.md', 'w') as f:
            f.write(text)

        article_dict = {
            'raw_content': article['content'],
            'day': article['day'],
            'title': article['title'],
            'paragraph': paragraph_dict_list,
        }

        self.save_to_db(article_dict)

    def similar_to_words(self, block_text):
        if self.is_include_chinese(block_text):
            return True
        if '**' in block_text and len(block_text.split()) < 35:
            # 小标题
            if block_text[:2] == "**" and block_text[-2:] == "**" and '**' not in block_text[2:-2]:
                return True
            if any(patten in block_text for patten in ['**:', ':**', '**：', '：**']):
                return True
        return False

    def walk(self, block):
        # 此处参考 https://github.com/jiegec/feishu-backup/blob/master/backup.py
        block_type = block['block_type']
        if block_type == 2:
            result = self.convert_text(block)
        elif block_type == 3:
            result = self.convert_heading(block, 1)
        elif block_type == 5:
            result = self.convert_heading(block, 3)
        elif block_type == 27:
            result = self.convert_image(block)
        # elif block['block_type'] == 34:
        #     result = self.convert_quote(block)
        elif block_type == 22:
            result = self.convert_divider(block)
        elif block_type == 13:
            result = self.convert_orderlist(block)
        elif block_type == 19:
            result = self.covert_callout(block)
        else:
            result = None
        return block_type, result

    def parse_document(self):
        blocks = []
        keep_fetch = True
        page_token = None
        while keep_fetch:
            blocks_data = self.client.get_document_blocks(self.tenant_access_token, self.document_id, page_token)
            if not blocks_data['has_more']:
                keep_fetch = False
            else:
                page_token = blocks_data['page_token']
            blocks += blocks_data['items']
            print('block_len:', len(blocks))

        article_list = []
        article = {}
        heading_count = -1
        for b in blocks:
            if b["block_type"] == 3:
                heading1_text = self.get_block_raw_text(b, b_type='heading1')
                if heading1_text:
                    day_num, title = self.parse_heading_text(heading1_text)
                    heading_count += 1
                    if heading_count > 0:
                        article_list.append(article)
                    article = {
                        'day': day_num,
                        'title': title,
                        'content': [b]
                    }
            elif 'content' in article:
                # 正文
                article['content'].append(b)
        return article_list

    @staticmethod
    def get_block_raw_text(block, b_type='text'):
        if b_type not in block:
            print(block)
            return False

        elements = block[b_type]['elements']
        raw_text = ''
        for ele in elements:
            if 'text_run' in ele:
                raw_text += ele['text_run']['content']
        if raw_text == '':
            return False
        else:
            return raw_text

    def is_subtitle(self, block, recent):
        if not recent:
            return False

    @staticmethod
    def parse_heading_text(heading1):
        day = heading1.split()[0].strip()
        title = heading1[len(day):].strip()
        if day.lower().startswith(('d', 'day')):
            return day, title
        else:
            print('heading error:', day)

    def convert_text(self, block):
        if 'text' not in block:
            print(block)
            return False

        elements = block['text']['elements']
        raw_text = ''
        for ele in elements:
            if 'text_run' in ele:
                ele_style = ele['text_run']['text_element_style']
                # 标红或加粗
                if ('text_color' in ele_style and ele_style['text_color'] == 1) or ele_style['bold']:
                    # 空格直接处理
                    if ele['text_run']['content'] == ' ':
                        raw_text += ele['text_run']['content']
                        continue
                    # 加粗标识 ** **  合并消除
                    if raw_text[-2:] == '**':
                        raw_text = raw_text[:-2] + ele['text_run']['content'] + '**'
                    else:
                        if ele['text_run']['content'][0] == ' ':
                            raw_text += ' **'
                        else:
                            raw_text += '**'

                        raw_text += ele['text_run']['content'].strip()

                        if ele['text_run']['content'][-1] == ' ':
                            raw_text += '** '
                        else:
                            raw_text += '**'

                    if raw_text[-3:] == ':**' or raw_text[-3:] == '：**':
                        raw_text = raw_text[:-3] + '**: '

                else:
                    raw_text += ele['text_run']['content']
        if raw_text in ['', ' ']:
            return False
        else:
            # # 判断段落文章
            # if raw_text[0].isdigit():
            #     if len(raw_text) <100:
            #         print(len(raw_text), raw_text, self.current_parsing['title'])
            if ':' in raw_text or '：' in raw_text:
                pass
            elif len(raw_text) > 250:
                pass
            elif raw_text[0].isdigit():
                pass
            elif self.is_include_chinese(raw_text):
                pass
            else:
                pass
                # print(len(raw_text), raw_text, self.current_parsing['article']['title'])
            return raw_text.strip()

    def convert_heading(self, block, heading_level=1):
        heading1_text = self.get_block_raw_text(block, b_type='heading{}'.format(heading_level))
        if not heading1_text:
            heading1_text = ''
        return '#' * heading_level + ' ' + heading1_text

    def convert_image(self, block):
        image_token = block['image']['token']
        file_name = image_token + '.png'
        if image_token:
            self.img_tokens.add(image_token)
            return '![](' + './img/' + file_name + ')'
        else:
            return False

    @staticmethod
    def convert_divider(block):
        return '\n' + '---'

    def convert_quote(self, block):
        pass

    def convert_orderlist(self, block):
        return False

    def covert_callout(self, block):
        return False

    @staticmethod
    def is_include_chinese(text):
        for ch in text:
            if u'\u4e00' <= ch <= u'\u9fff':
                return True
        return False

    def parse_para_dict(self, para_dict):
        word_set = set()
        star_positions = set()
        # bold_regex ='/\*\*(.*?)\*\*/gm'
        bold_regex = re.compile('(?<=\*\*).+?(?=\*\*)')
        pending_match_text = para_dict['para_text'] + para_dict['para_words']
        matched = bold_regex.finditer(pending_match_text)
        for m in matched:
            if m.start() not in star_positions:
                star_positions.add(m.start())
                # 需要加上末尾的两个*
                star_positions.add(m.end() + 2)
                word = m.group()
                if len(word.split()) < 5:
                    word_set.add(word)

        # 所有词过一遍lemma
        para_dict['new_words'] = set(self.get_lemma_text(w.strip().split()) for w in word_set)
        return para_dict

    @staticmethod
    def save_to_db(article_dict):
        db = os.path.join(os.path.dirname(__file__), 'test.db')
        pd = ParagraphDict(db)
        pd.batch_register(article_dict)
        return True


if __name__ == '__main__':
    # document_ids = ['doxcnU011496YFc2dXIMYSsdWAd']
    document_ids = ['doxcnU011496YFc2dXIMYSsdWAd', 'doxcnCTsMwN5JqEWxqMDppxdkvb']
    parser = DocParser(document_ids[0])
    article_list = []
    for document_id in document_ids:
        parser.document_id = document_id
        article_list += parser.parse_document()
    for article in article_list:
        # if article['day'].startswith('D802'):
        parser.convert2md(article)
    parser.download_all_images()
