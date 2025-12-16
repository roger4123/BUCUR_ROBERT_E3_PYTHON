import discord, os, json, logging
from datetime import datetime
from discord.ext import commands, tasks
from dotenv import load_dotenv
from database import init_db, get_db_cursor, DB_NAME

load_dotenv(override=True)
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
SESSION_TIMEOUT = 180

bot_intents = discord.Intents.default()
bot_intents.message_content = True
bot = commands.Bot(command_prefix='@', intents=bot_intents)

user_sessions = {}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%d-%m-%Y %H:%M:%S',
    handlers=[
        logging.FileHandler("logs/trivia.log", encoding='utf-8'), #
        logging.StreamHandler()                                   #
    ]
)
logger = logging.getLogger("TriviaBot")


@tasks.loop(seconds=10)
async def check_session_timeouts():
    """
    Automatically cleans up sessions if a user takes too long.
    """
    now = datetime.now()
    expired_users = []

    for user_id, session in user_sessions.items():
        last_activity = session.get("last_activity")
        if last_activity and (now - last_activity).total_seconds() > SESSION_TIMEOUT:
            expired_users.append(user_id)

    for uid in expired_users:
        del user_sessions[uid]
        logger.info(f"Session timed out for user {uid}")


# EVENTS
@bot.event
async def on_ready():
    logger.info(f"Bot logged in as {bot.user.name}.")
    if not DISCORD_TOKEN:
        logger.error("Error: the .env file wasn't read correctly!")

    if init_db():
        logger.info(f"Database {DB_NAME} initialized successfuly.")
    else:
        logger.error("Error: database wasn't initialized correctly!")

    if not check_session_timeouts.is_running():
        check_session_timeouts.start()

@bot.event
async def on_command_error(context, error):
    '''
    Handles unknown commands.
    '''
    logger.error(f"Command error triggered: {error}")

    if isinstance(error, commands.CommandNotFound):
        await context.send("❌ Unknown command! Try `@quiz`, `@answer <your_answer>` or `@stats`.")
        logger.info(f"User {context.author.name} (ID {context.author.id}) entered an unkown command.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await context.send("⚠️ Missing argument! Try: `@answer 21pilots`")
        logger.info(f"User {context.author.name} (ID {context.author.id}) enterd an incomplete command.")
    else:
        logger.error(f"Unknown error: {error}")


# COMMANDS
@bot.command()
async def info(context):
    """
    General info command. 
    Displays usage instructions and available categories.
    """
    with get_db_cursor() as (conn, cursor):
        cursor.execute("SELECT DISTINCT category FROM questions")
        rows = cursor.fetchall()
    
        cats = [r[0] for r in rows]
        cats_str = ", ".join(cats) if cats else "No categories found."

        embed = discord.Embed(title="🤖 TØP Trivia Bot Guide", description="Welcome to the Twenty One Pilots Trivia Bot! Here is how to interact with me:", color=0xd13232)
        
        embed.add_field(name="🎮 Starting a Game", value="`@quiz` - Start a random question\n`@quiz <Category>` - Start a specific category (e.g., `@quiz Lore`)", inline=False)
        embed.add_field(name="📂 Available Categories", value=cats_str, inline=False)
        embed.add_field(name="🗣️ Answering", value="`@answer <your guess>` - Submit an answer\n`@skip` - Give up and get the next question automatically", inline=False)
        embed.add_field(name="📊 Stats & Ranking", value="`@stats` - See your personal score\n`@leaderboard` - See the top 10 players", inline=False)
        
        await context.send(embed=embed)

@bot.command()
async def quiz(context, category: str = None):
    '''
    Starts a quiz session for the user.
    
    First, it checks if the user has an unanswered question, and if not, the quiz starts, by picking a random question and store the answer in the database. 
    In the end, it will display the question to the user.
    '''
    user_id = context.author.id

    if user_id in user_sessions:
        session = user_sessions[user_id]
        logger.info(f"User {context.author.name} (ID {user_id}) has an active question already.")
        await context.send(f"⚠️ **You have an active question!**\n\n**Question:** {session['question_text']}\n\nType `@answer <your_answer>` or `@skip` to move on.")
        return
    
    if category:
        category = category.capitalize()

    try:
        with get_db_cursor() as (conn, cursor):
            cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))

            prepared_query = '''
                SELECT id, question_text, correct_answer, options_json, category
                FROM questions 
                WHERE id NOT IN (SELECT question_id FROM answered_questions WHERE user_id = ?)
            '''
            params = [user_id]

            if category: 
                prepared_query += " AND category = ?"
                params.append(category)
            prepared_query += " ORDER BY RANDOM() LIMIT 1"

            cursor.execute(prepared_query, tuple(params))
            row = cursor.fetchone()

            if not row:
                await context.send("🏆 You have answered all available Twenty One Pilots questions! Check your stats with `@stats`.")
                return
            
            q_id, q_text, q_answer, q_options_json, q_category = row
            options = json.loads(q_options_json)
            
            user_sessions[user_id] = {
                'question_id': q_id,
                'correct_answer': q_answer,
                'question_text' : q_text,
                'category' : q_category,
                'last_activity' : datetime.now()
            }

            options_str = "\n".join([f"- {opt}" for opt in options])
            await context.send(f"❓ Question Time! Are you ready, {context.author.name}?\nCategory: {q_category} \n\n{q_text} \nOptions: \n{options_str} \n\nUse `@answer <your_answer>` to respond!")

            logger.info(f"Sent question {q_id} ({q_category}) to user {context.author.name} (ID {user_id})")
    except Exception as e:
        logger.error(f"Database error: {e}")
        await context.send("An error occured when fetching the question.")


@bot.command()
async def answer(context, *, user_answer: str):
    '''
    Checks the user answer.

    First, it checks if the user has an active session, then it will retreive the correct answer from the database. 
    After the correctness of the answer is checked, the session is cleared so they can start a new quiz and the database
    is updated.
    '''
    user_id = context.author.id

    if user_id not in user_sessions:
        await context.send("Sorry! You don't have an active question yet. Type `@quiz` to start!")
        logger.info(f"User {context.author.name} (ID {user_id}) doesn't have an active question yet.")
        return
    
    user_sessions[user_id]['last_activity'] = datetime.now()
    
    session_data = user_sessions[user_id]
    correct_answer = session_data["correct_answer"]
    question_id = session_data["question_id"]

    with get_db_cursor() as (conn, cursor):
        if user_answer.strip().lower() == correct_answer.lower():
            cursor.execute('UPDATE users SET correct_count = correct_count + 1, quizzes_taken = quizzes_taken + 1 WHERE user_id = ?', (user_id,))
            await context.send(f"✅ Correct answer! Congratulations, {context.author.name}! 🎉")
            logger.info(f"User {context.author.name} (ID {user_id}) scored a point. Question {question_id}")
        else:
            cursor.execute('UPDATE users SET incorrect_count = incorrect_count + 1, quizzes_taken = quizzes_taken + 1 WHERE user_id = ?', (user_id,))
            await context.send(f"❌ Better luck next time, {context.author.name}... The correct answer was {correct_answer}! 😞")
            logger.info(f"User {context.author.name} (ID {user_id}) has answered question {question_id} wrong")

        cursor.execute('INSERT INTO answered_questions (user_id, question_id) VALUES (?, ?)', (user_id, question_id))

    del user_sessions[user_id]
    logger.info(f"Deleting current session for {context.author.name} (ID {user_id})")

@bot.command()
async def stats(context):
    """Displays the user statistics."""
    user_id = context.author.id
    
    with get_db_cursor() as (conn, cursor):
        cursor.execute('SELECT correct_count, incorrect_count, quizzes_taken FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()

        if row:
            correct, incorrect, total = row
            win_rate = (correct / total * 100) if total > 0 else 0
            await context.send(f"📊 Stats for {context.author.name}\nTotal Quizzes: {total}\n✅ Correct: {correct}\n❌ Incorrect: {incorrect}\nWin Rate: {win_rate:.1f}%")
            logger.info(f"Displaying stats for {context.author.name} (ID {user_id})")
        else:
            await context.send("No stats found. Play a quiz first!")
            logger.info(f"User {context.author.name} (ID {user_id}) doesn't have any stats yet.")

@bot.command()
async def skip(context):
    """
    Get the next question.

    When a user has an active question, he has the option to skip it if he doesn't know the answer.
    The next question is automatically presented.
    """
    user_id = context.author.id

    if user_id not in user_sessions:
        await context.send("Nothing to skip! Type `@quiz` to start.")
        logger.info(f"User {context.author.name} (ID {user_id}) tried skipping a question.")
        return

        # do i count it as incorrect or not?
    # session_data = user_sessions[user_id]
    # correct_answer = session_data['correct_answer']
    # question_id = session_data['question_id']

    # cursor.execute('UPDATE users SET incorrect_count = incorrect_count + 1, quizzes_taken = quizzes_taken + 1 WHERE user_id = ?', (user_id,))
    # cursor.execute('INSERT INTO answered_questions (user_id, question_id) VALUES (?, ?)', (user_id, question_id))
    # conn.commit()
    # conn.close()

    del user_sessions[user_id]
    
    await context.send(f"⏭️ Skipped!")
    logger.info(f"User {context.author.name} (ID {user_id}) skipped the current question.")
    
    try:
        with get_db_cursor() as (conn, cursor):
            cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))

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
                logger.info(f"User {context.author.name} (ID {user_id}) has answered all possible questions.")
                return

            q_id, q_text, q_answer, q_options_json, q_category = row
            options = json.loads(q_options_json)

            user_sessions[user_id] = {
                'question_id': q_id,
                'correct_answer': q_answer,
            }

            options_str = "\n".join([f"- {opt}" for opt in options])
            await context.send(f"❓ Question Time! Are you ready, {context.author.name}?\nCategory: {q_category} \n\n{q_text} \nOptions: \n{options_str} \n\nUse `@answer <your_answer>` to respond!")
            logger.info(f"Sent question {q_id} ({q_category}) to user {context.author.name} (ID {user_id})")
    except Exception as e:
        logger.error(f"Database error when skipping question: {e}")

@bot.command()
async def leaderboard(context):
    """Display the top users globally."""
    with get_db_cursor() as (conn, cursor):        
        # top 10 users
        cursor.execute("SELECT user_id, correct_count FROM users ORDER BY correct_count DESC LIMIT 10")
        rows = cursor.fetchall()

        if not rows:
            await context.send("Leaderboard is empty.")
            logger.info("Leaderboard is empty.")
            return
        
        message_lines = ["🏆 Global Leaderboard 🏆"]
        
        for index, (uid, score) in enumerate(rows, 1):
            try:
                user = context.guild.get_member(uid) or await bot.fetch_user(uid)
                name = user.display_name
            except:
                name = "Unknown User"
                
            message_lines.append(f"#{index} {name} — {score} pts")

        await context.send("\n".join(message_lines))
        logger.info("Displaying leaderboard.")
        

if __name__=="__main__":
    if DISCORD_TOKEN:
        bot.run(DISCORD_TOKEN)
    else:
        logger.critical("Discord Token not configured!")