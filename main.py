import asyncio
import random
import json
import os
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
import logging

# You'll need to install: pip install python-telegram-bot
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Game Data Classes
@dataclass
class Horse:
    name: str
    speed: int  # 1-100
    stamina: int  # 1-100
    acceleration: int  # 1-100
    surface_pref: str  # dirt, turf, synthetic
    distance_pref: str  # sprint, mile, distance
    form: int  # 1-10 current condition
    age: int
    wins: int = 0
    races: int = 0
    value: int = 1000
    owner_id: Optional[int] = None
    trainer_id: Optional[int] = None

@dataclass
class Track:
    name: str
    surface: str
    distance: int  # furlongs
    condition: str  # fast, good, soft, heavy
    owner_id: Optional[int] = None
    level: int = 1
    reputation: int = 0

@dataclass
class Player:
    user_id: int
    username: str
    role: str  # owner, trainer, jockey, track_owner
    level: int = 1
    experience: int = 0
    money: int = 10000
    reputation: int = 0
    horses: List[str] = None  # horse names
    contracts: List[int] = None  # user_ids for contracts
    
    def __post_init__(self):
        if self.horses is None:
            self.horses = []
        if self.contracts is None:
            self.contracts = []

# Game State Management
class GameState:
    def __init__(self):
        self.players: Dict[int, Player] = {}
        self.horses: Dict[str, Horse] = {}
        self.tracks: Dict[str, Track] = {}
        self.races: List[Dict] = []
        self.daily_races_run = False
        self.last_race_day = datetime.now().date()
        
        # Initialize some default tracks
        self.init_default_tracks()
        self.init_sample_horses()
    
    def init_default_tracks(self):
        default_tracks = [
            Track("Meadowbrook Park", "dirt", 8, "fast"),
            Track("Green Valley", "turf", 10, "good"),
            Track("Sunset Downs", "dirt", 6, "fast"),
            Track("Royal Ascot", "turf", 12, "good")
        ]
        for track in default_tracks:
            self.tracks[track.name] = track
    
    def init_sample_horses(self):
        horse_names = ["Thunder Bolt", "Swift Arrow", "Golden Dream", "Storm Chaser", 
                      "Midnight Express", "Fire Spirit", "Ocean Breeze", "Diamond Star"]
        
        for name in horse_names:
            horse = Horse(
                name=name,
                speed=random.randint(60, 90),
                stamina=random.randint(60, 90),
                acceleration=random.randint(60, 90),
                surface_pref=random.choice(["dirt", "turf", "synthetic"]),
                distance_pref=random.choice(["sprint", "mile", "distance"]),
                form=random.randint(6, 9),
                age=random.randint(3, 8),
                value=random.randint(5000, 50000)
            )
            self.horses[name] = horse

# Global game state
game = GameState()

# Race Simulation Engine
class RaceSimulator:
    @staticmethod
    def simulate_race(horses: List[Horse], track: Track, jockeys: Dict[str, Player]) -> Dict:
        results = []
        
        for horse in horses:
            # Base performance calculation
            performance = horse.speed * 0.4 + horse.stamina * 0.3 + horse.acceleration * 0.2 + horse.form * 0.1
            
            # Track preference bonuses
            if horse.surface_pref == track.surface:
                performance += 5
            
            # Distance preference
            if (track.distance <= 7 and horse.distance_pref == "sprint") or \
               (7 < track.distance <= 10 and horse.distance_pref == "mile") or \
               (track.distance > 10 and horse.distance_pref == "distance"):
                performance += 3
            
            # Jockey skill bonus
            jockey = jockeys.get(horse.name)
            if jockey:
                jockey_skill = jockey.level * 2 + jockey.reputation * 0.1
                performance += jockey_skill
            
            # Random factor (racing luck)
            performance += random.uniform(-10, 10)
            
            results.append({
                'horse': horse.name,
                'performance': performance,
                'jockey': jockey.username if jockey else "No Jockey"
            })
        
        # Sort by performance (highest wins)
        results.sort(key=lambda x: x['performance'], reverse=True)
        
        return {
            'results': results,
            'track': track.name,
            'distance': track.distance,
            'surface': track.surface,
            'winner': results[0]['horse'],
            'place': results[1]['horse'] if len(results) > 1 else None,
            'show': results[2]['horse'] if len(results) > 2 else None
        }

# Bot Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🤵 Owner", callback_data="role_owner")],
        [InlineKeyboardButton("🏇 Jockey", callback_data="role_jockey")],
        [InlineKeyboardButton("👨‍🏫 Trainer", callback_data="role_trainer")],
        [InlineKeyboardButton("🏟️ Track Owner", callback_data="role_track_owner")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🏇 Welcome to Horse Racing Empire! 🏇\n\n"
        "Choose your role to begin your racing career:",
        reply_markup=reply_markup
    )

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in game.players:
        await update.message.reply_text("❌ You haven't joined the game yet! Use /start to begin.")
        return
    
    player = game.players[user_id]
    
    profile_text = f"""
👤 **{player.username}** - {player.role.title()}
💰 Money: ${player.money:,}
🏆 Level: {player.level}
⭐ Experience: {player.experience}
📈 Reputation: {player.reputation}
    """
    
    if player.role == "owner" and player.horses:
        profile_text += f"\n🐎 Horses: {len(player.horses)}"
    elif player.role == "trainer":
        profile_text += f"\n🐎 Horses Training: {len(player.horses)}"
    elif player.role == "track_owner":
        owned_tracks = [name for name, track in game.tracks.items() if track.owner_id == user_id]
        profile_text += f"\n🏟️ Tracks Owned: {len(owned_tracks)}"
    
    await update.message.reply_text(profile_text, parse_mode='Markdown')

async def horses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in game.players:
        await update.message.reply_text("❌ You haven't joined the game yet!")
        return
    
    player = game.players[user_id]
    
    if not player.horses:
        await update.message.reply_text("🐎 You don't own any horses yet!")
        return
    
    horses_text = "🐎 **Your Horses:**\n\n"
    for horse_name in player.horses:
        if horse_name in game.horses:
            horse = game.horses[horse_name]
            horses_text += f"**{horse.name}**\n"
            horses_text += f"⚡ Speed: {horse.speed} | 💪 Stamina: {horse.stamina}\n"
            horses_text += f"🏁 Record: {horse.wins}/{horse.races}\n"
            horses_text += f"💵 Value: ${horse.value:,}\n\n"
    
    await update.message.reply_text(horses_text, parse_mode='Markdown')

async def market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    available_horses = [horse for horse in game.horses.values() if horse.owner_id is None]
    
    if not available_horses:
        await update.message.reply_text("🏪 No horses available in the market right now!")
        return
    
    market_text = "🏪 **Horse Market:**\n\n"
    
    for horse in available_horses[:5]:  # Show first 5
        market_text += f"**{horse.name}** - ${horse.value:,}\n"
        market_text += f"⚡{horse.speed} 💪{horse.stamina} 🚀{horse.acceleration}\n"
        market_text += f"Prefers: {horse.surface_pref} | {horse.distance_pref}\n\n"
    
    keyboard = [[InlineKeyboardButton("💰 Buy Horse", callback_data="buy_horse_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(market_text, reply_markup=reply_markup, parse_mode='Markdown')

async def tracks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tracks_text = "🏟️ **Available Tracks:**\n\n"
    
    for track_name, track in game.tracks.items():
        owner_name = "Available"
        if track.owner_id and track.owner_id in game.players:
            owner_name = game.players[track.owner_id].username
        
        tracks_text += f"**{track.name}**\n"
        tracks_text += f"Surface: {track.surface.title()} | Distance: {track.distance}f\n"
        tracks_text += f"Condition: {track.condition.title()}\n"
        tracks_text += f"Owner: {owner_name}\n\n"
    
    await update.message.reply_text(tracks_text, parse_mode='Markdown')

async def race(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Simple daily race simulation
    if game.daily_races_run and game.last_race_day == datetime.now().date():
        await update.message.reply_text("🏁 Today's races have already been run! Check back tomorrow.")
        return
    
    # Run a sample race
    available_horses = [horse for horse in game.horses.values() if horse.form > 5]
    if len(available_horses) < 4:
        await update.message.reply_text("❌ Not enough horses in good form to run a race!")
        return
    
    race_horses = random.sample(available_horses, min(8, len(available_horses)))
    track = random.choice(list(game.tracks.values()))
    
    # Assign jockeys
    jockeys = {}
    jockey_players = [p for p in game.players.values() if p.role == "jockey"]
    for i, horse in enumerate(race_horses):
        if i < len(jockey_players):
            jockeys[horse.name] = jockey_players[i]
    
    # Simulate race
    race_result = RaceSimulator.simulate_race(race_horses, track, jockeys)
    
    # Update statistics
    for i, result in enumerate(race_result['results']):
        horse_name = result['horse']
        if horse_name in game.horses:
            horse = game.horses[horse_name]
            horse.races += 1
            if i == 0:  # Winner
                horse.wins += 1
                if horse.owner_id and horse.owner_id in game.players:
                    game.players[horse.owner_id].money += 5000
                    game.players[horse.owner_id].experience += 10
    
    # Format results
    result_text = f"🏁 **Race Results at {track.name}**\n\n"
    result_text += f"🏟️ {track.distance}f on {track.surface}\n\n"
    
    for i, result in enumerate(race_result['results'][:3]):
        position = ["🥇", "🥈", "🥉"][i]
        result_text += f"{position} {result['horse']} (Jockey: {result['jockey']})\n"
    
    game.daily_races_run = True
    game.last_race_day = datetime.now().date()
    
    await update.message.reply_text(result_text, parse_mode='Markdown')

# Callback Handlers
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    username = query.from_user.username or query.from_user.first_name
    
    if query.data.startswith("role_"):
        role = query.data.replace("role_", "")
        
        # Create new player
        new_player = Player(
            user_id=user_id,
            username=username,
            role=role
        )
        
        # Role-specific starting bonuses
        if role == "owner":
            new_player.money = 25000
            # Give starter horse
            available_horses = [name for name, horse in game.horses.items() if horse.owner_id is None]
            if available_horses:
                starter_horse = random.choice(available_horses)
                game.horses[starter_horse].owner_id = user_id
                new_player.horses.append(starter_horse)
        
        elif role == "track_owner":
            new_player.money = 50000
            # Assign a track
            available_tracks = [name for name, track in game.tracks.items() if track.owner_id is None]
            if available_tracks:
                track_name = random.choice(available_tracks)
                game.tracks[track_name].owner_id = user_id
        
        game.players[user_id] = new_player
        
        await query.edit_message_text(
            f"🎉 Welcome to the racing world as a {role.title()}!\n\n"
            f"💰 Starting money: ${new_player.money:,}\n"
            f"Use /profile to see your status\n"
            f"Use /help to see available commands"
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🏇 **Horse Racing Empire Commands:**

**General:**
/start - Join the game and choose your role
/profile - View your player profile
/help - Show this help message

**Horses & Racing:**
/horses - View your horses (Owners/Trainers)
/market - Browse horses for sale
/race - Run today's race simulation
/tracks - View available racing tracks

**Coming Soon:**
- Training system for trainers
- Jockey booking system
- Track management for track owners
- Breeding system
- Betting system
- Championships and tournaments

Choose your role and start building your racing empire! 🏆
    """
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

# Error handler
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    logging.error(msg="Exception while handling an update:", exc_info=context.error)

# Main Bot Setup
async def main():
    # Get bot token from environment variable
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN environment variable is required")
    
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Command handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("profile", profile))
        application.add_handler(CommandHandler("horses", horses))
        application.add_handler(CommandHandler("market", market))
        application.add_handler(CommandHandler("tracks", tracks))
        application.add_handler(CommandHandler("race", race))
        application.add_handler(CommandHandler("help", help_command))
        
        # Callback handlers
        application.add_handler(CallbackQueryHandler(button_callback))
        
        # Error handler
        application.add_error_handler(error_handler)
        
        # Initialize and start
        await application.initialize()
        await application.start()
        
        # Start the bot
        print("🏇 Horse Racing Bot starting...")
        await application.run_polling(stop_signals=None)
        
    except Exception as e:
        logging.error(f"Error starting bot: {e}")
        raise
    finally:
        # Cleanup
        if 'application' in locals():
            await application.stop()
            await application.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError as e:
        if "This event loop is already running" in str(e):
            # Fallback for environments with existing event loops
            import nest_asyncio
            nest_asyncio.apply()
            asyncio.run(main())
        else:
            raise
    except KeyboardInterrupt:
        print("Bot stopped by user")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        raise
