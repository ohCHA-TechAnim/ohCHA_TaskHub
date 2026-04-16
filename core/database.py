import sqlite3
from pathlib import Path

class Database:
    def __init__(self, db_name="taskhub.db"):
        self.db_path = Path(db_name)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS favorites (id INTEGER PRIMARY KEY AUTOINCREMENT, display_name TEXT NOT NULL, folder_path TEXT NOT NULL UNIQUE)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS todos (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, details TEXT, memo TEXT, is_done BOOLEAN NOT NULL DEFAULT 0)''')
        
        try: self.cursor.execute('ALTER TABLE todos ADD COLUMN order_idx INTEGER DEFAULT 0')
        except sqlite3.OperationalError: pass
        
        # 🔥 이미지를 따로 보관할 전용 공간 추가!
        try: self.cursor.execute('ALTER TABLE todos ADD COLUMN images TEXT DEFAULT ""')
        except sqlite3.OperationalError: pass
            
        self.conn.commit()

    # --- 즐겨찾기 ---
    def add_favorite(self, display_name, folder_path):
        try:
            self.cursor.execute('INSERT INTO favorites (display_name, folder_path) VALUES (?, ?)', (display_name, folder_path))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError: return False
    def delete_favorite(self, folder_path):
        self.cursor.execute('DELETE FROM favorites WHERE folder_path = ?', (folder_path,))
        self.conn.commit()
    def get_all_favorites(self):
        self.cursor.execute('SELECT display_name, folder_path FROM favorites ORDER BY display_name')
        return self.cursor.fetchall()

    # --- TO-DO ---
    def add_todo(self, title):
        self.cursor.execute('SELECT MAX(order_idx) FROM todos')
        max_order = self.cursor.fetchone()[0]
        next_order = 0 if max_order is None else max_order + 1
        
        self.cursor.execute('INSERT INTO todos (title, details, memo, is_done, order_idx, images) VALUES (?, "", "", 0, ?, "")', (title, next_order))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_all_todos(self):
        # 🔥 images 컬럼을 포함하여 총 7개의 데이터를 반환합니다.
        self.cursor.execute('SELECT id, title, details, memo, is_done, order_idx, images FROM todos ORDER BY order_idx ASC')
        return self.cursor.fetchall()

    def update_todo(self, todo_id, field, value):
        if field == "is_done": value = 1 if int(value) == 1 else 0
        self.cursor.execute(f'UPDATE todos SET {field} = ? WHERE id = ?', (value, todo_id))
        self.conn.commit()
        
    def update_todo_order(self, todo_id, new_order):
        self.cursor.execute('UPDATE todos SET order_idx = ? WHERE id = ?', (new_order, todo_id))
        self.conn.commit()

    def delete_todo(self, todo_id):
        self.cursor.execute('DELETE FROM todos WHERE id = ?', (todo_id,))
        self.conn.commit()