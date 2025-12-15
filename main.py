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
            "Use this bot in a group chat, please and thank you. \n\n\nBuilt by @whiteowl_y✨"
            )
        return

    group_id = update.effective_chat.id
    
    database.ensure_game_exists(group_id) 

    keyboard = [[InlineKeyboardButton("Join Secret Santa", callback_data='join_game')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Secret Santa\n\n"
        "Join down below!\n",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /help command."""
    await update.message.reply_text(
        "Hey! Here are the commands you can use:\n\n"
        "/start - Start the Secret Santa bot\n"
        "/join - Join the Secret Santa\n"
        "/draw - Draw names for Secret Santa\n"
        "/setdate - Set the gift exchange date\n"
        "/daysleft - Show how many days are left until the gift exchange\n"
        "/summary - Get a summary of your secret santa game\n"
        "/help - Show this help message\n"
        "/cancel - Cancel the current operation and start afresh\n"
        "/participants - Show the list of participants\n",
    )    

async def join_game_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the Join button."""
    query = update.callback_query
    
    user = query.from_user
    group_id = query.message.chat_id
    # Use username if available, otherwise fallback to first_name for group alert
    username = user.username or user.first_name
    firstname = user.first_name 
    added = database.add_participant(user.id, group_id, username) 

    
    participants = database.get_participants_data(group_id) 
    count = len(participants)
    
    # --- Start: Logic for updating the group message keyboard and content ---
    names_list = "\n".join([f"• @{p[1]}" for p in participants])
    if count >= 2:
        keyboard = [
            [InlineKeyboardButton("Join!", callback_data='join_game')],
            [InlineKeyboardButton("Draw", callback_data='go_draw')]
        ]
        group_status_text = 'Is everyone in? Hit Draw!'
    else:
        keyboard = [[InlineKeyboardButton("Join!", callback_data='join_game')]]
        group_status_text = 'Waiting for more people to join...'
        
    reply_markup_group = InlineKeyboardMarkup(keyboard) 
    # --- End: Logic for updating the group message keyboard and content ---

    if added:
        await query.answer("Joining the Secret Santa list...")

        # New text for the DM confirmation
        dm_text = (
            f"You successfully joined the Secret Santa for {query.message.chat.title}!\n\n"
            f"Wait for the Draw to start. "
           
        )

        try:
            # 1. Attempt to send DM to user
            await context.bot.send_message(
                chat_id=user.id, 
                text=dm_text,
                    
            )
        except Exception:
            # 2. If DM fails, send a clearer warning to the group
            try:
                await context.bot.send_message(
                    chat_id=group_id, 
                    text=f"@{username} I couldn't DM you! Please start a private chat with me first "
                         f"(by searching for me or clicking my name).",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logging.debug(f"Failed to warn group about DM failure: {e}")

        # Announce join to the group
        try:
            mention = f"@{user.username}" if user.username else user.first_name
            await context.bot.send_message(
                chat_id=group_id,
                text=f"{mention} has joined the Secret Santa!",
                parse_mode='Markdown'
            )
        except Exception as e:
            logging.debug(f"Could not send join announcement: {e}")

        # Update the inline group message and also post a fresh summary message
        try:
            await query.edit_message_text(
                 text=f"Secret Santa Members\n\n"
                     f"Total: {count}\n"
                     f"{names_list}\n\n"
                     f"{group_status_text}",
                reply_markup=reply_markup_group, 
                parse_mode='Markdown'
            )

            try:
                await context.bot.send_message(
                    chat_id=group_id,
                    text=f"Secret Santa Members\n\n"
                        f"Total: {count}\n"
                         f"{names_list}\n\n"
                         f"{group_status_text}",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logging.debug(f"Could not send group update message: {e}")
        except Exception as e:
            logging.debug(f"Could not edit original inline message: {e}")
    else:
        await query.answer("You are already in the list!", show_alert=False)


async def join_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /join command so users can join without using the inline button."""
    if update.effective_chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("This command must be used in a group chat.")
        return

    user = update.message.from_user
    group_id = update.effective_chat.id
    username = user.username or user.first_name
    firstname = user.first_name

    added = database.add_participant(user.id, group_id, username)

    participants = database.get_participants_data(group_id)
    count = len(participants)

    names_list = "\n".join([f"• @{p[1]}" for p in participants])

    if added:
        # Try to DM confirmation
        dm_text = (
            f"You've successfully joined the Secret Santa for {update.effective_chat.title}!\n\n"
            f"Wait for the Draw to start."
        )

        try:
            await context.bot.send_message(chat_id=user.id, text=dm_text)
        except Exception:
            try:
                await context.bot.send_message(
                    chat_id=group_id,
                    text=(f" @{username} I couldn't DM you! Please start a private chat with me first ")
                )
            except Exception as e:
                logging.debug(f"Failed to warn group about DM failure: {e}")

        # Announce to group
        try:
            mention = f"@{user.username}" if user.username else user.first_name
            await context.bot.send_message(chat_id=group_id, text=f"{mention} has joined the Secret Santa!")
        except Exception as e:
            logging.debug(f"Could not send join announcement: {e}")

        # Post a fresh summary message in the group
        try:
            if count >= 2:
                keyboard = [
                    [InlineKeyboardButton("Join!", callback_data='join_game')],
                    [InlineKeyboardButton("Draw", callback_data='go_draw')]
                ]
                group_status_text = 'Is everyone in? Hit Draw!'
            else:
                keyboard = [[InlineKeyboardButton("Join!", callback_data='join_game')]]
                group_status_text = 'Waiting for more people to join...'

            reply_markup_group = InlineKeyboardMarkup(keyboard)

            await context.bot.send_message(
                chat_id=group_id,
                text=(f"Secret Santa Members\n\nTotal: {count}\n"
                      f"{names_list}\n\n{group_status_text}"),
                reply_markup=reply_markup_group
            )
        except Exception as e:
            logging.debug(f"Could not send group update message: {e}")
    else:
        await update.message.reply_text("You are already in the list!")



async def draw_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /draw command to perform the Secret Santa draw (group command)."""
    if update.effective_chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("This command must be used in a group chat.")
        return

    group_id = update.effective_chat.id

    # Only allow group admins/creator to run the draw
    try:
        user = update.effective_user or update.message.from_user
        member = await context.bot.get_chat_member(group_id, user.id)
        if member.status not in ("administrator", "creator"):
            await update.message.reply_text("Only group admins can start the draw.")
            return
    except Exception:
        # If we cannot determine admin status, be conservative and deny
        await update.message.reply_text("Could not verify admin status. Only group admins can start the draw.")
        return

    # Ensure a game row exists and check status to avoid double-draws
    database.ensure_game_exists(group_id)
    status = database.get_game_status(group_id)
    if status == 'COMPLETED':
        await update.message.reply_text("Draw already completed for this group.")
        return
    if status == 'DRAWING':
        await update.message.reply_text("A draw is already in progress. Please wait.")
        return

    participants = database.get_participants_data(group_id)

    if len(participants) < 2:
        await update.message.reply_text("Need at least 2 people!")
        return

    await update.message.reply_text("Drawing names now...")

    # Attempt an atomic status transition to DRAWING; if it fails, another draw is in progress or completed.
    try:
        set_ok = database.try_set_status_to_drawing(group_id)
        if not set_ok:
            current = database.get_game_status(group_id)
            if current is None or (isinstance(current, str) and current.strip() == ''):
                try:
                    database.update_game_status(group_id, 'DRAWING')
                except Exception:
                    logging.debug("Fallback: failed to set DRAWING directly")
            else:
                await update.message.reply_text(f"Cannot start draw. Current status: {current}")
                return
    except Exception:
        logging.debug("Failed to atomically set game status to DRAWING; falling back to non-atomic update")
        try:
            database.update_game_status(group_id, 'DRAWING')
        except Exception:
            logging.debug("Failed to set game status to DRAWING; continuing anyway")

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

    failed_dms = []
    success_count = 0
    for santa_id, target_id in pairs:
        target_name = id_to_name[target_id]
        try:
            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Refresh Summary", callback_data='summary_btn')]])
            await context.bot.send_message(
                chat_id=santa_id,
                text=f"You are @{target_name}'s secret santa!\n\n"
                     f"Make sure you get them something good!\n"
                     f"{date_info}"
            )
            success_count += 1
        except Exception as e:
            logging.error(f"Failed to DM {santa_id}: {e}")
            failed_user_info = next((p for p in participants if p[0] == santa_id), None)
            if failed_user_info:
                failed_dms.append(failed_user_info[1])

    failed_info = ""
    if failed_dms:
        unique_failed_dms = sorted(list(set(failed_dms)))
        failed_list = "\n".join([f"• @{name}" for name in unique_failed_dms])
        failed_info = (
            f"\n\nDM Failures!\n"
            f"The following users need to start a private chat with me:\n"
            f"{failed_list}"
        )

    await update.message.reply_text(
        f"Draw Complete!\n\n"
        f"Participants: {len(user_ids)}\n"
        f"DMs Sent: {success_count}\n"
        f"{failed_info}\n"
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


async def setdate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point for /setdate. If arguments are provided, save directly; otherwise start the conversation."""
    if update.effective_chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("This command must be used in a group chat.")
        return ConversationHandler.END

    # If user provided the date inline: /setdate Dec 24
    if context.args:
        exchange_date = " ".join(context.args)
        group_id = update.effective_chat.id
        database.ensure_game_exists(group_id)
        database.update_exchange_date(group_id, exchange_date)
        await update.message.reply_text(f"Saved exchange date: {exchange_date}")
        return ConversationHandler.END

    # Otherwise start the interactive flow
    return await set_date_start(update, context)
    
async def set_date_finish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives the date and saves it to the database."""
    group_id = update.effective_chat.id
    exchange_date = update.message.text
    # Ensure the game row exists so the date is saved
    database.ensure_game_exists(group_id)
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
                f"You have exactly {days_remaining} days left to shop! Happy gifting!"
            )

    except ValueError:
        await update.message.reply_text(
            f"Error Calculating Date!\n\n"
            f"I couldn't understand the date format: {date_str}.\n"
            " Ask the admin to use `/setdate` with a clear format (e.g., 'Dec 24th')."
        )


async def participants(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /participants command, listing every participant in the group."""
    if update.effective_chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("This command must be used in a group chat.")
        return

    group_id = update.effective_chat.id
    participants = database.get_participants_data(group_id)

    if not participants:
        await update.message.reply_text(
            "Secret Santa Members\n\nParticipants: none\n\n"
        )
        return

    names_list = "\n".join([f"• @{p[1]}" for p in participants])
    await update.message.reply_text(
        f"Secret Santa Members\n\nTotal: {len(participants)}\n{names_list}"
    )


async def chatid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Debug: replies with the current chat id (use in group to get group id)."""
    chat = update.effective_chat
    await update.message.reply_text(f"Chat ID: {chat.id} (type: {chat.type})")


async def showdate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Debug: shows stored exchange date and game status for the current group/chat."""
    group_id = update.effective_chat.id
    # Ensure DB row exists
    database.ensure_game_exists(group_id)
    status = database.get_game_status(group_id)
    exchange_date = database.get_exchange_date(group_id)
    participants = database.get_participants_data(group_id)
    participants_display = 'none' if len(participants) == 0 else str(len(participants))
    await update.message.reply_text(
        f"Game status: {status}\nExchange date: {exchange_date or '(not set)'}\nParticipants: {participants_display}"
    )


async def cancelgame_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Group command to fully cancel/reset the current Secret Santa game (deletes participants and date)."""
    if update.effective_chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("This command must be used in a group chat.")
        return

    group_id = update.effective_chat.id
    try:
        database.cancel_game_full(group_id)
        await update.message.reply_text("Secret Santa fully reset. Participants and date cleared; status set to JOINING.")
    except Exception as e:
        logging.debug(f"Failed to fully cancel game for {group_id}: {e}")
        await update.message.reply_text("Failed to fully reset the game. See logs.")




async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /summary command in group: shows participants count, users, and exchange date after draw."""
    if update.effective_chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("This command must be used in a group chat.")
        return

    group_id = update.effective_chat.id
    database.ensure_game_exists(group_id)
    status = database.get_game_status(group_id)
    if status != 'COMPLETED':
        await update.message.reply_text("The draw has not been completed yet. Use this after the draw.")
        return

    participants = database.get_participants_data(group_id)
    count = len(participants)
    exchange_date = database.get_exchange_date(group_id) or '(not set)'
    if count == 0:
        await update.message.reply_text(
            f"Secret Santa Summary\n\nParticipants: none\n\nExchange Day: {exchange_date}"
        )
        return

    names_list = "\n".join([f"• @{p[1]}" for p in participants])
    await update.message.reply_text(
        f"Secret Santa Summary\n\n"
        f"Participants: {count}\n"
        f"{names_list}\n\n"
        f"Exchange Day: {exchange_date}"
    )

def main():
    database.init_db()

    application = Application.builder().token(TOKEN).build()

    date_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('setdate', setdate_command)],
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
    application.add_handler(CommandHandler(["daysleft", "reminddays"], days_left))
    application.add_handler(CommandHandler("participants", participants))
    application.add_handler(CommandHandler(["draw", "redraw"], draw_command))
    application.add_handler(CommandHandler("join", join_command))
    application.add_handler(CommandHandler("summary", summary_command))
    application.add_handler(CommandHandler("help", help_command))

    # Debug helpers
    application.add_handler(CommandHandler("chatid", lambda u, c: chatid_command(u, c)))
    application.add_handler(CommandHandler("showdate", lambda u, c: showdate_command(u, c)))
    # application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CommandHandler("cancel", cancelgame_command))
   
    
    print("Bot started polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == '__main__':
    main()