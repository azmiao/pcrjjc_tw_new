import os
import sqlite3

import hoshino

JJCHistory_DB_PATH = os.path.expanduser('~/.hoshino/jjchistory.db')


class JJCHistoryStorage:
    def __init__(self):
        os.makedirs(os.path.dirname(JJCHistory_DB_PATH), exist_ok=True)
        self._create_table()

    @staticmethod
    def _connect():
        return sqlite3.connect(JJCHistory_DB_PATH)

    def _create_table(self):
        try:
            self._connect().execute('''CREATE TABLE IF NOT EXISTS JJCHistoryStorage
                (ID INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                 UID INT  NOT NULL,
                 DATETIME DATETIME DEFAULT(datetime('now','localtime')),
                 ITEM INT NOT NULL,
                 BEFORE INT NOT NULL,
                 AFTER INT NOT NULL
                  )
                '''
                                    )
        except Exception as _:
            raise Exception('创建JJCHistory表失败')

    def add(self, uid, item, before, after):
        conn = self._connect()
        try:
            conn.execute('INSERT INTO JJCHistoryStorage (UID,ITEM,BEFORE,AFTER) VALUES (?,?,?,?)',
                         (uid, item, before, after))
            conn.commit()
        except Exception as _:
            raise Exception('新增记录异常')

    def refresh(self, user_id, item_type):
        conn = self._connect()
        try:
            conn.execute('''delete from JJCHistoryStorage
where ID in
(select ID from JJCHistoryStorage 
where UID=? and ITEM = ?
order by DATETIME desc 
limit(select count(*) FROM JJCHistoryStorage WHERE UID = ? and ITEM = ?) offset 10)
            ''', (user_id, item_type, user_id, item_type))
            conn.commit()
        except Exception as _:
            raise Exception('更新记录异常')

    def select(self, user_id, item_type):
        conn = self._connect().cursor()
        try:
            if item_type == 1:
                item_name = '竞技场'
            else:
                item_name = '公主竞技场'
            result = conn.execute('''
            select * from JJCHistoryStorage WHERE UID=? and ITEM = ? ORDER  BY DATETIME desc''', (user_id, item_type))
            result_list = list(result)
            # print(result_list)
            # print(f"长度{len(result_list)}")
            if len(result_list) != 0:
                msg = f'竞技场绑定ID: {user_id}\n{item_name}历史记录'
                for row in result_list:
                    if row[4] > row[5]:
                        jjc_msg = f'\n【{row[2]}】{row[4]}->{row[5]} ▲{row[4] - row[5]}'
                    else:
                        jjc_msg = f'\n【{row[2]}】{row[4]}->{row[5]} ▼{row[5] - row[4]}'
                    msg = msg + jjc_msg
                return msg
            else:
                msg = f'竞技场绑定ID: {user_id}\n{item_name}历史记录\n无记录'
                return msg
        except Exception as _:
            raise Exception('查找记录异常')

    def remove(self, user_id):
        conn = self._connect()
        try:
            conn.execute('delete from JJCHistoryStorage where UID = ?', (user_id,))
            conn.commit()
            hoshino.logger.info(f'移除ID:{user_id}的竞技场记录')
        except Exception as _:
            raise Exception('移除记录异常')
