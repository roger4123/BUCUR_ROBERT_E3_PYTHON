import random, discord, os
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv(override=True)

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

test_questions = [
    {"question": "How many members are in the band Twenty One Pilots?", "answer": "2", "options": ["1", "2", "4", "21"]},
    {"question": "How many albums does the band Twenty One Pilots have?", "answer": "6", "options": ["3", "5", "6", "9"]},
    {"question": "What is the name of the lead singer of Twenty One Pilots?", "answer": "Tyler Joseph", "options": ["James Hetfield", "John Malkovich", "Gerard Way", "Tyler Joseph"]},
]

bot_intents = discord.Intents.default()
bot_intents.message_content = True
bot = commands.Bot(command_prefix='@', intents=bot_intents)

user_sessions = {}

@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user.name}")

@bot.command()
async def quiz(context):
    '''
    Starts a quiz session for the user.
    
    First, it checks if the user has an unanswered question, and if not, the quiz starts, by picking a random question and store 
    the answer in memory. In the end, it will display the question to the user.
    '''
    user_id = context.author.id

    if user_id in user_sessions:
        await context.send("You already have an active question which you haven't answered yet! (Tip: use @answer <your_answer>)")
        return
    
    query_data = random.choice(test_questions)

    user_sessions[user_id] = query_data["answer"]

    options_str = "\n".join([f"- {opt}" for opt in query_data["options"]])
    await context.send(f"❓ Question Time! {query_data['question']} \nOptions: \n{options_str} \n\nUse '@answer <your_answer>' to respond!")

@bot.command()
async def answer(context, *, user_answer: str):
    '''
    Checks the user answer.

    First, it checks if the user has an active session, then it will retreive the correct answer from memory. 
    After the correctness of the answer is checked, the session is cleared so they can start a new quiz.
    '''

    user_id = context.author.id

    if user_id not in user_sessions:
        await context.send("Sorry! You don't have an active question yet. Type '@quiz' to start!")
        return
    
    correct_answer = user_sessions[user_id]

    if user_answer.strip().lower() == correct_answer.lower():
        await context.send("✅ Correct answer! Congratulations! 🎉")
    else:
        await context.send(f"❌ Better luck next time... The correct answer was {correct_answer}! 😞")

    del user_sessions[user_id]

if __name__=="__main__":
    bot.run(DISCORD_TOKEN)