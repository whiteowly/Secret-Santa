import logging
import random
import database # <--- CORRECT
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler, 
    ContextTypes,
    ConversationHandler,
    MessageHandler,     
    filters             
)

# REPLACE WITH YOUR TOKEN
TOKEN = "7821913361:AAEb3wpAAAJUdJG3z3pEO2P7BQz-swU5G0M"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

SETTING_DATE = 1

async def start_secret_santa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /start command."""
    if update.effective_chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("Please start Secret Santa in a group chat!")
        return

    group_id = update.effective_chat.id
    
    # [DB] Initialize game in database
    database.ensure_game_exists(group_id) # <--- CORRECTED

    keyboard = [[InlineKeyboardButton("Join Secret Santa", callback_data='join_game')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🎄 **Secret Santa Started!** 🎄\n\n"
        "1. Click 'Join' below to enter.\n"
        "2. **Start me in DM** so I can tell you who your target is!",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def join_game_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the Join button."""
    query = update.callback_query
    
    user = query.from_user
    group_id = query.message.chat_id
    username = user.username or user.first_name

    # [DB] Add participant to database
    added = database.add_participant(user.id, group_id, username) # <--- CORRECTED

    if added:
        await query.answer("You are joining the Secret Santa!")
        # Send DM confirmation
        try:
            await context.bot.send_message(
                chat_id=user.id, 
                text=f"✅ You have successfully joined the Secret Santa for **{query.message.chat.title}**!"
            )
        except Exception:
            await context.bot.send_message(
                chat_id=group_id, 
                text=f"❗ @{username} - I can't DM you! Please click my name and press Start."
            )
    else:
        await query.answer("You are already in the list!", show_alert=False)

    # [DB] Get current list of participants to update the message
    participants = database.get_participants_data(group_id) # <--- CORRECTED
    count = len(participants)
    
    # Create the text list of names
    names_list = "\n".join([f"• {p[1]}" for p in participants])

    # Logic for buttons (Show GO button if 2+ people)
    if count >= 2:
        keyboard = [
            [InlineKeyboardButton("Join Secret Santa", callback_data='join_game')],
            [InlineKeyboardButton("🚀 GO! Draw Targets", callback_data='go_draw')]
        ]
    else:
        keyboard = [[InlineKeyboardButton("Join Secret Santa", callback_data='join_game')]]
    
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await query.edit_message_text(
            text=f"🎁 **Secret Santa Participants** 🎁\n\n"
                 f"**Count: {count}**\n"
                 f"{names_list}\n\n"
                 f"{'Ready to draw? Click GO!' if count >= 2 else 'Waiting for more people...'}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except Exception:
        pass 

async def go_draw_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the Draw logic using the Database."""
    query = update.callback_query
    group_id = query.message.chat_id

    # [DB] Fetch all participants
    participants = database.get_participants_data(group_id)

    if len(participants) < 2:
        await query.answer("Need at least 2 people!", show_alert=True)
        return
    
    await query.answer("Drawing names now...")

    # Extract IDs for shuffling
    user_ids = [p[0] for p in participants]
    id_to_name = {p[0]: p[1] for p in participants}

    # 1. Shuffle
    random.shuffle(user_ids)
    
    # 2. Create Pairs (Circular)
    pairs = [] 
    for i in range(len(user_ids)):
        santa_id = user_ids[i]
        target_id = user_ids[(i + 1) % len(user_ids)]
        pairs.append((santa_id, target_id))

    # 3. [DB] Save assignments to Database
    database.update_assignments_and_status(group_id, pairs)
    exchange_date = database.get_exchange_date(group_id)
    date_info = f"\n🗓️ **Exchange Day:** {exchange_date}" if exchange_date else ""

    # 4. Send DMs
    success_count = 0
    for santa_id, target_id in pairs:
        target_name = id_to_name[target_id]
        try:
            await context.bot.send_message(
                chat_id=santa_id,
                text=f"🤫 **SECRET SANTA MISSION** 🤫\n\n"
                     f"You have been assigned to get a gift for: \n"
                     f"🎁 **{target_name}** 🎁"
                     f"{date_info}",
                     parse_mode='Markdown'
            )
            success_count += 1
        except Exception as e:
            logging.error(f"Failed to DM {santa_id}: {e}")

    # 5. Final Announcement
    await query.message.edit_text(
        f"🎲 **Draw Complete!** 🎲\n\n"
        f"Participants: {len(user_ids)}\n"
        f"DMs Sent: {success_count}\n\n"
        "Check your private messages to see who you got!"
    )

async def set_date_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the conversation by asking for the gift exchange date."""
    if update.effective_chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("This command must be used in the group chat.")
        return ConversationHandler.END

    await update.message.reply_text(
        "📅 **What is the gift exchange day?**\n"
        "Please reply with the date (e.g., 'Dec 24th' or 'January 5th').\n\n"
        "To cancel, use /cancel.",
        parse_mode='Markdown'
    )
    return SETTING_DATE
    
async def set_date_finish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives the date and saves it to the database."""
    group_id = update.effective_chat.id
    exchange_date = update.message.text
    
    # [DB] Save the date
    database.update_exchange_date(group_id, exchange_date)
    
    await update.message.reply_text(
        f"✅ Gift exchange day saved: **{exchange_date}**\n\n"
        f"This date will now be included in the private assignment messages.",
        parse_mode='Markdown'
    )
    
    # End the conversation
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels the current conversation."""
    await update.message.reply_text('❌ Date setting cancelled.')
    return ConversationHandler.END

def main():
    # [DB] Initialize the DB tables on startup
    database.init_db()

    application = Application.builder().token(TOKEN).build()

    date_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('setdate', set_date_start)],
        states={
            SETTING_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, set_date_finish) 
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(date_conv_handler)
    application.add_handler(CommandHandler(["start", "secretsanta"], start_secret_santa))
    application.add_handler(CallbackQueryHandler(join_game_callback, pattern='^join_game$'))
    application.add_handler(CallbackQueryHandler(go_draw_callback, pattern='^go_draw$'))
    
    print("Bot started polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()