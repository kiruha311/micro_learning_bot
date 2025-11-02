import sqlite3
import logging
from datetime import datetime

class Database:
    def __init__(self, db_path='wiki_bot.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.init_db()
    
    def init_db(self):
        """Инициализация базы данных и создание таблиц"""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS sent_articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                summary TEXT,
                sent_date DATE NOT NULL,
                sent_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(chat_id, url, sent_date)
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                chat_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                registered_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                action_type TEXT NOT NULL,
                action_date DATE NOT NULL,
                FOREIGN KEY (chat_id) REFERENCES users (chat_id)
            )
        ''')
        
        self.conn.commit()
    
    def add_user(self, chat_id, username=None, first_name=None, last_name=None):
        """Добавление нового пользователя"""
        self.cursor.execute('''
            INSERT OR REPLACE INTO users (chat_id, username, first_name, last_name, is_active)
            VALUES (?, ?, ?, ?, TRUE)
        ''', (chat_id, username, first_name, last_name))
        self.conn.commit()
    
    def add_sent_article(self, chat_id, title, url, summary):
        """Добавление отправленной статьи в базу"""
        sent_date = datetime.now().date()
        
        try:
            self.cursor.execute('''
                INSERT INTO sent_articles (chat_id, title, url, summary, sent_date)
                VALUES (?, ?, ?, ?, ?)
            ''', (chat_id, title, url, summary, sent_date))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            logging.warning(f"Статья уже отправлена сегодня: {title}")
            return False
    
    def log_action(self, chat_id, action_type):
        """Логирование действий пользователя"""
        self.cursor.execute('''
            INSERT INTO statistics (chat_id, action_type, action_date)
            VALUES (?, ?, DATE('now'))
        ''', (chat_id, action_type))
        self.conn.commit()
    
    def was_article_sent_today(self, chat_id):
        """Проверка, отправлялась ли сегодня статья"""
        self.cursor.execute('''
            SELECT COUNT(*) FROM sent_articles 
            WHERE chat_id = ? AND sent_date = DATE('now')
        ''', (chat_id,))
        count = self.cursor.fetchone()[0]
        return count > 0
    
    def get_sent_articles_history(self, chat_id, limit=10):
        """Получение истории отправленных статей"""
        self.cursor.execute('''
            SELECT title, url, sent_date 
            FROM sent_articles 
            WHERE chat_id = ? 
            ORDER BY sent_date DESC, sent_time DESC 
            LIMIT ?
        ''', (chat_id, limit))
        return self.cursor.fetchall()
    
    def get_user_stats(self, chat_id):
        """Получение статистики пользователя"""
        self.cursor.execute('SELECT COUNT(*) FROM sent_articles WHERE chat_id = ?', (chat_id,))
        total_articles = self.cursor.fetchone()[0]
        
        self.cursor.execute('''
            SELECT COUNT(*) FROM sent_articles 
            WHERE chat_id = ? AND sent_date >= DATE('now', '-7 days')
        ''', (chat_id,))
        last_week_articles = self.cursor.fetchone()[0]
        
        self.cursor.execute('''
            SELECT title, COUNT(*) as count 
            FROM sent_articles 
            WHERE chat_id = ? 
            GROUP BY title 
            ORDER BY count DESC 
            LIMIT 1
        ''', (chat_id,))
        favorite_topic = self.cursor.fetchone()
        
        return {
            'total_articles': total_articles,
            'last_week_articles': last_week_articles,
            'favorite_topic': favorite_topic
        }
    
    def get_article_by_date(self, chat_id, target_date):
        """Получение статьи по дате"""
        self.cursor.execute('''
            SELECT title, url, summary 
            FROM sent_articles 
            WHERE chat_id = ? AND sent_date = ?
        ''', (chat_id, target_date))
        return self.cursor.fetchone()

    def get_random_article_from_history(self, chat_id):
        """Получение случайной статьи из истории"""
        self.cursor.execute('''
            SELECT title, url, summary 
            FROM sent_articles 
            WHERE chat_id = ? 
            ORDER BY RANDOM() 
            LIMIT 1
        ''', (chat_id,))
        return self.cursor.fetchone()