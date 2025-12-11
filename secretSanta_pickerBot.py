import logging
import random # <--- Added this for the shuffle
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# REPLACE WITH YOUR TOKEN
TOKEN = "7821913361:AAEb3wpAAAJUdJG3z3pEO2P7BQz-swU5G0M" 

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# In-memory storage (Replace with your DB logic later)
GAME_DATA = {}

async def start_secret_santa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /start command, works in group."""
    if update.effective_chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("Please start Secret Santa in a group chat!")
        return

    group_id = update.effective_chat.id
    
    # Initialize game data if not exists
    if group_id not in GAME_DATA:
        GAME_DATA[group_id] = {'participants': {}} 

    keyboard = [[InlineKeyboardButton("Join Secret Santa", callback_data='join_game')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🎁 **Time for Secret Santa!**\n\n"
        "1. Click 'Join' below.\n"
        "2. **Start the bot in DM** so I can message you your target!",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def join_game_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the 'join_game' button click."""
    query = update.callback_query
    await query.answer("You are joining the Secret Santa!") 

    user = query.from_user
    group_id = query.message.chat_id
    
    # Ensure data exists
    if group_id not in GAME_DATA:
        GAME_DATA[group_id] = {'participants': {}}

    participants = GAME_DATA[group_id]['participants']
    
    # Add user if not present
    if user.id not in participants:
        participants[user.id] = {
            'username': user.username or user.first_name, 
            'first_name': user.first_name,
            'drawn_to': None 
        }

        # Send DM confirmation
        try:
            await context.bot.send_message(
                chat_id=user.id, 
                text=f"✅ You have joined the Secret Santa for **{query.message.chat.title}**!"
            )
        except Exception:
            # If DM fails, warn in group
            await context.bot.send_message(
                chat_id=group_id, 
                text=f"❗ @{user.username or user.first_name} - I can't DM you! Please click my name and press Start."
            )
            return

    # --- FIX 1: Generate the List of Names ---
    # We create a string list of all names currently in the participants dictionary
    names_list = "\n".join([f"• {p['first_name']}" for p in participants.values()])
    count = len(participants)

    # Determine which buttons to show
    if count >= 2:
        keyboard = [
            [InlineKeyboardButton("Join Secret Santa", callback_data='join_game')],
            [InlineKeyboardButton("🚀 GO! Draw Targets", callback_data='go_draw')]
        ]
    else:
        keyboard = [[InlineKeyboardButton("Join Secret Santa", callback_data='join_game')]]
    
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Update the group message
    try:
        await query.edit_message_text(
            text=f"🎁 **Secret Santa List** 🎁\n\n"
                 f"**Participants ({count}):**\n"
                 f"{names_list}\n\n"
                 f"{'Ready to draw? Click GO!' if count >= 2 else 'Waiting for more people...'}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except Exception:
        pass # Message content was the same, ignore error

async def go_draw_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the Draw Logic (Missing in your original code)."""
    query = update.callback_query
    group_id = query.message.chat_id

    if group_id not in GAME_DATA:
        await query.answer("Game data not found!", show_alert=True)
        return

    participants_dict = GAME_DATA[group_id]['participants']
    user_ids = list(participants_dict.keys())

    if len(user_ids) < 2:
        await query.answer("Need at least 2 people!", show_alert=True)
        return
    
    await query.answer("Drawing names now...")

    # --- FIX 2: The Random Draw Logic ---
    # 1. Shuffle the list of IDs
    random.shuffle(user_ids)
    
    # 2. Shift assignments (Person 1 gets Person 2, etc.)
    # This ensures nobody gets themselves.
    pairs = []
    for i in range(len(user_ids)):
        santa_id = user_ids[i]
        target_id = user_ids[(i + 1) % len(user_ids)] # Wrap around to start
        pairs.append((santa_id, target_id))

    # 3. Send DMs
    success_count = 0
    for santa_id, target_id in pairs:
        target_name = participants_dict[target_id]['first_name']
        try:
            await context.bot.send_message(
                chat_id=santa_id,
                text=f"🤫 **SECRET SANTA RESULT** 🤫\n\n"
                     f"You are the Secret Santa for: **{target_name}**! 🎁"
            )
            success_count += 1
        except Exception as e:
            logging.error(f"Could not DM user {santa_id}: {e}")

    # 4. Final Group Announcement
    await query.message.edit_text(
        f"🎲 **Draw Complete!** 🎲\n\n"
        f"I have sent DMs to {success_count}/{len(user_ids)} participants.\n"
        "Check your private messages!"
    )
    
    # Optional: Clear game data so they can start over
    del GAME_DATA[group_id]

def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler(["start", "secretsanta"], start_secret_santa))
    
    # Handler for Joining
    application.add_handler(CallbackQueryHandler(join_game_callback, pattern='^join_game$'))
    
    # Handler for Drawing (This was missing)
    application.add_handler(CallbackQueryHandler(go_draw_callback, pattern='^go_draw$'))
    
    print("Bot started polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()