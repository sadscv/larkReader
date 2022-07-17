import json
import os
import sqlite3


class ParagraphDict(object):

    def __init__(self, filename, verbose=False):
        self.__dbname = filename
        if filename != ':memory:':
            os.path.abspath(filename)
        self.__conn = None
        self.__cursor = None
        self.__verbose = verbose
        self.__open()

    def __open(self):
        sql_para = '''
        CREATE TABLE IF NOT EXISTS "paragraph" (
            "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL UNIQUE,
            "article_raw" TEXT,
            "article_day" VARCHAR(64),
            "article_title" VARCHAR(512),
            "paragraph_text" TEXT,
            "paragraph_raw" TEXT
        );
        CREATE UNIQUE INDEX IF NOT EXISTS "para_1" ON paragraph (id);
        CREATE INDEX IF NOT EXISTS "para_1" ON paragraph (paragraph_text,article_day collate nocase);
        '''

        sql_word = '''
        CREATE TABLE IF NOT EXISTS "words" (
            "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL UNIQUE,
            "description" TEXT,
            "word_raw" VARCHAR(64),
            "count" INT
        );
        CREATE UNIQUE INDEX IF NOT EXISTS "stardict_1" ON words (id);
        CREATE UNIQUE INDEX IF NOT EXISTS "stardict_2" ON words (word_raw);
        '''

        sql_para_word = '''
        CREATE TABLE IF NOT EXISTS "para_word" (
            "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL UNIQUE,
            "para_uid" VARCHAR(64),
            "word_uid" VARCHAR(64)
        );
        CREATE UNIQUE INDEX IF NOT EXISTS "para_word_1" ON para_word (id);
        CREATE UNIQUE INDEX IF NOT EXISTS "para_word_2" ON para_word (para_uid, word_uid);
        '''

        self.__conn = sqlite3.connect(self.__dbname, isolation_level="IMMEDIATE")
        self.__cursor = self.__conn.cursor()
        self.__conn.isolation_level = "IMMEDIATE"

        def parse_sql(sql):
            sql = '\n'.join([n.strip('\t') for n in sql.split('\n')])
            sql = sql.strip('\n')
            return sql

        self.__conn.executescript(parse_sql(sql_para))
        self.__conn.executescript(parse_sql(sql_word))
        self.__conn.executescript(parse_sql(sql_para_word))
        self.__conn.commit()

        fields = ('id', 'article_raw', 'article_day', 'article_title', 'paragraph_raw')
        self.__fields = tuple([(fields[i], i) for i in range(len(fields))])
        self.__names = {}
        for k, v in self.__fields:
            self.__names[k] = v
        self.__enable = self.__fields[3:]
        return True

    def close(self):
        if self.__conn:
            self.__conn.close()
        self.__conn = None

    def __del__(self):
        self.close()

    # 输出日志
    def out(self, text):
        if self.__verbose:
            print(text)
        return True

    def batch_register(self, article_dict):
        article_raw = json.dumps(article_dict['raw_content'])
        article_day = article_dict['day']
        article_title = article_dict['title']
        paragraph_dict = article_dict['paragraph']
        for paragraph in paragraph_dict:
            para_text = paragraph['para_text']
            para_raw = json.dumps(paragraph['para_raw'])
            para_uid, reg_new_para = self.register_para(article_raw, article_day, article_title, para_text, para_raw)
            if reg_new_para:
                for word in paragraph['new_words']:
                    word_uid = self.register_word(word)
                    self.register_para_word(para_uid, word_uid)

    def register_para(self, article_raw, article_day, article_title, paragraph_text, paragraph_raw, commit=True):
        sql = 'select id from paragraph where paragraph_text =?;'
        result = self.__conn.execute(sql, (paragraph_text,)).fetchone()
        if result:
            return result[0], False
        else:
            sql1 = 'INSERT INTO paragraph(article_raw, article_day, article_title, paragraph_text, paragraph_raw) VALUES(?,?,?,?,?) returning id;'
            self.__conn.execute(sql1, (article_raw, article_day, article_title, paragraph_text, paragraph_raw))
            self.__conn.commit()
            return self.__conn.execute('select last_insert_rowid();').fetchone()[0], True

        # return '123'

    def register_word(self, word):
        sql = 'select id, count from words where word_raw=?;'
        result = self.__conn.execute(sql, (word,)).fetchone()
        if result:
            word_uid, count = result
            count += 1
            sql2 = 'update words set count =? where id=?;'
            self.__conn.execute(sql2, (count, word_uid))
            self.__conn.commit()
        else:
            sql3 = 'insert into words(word_raw, count) VALUES (?, ?);'
            self.__conn.execute(sql3, (word, 1))
            self.__conn.commit()
            word_uid = self.__conn.execute('select last_insert_rowid();').fetchone()[0]
        return word_uid

    def register_para_word(self, para_uid, word_uid):
        sql = 'insert into para_word(para_uid, word_uid) VALUES(?,?);'
        self.__conn.execute(sql, (para_uid, word_uid))
        self.__conn.commit()

    def query_word(self, word):
        sql = '''
            SELECT 
            words.word_raw AS word, 
            words.count AS count, 
            paragraph.paragraph_raw AS para_raw, 
            paragraph.article_day AS day, 
            paragraph.article_title AS title
            FROM 
            words
            LEFT JOIN para_word ON para_word.word_uid = words.id
            LEFT JOIN paragraph ON para_word.para_uid = paragraph.id
            WHERE
            words.word_raw = ?
            '''
        return self.__conn.execute(sql, (word,)).fetchall()
