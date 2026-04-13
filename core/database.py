import sqlite3
from pathlib import Path

class Database:
    def __init__(self, db_name="taskhub.db"):
        # DB 파일은 앱 최상단에 생성됩니다.
        self.db_path = Path(db_name)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        """즐겨찾기 저장을 위한 테이블 생성"""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                display_name TEXT NOT NULL,
                folder_path TEXT NOT NULL UNIQUE
            )
        ''')
        self.conn.commit()

    def add_favorite(self, display_name, folder_path):
        """즐겨찾기 추가 (이미 있는 경로는 무시)"""
        try:
            self.cursor.execute('INSERT INTO favorites (display_name, folder_path) VALUES (?, ?)', 
                                (display_name, folder_path))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False # 이미 존재하는 경로

    def delete_favorite(self, folder_path):
        """즐겨찾기 삭제"""
        self.cursor.execute('DELETE FROM favorites WHERE folder_path = ?', (folder_path,))
        self.conn.commit()

    def get_all_favorites(self):
        """모든 즐겨찾기 목록 가져오기"""
        self.cursor.execute('SELECT display_name, folder_path FROM favorites ORDER BY display_name')
        return self.cursor.fetchall()