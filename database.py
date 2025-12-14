import sqlite3
import json

DB_NAME = "trivia.db"

def get_db_connection():
    """Establishes a connection to the SQlite database."""
    return sqlite3.connect(DB_NAME)

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
                options_json TEXT
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
            top_questions = [
                ("What is the name of Tyler Joseph's ukulele?", "Lehua", ["Coco", "Lehua", "Stitch", "Uke"]),
                ("Which album features the song 'Stressed Out'?", "Blurryface", ["Vessel", "Trench", "Blurryface", "Scaled and Icy"]),
                ("What is the fictional city central to the Trench era lore?", "Dema", ["Voldsoy", "Dema", "Keons", "Nico"]),
                ("Who is the drummer of Twenty One Pilots?", "Josh Dun", ["Tyler Joseph", "Chris Salih", "Nick Thomas", "Josh Dun"]),
                ("Which song contains the lyrics: 'The sun will rise and we will try again'?", "Truce", ["Goner", "Trees", "Truce", "Car Radio"]),
                ("What is the color scheme associated with the 'Scaled and Icy' era?", "Pink and Blue", ["Yellow and Black", "Red and Black", "Pink and Blue", "Green and Purple"]),
                ("How many bishops are there in Dema?", "9", ["7", "9", "12", "5"]),
                ("What was the name of the band's debut self-titled album?", "Twenty One Pilots", ["Regional at Best", "Vessel", "Twenty One Pilots", "No Phun Intended"]),
                ("Which character represents Tyler's insecurities in the Blurryface era?", "Blurryface", ["Nico", "Clancy", "Blurryface", "Ned"]),
                ("What is the name of the small alien creature that appears in the 'Chlorine' video?", "Ned", ["Fred", "Ned", "Ted", "Jim"])
            ]
            
            for q, a, opts in top_questions:
                cursor.execute('INSERT INTO questions (question_text, correct_answer, options_json) VALUES (?, ?, ?)', (q, a, json.dumps(opts)))
            conn.commit()
        
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
        conn = get_db_connection()
        cursor = conn.cursor()

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
        
        conn.close()
    except Exception as e:
        print(f"Error reading stats: {e}")