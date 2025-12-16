import sqlite3
import json
import os
from contextlib import contextmanager

DB_NAME = "trivia.db"

def get_db_connection():
    """Establishes a connection to the SQlite database."""
    return sqlite3.connect(DB_NAME)

@contextmanager
def get_db_cursor():
    """
    Context manager for database connections.
    Automatically handles commits, rollbacks, and closing connections.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        yield conn, cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    """Initializes the database, creates tables, and adds questions."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Users Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                correct_count INTEGER DEFAULT 0,
                incorrect_count INTEGER DEFAULT 0,
                quizzes_taken INTEGER DEFAULT 0
            )
        ''')

        # Questions Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_text TEXT,
                correct_answer TEXT,
                options_json TEXT,
                category TEXT DEFAULT 'General'
            )
        ''')

        # Answers Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS answered_questions (
                user_id INTEGER,
                question_id INTEGER,
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                FOREIGN KEY(question_id) REFERENCES questions(id)
            )
        ''')

        cursor.execute('SELECT COUNT(*) FROM questions')
        if cursor.fetchone()[0] == 0:
            print("Populating database with questions...")

            #refactoring logic for JSON mapping
            base_dir = os.path.dirname(os.path.abspath(__file__))
            json_path = os.path.join(base_dir, "21pilots_questions.json")

            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    questions_data = json.load(f)

                for item in questions_data:
                        category = item.get('category', 'General')
                        q = item['question']
                        a = item['answer']
                        opts = json.dumps(item['options'])

                        cursor.execute('INSERT INTO questions (question_text, correct_answer, options_json, category) VALUES (?, ?, ?, ?)', (q, a, opts, category))
                conn.commit()
                print("Questions loaded successfully!")
            else:
                print("Error: 21pilots_questions.json not found!")
        else:
            print("Database already initialized and populated.")
        conn.close()
        return True
    
    except Exception as e:
        print(f"Error initializing database: {e}")
        return False

if __name__ == "__main__":
    if init_db():
        print(f"Database initialized successfully at: {DB_NAME}")
    else:
        print("Error: database wasn't initialized correctly!")

    try:
        with get_db_cursor() as (conn, cursor):
            print("\n--CURRENT DB STATUS--")
            
            cursor.execute("SELECT COUNT(*) FROM questions")
            q_count = cursor.fetchone()[0]
            print(f"\nTotal Questions: {q_count}")

            print("User Stats:")
            cursor.execute("SELECT user_id, correct_count, incorrect_count, quizzes_taken FROM users")
            users = cursor.fetchall()
            
            if users:
                for u in users:
                    print(f"    User ID: {u[0]} | ✅ Correct: {u[1]} | ❌ Incorrect: {u[2]} | Total: {u[3]}")
            else:
                print("     No users found yet.")
    except Exception as e:
        print(f"Error reading stats: {e}")