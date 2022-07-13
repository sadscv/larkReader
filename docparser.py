import os

from larkreader import LarkReader


class DocParser(LarkReader):
    def __init__(self, document_id):
        super().__init__(document_id)
        self.backup_path = './archive/'

    def convert2md(self, article):
        text = ''
        for block in article['content']:
            if self.walk(block):
                text += self.walk(block)
            text += '\n'
        os.makedirs(self.backup_path, exist_ok=True)
        with open(self.backup_path+article['title']+'.md', 'w') as f:
            print(text)
            f.write(text)

    def walk(self, block):
        # 此处参考 https://github.com/jiegec/feishu-backup/blob/master/backup.py
        if block['block_type'] == 2:
            return self.convert_text(block)
        elif block['block_type'] == 3:
            return self.convert_heading(block, 1)
        elif block['block_type'] == 5:
            return self.convert_heading(block, 3)
        elif block['block_type'] == 27:
            return self.convert_image(block)
        elif block['block_type'] == 34:
            self.convert_quote(block)
        elif block['block_type'] == 22:
            self.convert_divider(block)
        elif block['block_type'] == 13:
            self.convert_orderlist(block)
        else:
            pass

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
        heading1_text = None
        heading_count = -1
        for b in blocks:
            if b["block_type"] == 3:
                heading1_text = self.get_block_raw_text(b, b_type='heading1')
                if not heading1_text:
                    continue
                day_num = self.get_day_num(heading1_text)
                heading_count += 1
                if heading_count > 0:
                    article_list.append(article)
                article = {
                    'title': day_num,
                    'heading': heading1_text,
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

    @staticmethod
    def get_day_num(heading1):
        day = heading1.split()[0]
        print(day)
        if day.lower().startswith(('d', 'day')):
            return heading1[:4]
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
                    # 加粗标识 ** **  合并消除
                    if raw_text[-3:] == '** ':
                        raw_text = raw_text[:-3] +ele['text_run']['content'] + '** '
                    else:
                        raw_text += '**' + ele['text_run']['content'] + '** '
                else:
                    raw_text += ele['text_run']['content']
        if raw_text == '':
            return False
        else:
            return raw_text

    def convert_heading(self, block, heading_level=1):
        heading1_text = self.get_block_raw_text(block, b_type='heading1')
        if not heading1_text:
            heading1_text = ''
        return '#'*heading_level + ' ' + heading1_text

    def convert_image(self, block):
        return None

    def convert_quote(self, block):
        pass

    def convert_divider(self, block):
        pass

    def convert_orderlist(self, block):
        pass


if __name__ == '__main__':
    document_ids = ['doxcnU011496YFc2dXIMYSsdWAd']
    # document_ids = ['doxcnU011496YFc2dXIMYSsdWAd', 'doxcnCTsMwN5JqEWxqMDppxdkvb']
    parser = DocParser(document_ids[0])
    article_list = []
    for document_id in document_ids:
        parser.document_id = document_id
        article_list += parser.parse_document()
    for article in article_list:
        parser.convert2md(article)
