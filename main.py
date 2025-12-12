import logging
import random
import database 
from telegram.ext import ContextTypes
from telegram import Update
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler, 
    ContextTypes,
    ConversationHandler,
    MessageHandler,     
    filters             
)
import datetime
import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

TOKEN = os.getenv('TELEGRAM_TOKEN') or os.getenv('TOKEN')
if not TOKEN:
    raise SystemExit('Error: TELEGRAM_TOKEN environment variable not set.')

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

SETTING_DATE = 1

async def start_secret_santa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /start command."""
    if update.effective_chat.type not in ["group", "supergroup"]:
        await update.message.reply_text(
            "Use this bot in a group chat, please and thank you. \n\n\n Btw @whiteowlyy built me✨"
            )
        return

    group_id = update.effective_chat.id
    
    database.ensure_game_exists(group_id) 

    keyboard = [[InlineKeyboardButton("Join Secret Santa", callback_data='join_game')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Who's joining the Secret Santa? \n\n"
        "Join the gang, but slide into my DMs first!\n",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def join_game_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the Join button."""
    query = update.callback_query
    
    user = query.from_user
    group_id = query.message.chat_id
    username = user.username or user.first_name
    added = database.add_participant(user.id, group_id, username) 

    if added:
        await query.answer("You are joining the gang!")
        
        try:
            await context.bot.send_message(
                chat_id=user.id, 
                text=f"You have successfully joined the gang for {query.message.chat.title}✨",
                reply_markup=reply_markup
            )
        except Exception:
            await context.bot.send_message(
                chat_id=group_id, 
                text=f"❗ @{username} DM me:)"
            )
    else:
        await query.answer("You are already in the list!", show_alert=False)

    
    participants = database.get_participants_data(group_id) 
    count = len(participants)
    
    
    names_list = "\n".join([f"• {p[1]}" for p in participants])

   
    if count >= 2:
        keyboard = [
            [InlineKeyboardButton("Join!", callback_data='join_game')],
            [InlineKeyboardButton("Draw", callback_data='go_draw')]
        ]
    else:
        keyboard = [[InlineKeyboardButton("Join!", callback_data='join_game')]]
    
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await query.edit_message_text(
            text=f"Gang Members\n\n"
                 f"Total: {count}**\n"
                 f"@{names_list}\n\n"
                 f"{'Is everyone in? Hit Draw!' if count >= 2 else 'are you planning to give a gift for yourself? wait for more people to join...'}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except Exception:
        pass 

async def go_draw_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the Draw logic using the Database."""
    query = update.callback_query
    group_id = query.message.chat_id

    
    participants = database.get_participants_data(group_id)

    if len(participants) < 2:
        await query.answer("Need at least 2 people!", show_alert=True)
        return
    
    await query.answer("Drawing names now...")


    user_ids = [p[0] for p in participants]
    id_to_name = {p[0]: p[1] for p in participants}


    random.shuffle(user_ids)
    
 
    pairs = [] 
    for i in range(len(user_ids)):
        santa_id = user_ids[i]
        target_id = user_ids[(i + 1) % len(user_ids)]
        pairs.append((santa_id, target_id))

   
    database.update_assignments_and_status(group_id, pairs)
    exchange_date = database.get_exchange_date(group_id)
    date_info = f"\nExchange Day: {exchange_date}" if exchange_date else ""

    success_count = 0
    for santa_id, target_id in pairs:
        target_name = id_to_name[target_id]
        try:
            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Refresh Summary", callback_data='summary_btn')]])
            await context.bot.send_message(
                chat_id=santa_id,
                text=f"You are @{target_name} 's secret santa! \n\n"
                     f"Make sure you get them something good! \n"
                     f"{date_info}",
                     parse_mode='Markdown',
                
            )
            success_count += 1
        except Exception as e:
            logging.error(f"Failed to DM {santa_id}: {e}")

    await query.message.edit_text(
        f"Draw Complete!\n\n"
        f"Participants: {len(user_ids)}\n"
        f"DMs Sent: {success_count}\n\n"
        "Check your DMs to see who you got!"
    )

async def set_date_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the conversation by asking for the gift exchange date."""
    if update.effective_chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("This command must be used in a group chat.")
        return ConversationHandler.END

    await update.message.reply_text(
        "When is the gifting day?\n"
        "Please reply with the date (e.g., 'Dec 24th' or 'January 5th').\n\n"
        "To cancel, use /cancel.",
        parse_mode='Markdown'
    )
    return SETTING_DATE
    
async def set_date_finish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives the date and saves it to the database."""
    group_id = update.effective_chat.id
    exchange_date = update.message.text
    
    database.update_exchange_date(group_id, exchange_date)
    
    await update.message.reply_text(
        f"It's a date!: on {exchange_date}\n\n",
        parse_mode='Markdown'
    )
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels the current conversation."""
    await update.message.reply_text('Date setting cancelled.')
    return ConversationHandler.END

async def days_left(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /daysleft command, calculating days remaining until exchange."""
    group_id = update.effective_chat.id
    
    date_str = database.get_exchange_date(group_id)
    
    if not date_str:
        await update.message.reply_text(
            "⚠️ The gift exchange date has not been set yet! "
            "Please use the `/setdate` command first."
        )
        return

    try:
        
        today = datetime.date.today()
        current_year = today.year

        
        cleaned_date_str = date_str.lower().replace('st', '').replace('nd', '').replace('rd', '').replace('th', '')

        
        exchange_date = datetime.datetime.strptime(f"{cleaned_date_str} {current_year}", "%b %d %Y").date()
        
        
        if exchange_date < today:
            next_year = current_year + 1
            exchange_date = datetime.datetime.strptime(f"{cleaned_date_str} {next_year}", "%b %d %Y").date()

        time_until = exchange_date - today
        days_remaining = time_until.days
        if days_remaining < 0:
            await update.message.reply_text(
                f"How were the gifts?"
            )
        elif days_remaining == 0:
            await update.message.reply_text(
                f"IT'S TODAY!\n\n"
                f"Let's see those gifts!"
            )
        else:
            await update.message.reply_text(
                f"Time Remaining Until Gifting day! ⏳\n\n"
                f"That means you have exactly {days_remaining} days left to shop! Happy gifting!"
            )

    except ValueError:
        await update.message.reply_text(
            f"Error Calculating Date!\n\n"
            f"I couldn't understand the date format: **{date_str}**.\n"
            " Ask the admin to use `/setdate` with a clear format (e.g., 'Dec 24th')."
        )



def main():
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
    application.add_handler(CommandHandler(["daysleft", "reminddays"], days_left))
   
    
    print("Bot started polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()