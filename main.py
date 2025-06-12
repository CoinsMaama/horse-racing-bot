import asyncio
import logging
import signal
import sys
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Your bot token
BOT_TOKEN = "8144174417:AAHd10YHFrhmbC-X_VhHL6GzIYJ8calc6xc"

# Global variable to hold the application
application = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    await update.message.reply_text('🏇 Welcome to Horse Racing Bot!')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    help_text = """
🏇 Horse Racing Bot Commands:
/start - Start the bot
/help - Show this help message
    """
    await update.message.reply_text(help_text)

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    print(f"\n🏇 Received signal {signum}. Shutting down gracefully...")
    if application:
        # Stop the application
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(shutdown())
            else:
                asyncio.run(shutdown())
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    sys.exit(0)

async def shutdown():
    """Shutdown the application gracefully."""
    global application
    if application:
        logger.info("Stopping application...")
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        logger.info("Application stopped successfully")

def main():
    """Start the bot."""
    global application
    
    try:
        print("🏇 Horse Racing Bot starting...")
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Create the Application
        application = Application.builder().token(BOT_TOKEN).build()

        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))

        print("🏇 Bot is running! Press Ctrl+C to stop.")
        
        # Run the bot with polling
        application.run_polling(
            poll_interval=1.0,
            timeout=10,
            bootstrap_retries=-1,
            read_timeout=10,
            write_timeout=10,
            connect_timeout=10,
            pool_timeout=1,
            stop_signals=None  # We handle signals manually
        )
        
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        return 1
    finally:
        print("🏇 Bot shutdown complete")
        return 0

if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n🏇 Bot stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
