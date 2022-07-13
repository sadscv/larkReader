from larkreader import LarkReader


class DocParser(LarkReader):
    def __init__(self, document_id):
        super().__init__(document_id)

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
        heading = None
        heading_count = -1
        for b in blocks:
            if b["block_type"] == 3:
                heading = self.get_block_raw_text(b, b_type='heading1')
                day_num = self.get_day_num(heading)
                heading_count += 1
                if heading_count > 0:
                    article_list.append(article)
                article = {
                    'title': day_num,
                    'heading': heading,
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
        return raw_text

    @staticmethod
    def get_day_num(heading1):
        day = heading1.split()[0]
        print(day)
        if day.lower().startswith(('d', 'day')):
            return heading1[:4]
        else:
            print('heading error:', day)


if __name__ == '__main__':
    document_id = 'doxcnU011496YFc2dXIMYSsdWAd'
    parser = DocParser(document_id)
    article_list = parser.parse_document()
    for article in article_list:
        print(article)
