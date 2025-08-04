
# Import and run the Discord bot
import os
import sys

# Add current directory to path to import DETERMINATION module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import and run the bot
try:
    from DETERMINATION import bot, DISCORD_BOT_TOKEN
    if __name__ == "__main__":
        print("Starting DETERMINATION Discord Bot...")
        bot.run(DISCORD_BOT_TOKEN)
except Exception as e:
    print(f"Error starting bot: {e}")
    print("Make sure your environment variables are set correctly in DETERMINATION.ENV")
