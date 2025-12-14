import random, discord, os, json
from discord.ext import commands
from dotenv import load_dotenv
from database import init_db, get_db_connection, DB_NAME

load_dotenv(override=True)
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

bot_intents = discord.Intents.default()
bot_intents.message_content = True
bot = commands.Bot(command_prefix='@', intents=bot_intents)

user_sessions = {}

@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user.name}.")
    if not DISCORD_TOKEN:
        print("Error: the .env file wasn't read correctly!")

    if init_db():
        print(f"Database {DB_NAME} initialized successfuly.")
    else:
        print("Error: database wasn't initialized correctly!")

@bot.event
async def on_command_error(context, error):
    '''
    Handles unknown commands.
    '''
    if isinstance(error, commands.CommandNotFound):
        await context.send("❌ Unknown command! Try `@quiz`, `@answer <your_answer>` or `@stats`.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await context.send("⚠️ Missing argument! Try: `@answer 21pilots`")
    else:
        print(f"Unknown error: {error}")

@bot.command()
async def quiz(context):
    '''
    Starts a quiz session for the user.
    
    First, it checks if the user has an unanswered question, and if not, the quiz starts, by picking a random question and store the answer in the database. 
    In the end, it will display the question to the user.
    '''
    user_id = context.author.id

    if user_id in user_sessions:
        await context.send("You already have an active question which you haven't answered yet! (Tip: use `@answer <your_answer>`)")
        return
    
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
    conn.commit()

    cursor.execute('''
        SELECT id, question_text, correct_answer, options_json 
        FROM questions 
        WHERE id NOT IN (SELECT question_id FROM answered_questions WHERE user_id = ?)
        ORDER BY RANDOM() LIMIT 1
    ''', (user_id,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        await context.send("🏆 You have answered all available Twenty One Pilots questions! Check your stats with `@stats`.")
        return
    
    q_id, q_text, q_answer, q_options_json = row
    options = json.loads(q_options_json)
    
    user_sessions[user_id] = {
        'question_id': q_id,
        'correct_answer': q_answer
    }

    options_str = "\n".join([f"- {opt}" for opt in options])
    await context.send(f"❓ Question Time! {q_text} \nOptions: \n{options_str} \n\nUse `@answer <your_answer>` to respond!")

@bot.command()
async def answer(context, *, user_answer: str):
    '''
    Checks the user answer.

    First, it checks if the user has an active session, then it will retreive the correct answer from the database. 
    After the correctness of the answer is checked, the session is cleared so they can start a new quiz and the database
    is updated.
    '''

    user_id = context.author.id

    conn = get_db_connection()
    cursor = conn.cursor()

    if user_id not in user_sessions:
        await context.send("Sorry! You don't have an active question yet. Type `@quiz` to start!")
        return
    
    session_data = user_sessions[user_id]
    correct_answer = session_data["correct_answer"]
    question_id = session_data["question_id"]

    if user_answer.strip().lower() == correct_answer.lower():
        cursor.execute('UPDATE users SET correct_count = correct_count + 1, quizzes_taken = quizzes_taken + 1 WHERE user_id = ?', (user_id,))
        await context.send("✅ Correct answer! Congratulations! 🎉")
    else:
        cursor.execute('UPDATE users SET incorrect_count = incorrect_count + 1, quizzes_taken = quizzes_taken + 1 WHERE user_id = ?', (user_id,))
        await context.send(f"❌ Better luck next time... The correct answer was {correct_answer}! 😞")

    cursor.execute('INSERT INTO answered_questions (user_id, question_id) VALUES (?, ?)', (user_id, question_id))
    conn.commit()
    conn.close()

    del user_sessions[user_id]

@bot.command()
async def stats(context):
    """Displays the user statistics."""
    user_id = context.author.id
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT correct_count, incorrect_count, quizzes_taken FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        correct, incorrect, total = row
        win_rate = (correct / total * 100) if total > 0 else 0
        await context.send(f"📊 Stats for {context.author.name}\nTotal Quizzes: {total}\n✅ Correct: {correct}\n❌ Incorrect: {incorrect}\nWin Rate: {win_rate:.1f}%")
    else:
        await context.send("No stats found. Play a quiz first!")

if __name__=="__main__":
    bot.run(DISCORD_TOKEN)