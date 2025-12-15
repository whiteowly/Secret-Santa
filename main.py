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

TOKEN = "7821913361:AAEb3wpAAAJUdJG3z3pEO2P7BQz-swU5G0M"
# os.getenv('TELEGRAM_TOKEN') or os.getenv('TOKEN')
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
        "Gang Members\n\n"
        f"Total: 0\n\n"
        "Waiting for people to join...\n",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def join_game_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the Join button."""
    query = update.callback_query
    
    user = query.from_user
    group_id = query.message.chat_id
    # Use username if available, otherwise fallback to first_name for group alert
    username = user.username or user.first_name 
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
            f"🎁 You successfully joined the Secret Santa for **{query.message.chat.title}**!\n\n"
            f"Wait for the Draw to start. I will send you a DM with your recipient's name "
            f"right here once the group admin hits the 'Draw' button."
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
                    text=f"❗ @{username} **I couldn't DM you!** Please start a private chat with me first "
                         f"(by searching for me or clicking my name) and send /start, then try joining again.",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logging.debug(f"Failed to warn group about DM failure: {e}")

        # Announce join to the group
        try:
            mention = f"@{user.username}" if user.username else user.first_name
            await context.bot.send_message(
                chat_id=group_id,
                text=f"🎉 {mention} has joined the Secret Santa!",
                parse_mode='Markdown'
            )
        except Exception as e:
            logging.debug(f"Could not send join announcement: {e}")

        # Update the inline group message and also post a fresh summary message
        try:
            await query.edit_message_text(
                 text=f"Gang Members\n\n"
                     f"Total: {count}\n"
                     f"{names_list}\n\n"
                     f"{group_status_text}",
                reply_markup=reply_markup_group, 
                parse_mode='Markdown'
            )

            try:
                await context.bot.send_message(
                    chat_id=group_id,
                    text=f"Gang Members\n\n"
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

    added = database.add_participant(user.id, group_id, username)

    participants = database.get_participants_data(group_id)
    count = len(participants)

    names_list = "\n".join([f"• @{p[1]}" for p in participants])

    if added:
        # Try to DM confirmation
        dm_text = (
            f"🎁 You successfully joined the Secret Santa for {update.effective_chat.title}!\n\n"
            f"Wait for the Draw to start. I will send you a DM with your recipient's name "
            f"right here once the group admin hits the 'Draw' button."
        )

        try:
            await context.bot.send_message(chat_id=user.id, text=dm_text)
        except Exception:
            try:
                await context.bot.send_message(
                    chat_id=group_id,
                    text=(f"❗ @{username} I couldn't DM you! Please start a private chat with me first "
                          f"and send /start, then try joining again.")
                )
            except Exception as e:
                logging.debug(f"Failed to warn group about DM failure: {e}")

        # Announce to group
        try:
            mention = f"@{user.username}" if user.username else user.first_name
            await context.bot.send_message(chat_id=group_id, text=f"🎉 {mention} has joined the Secret Santa!")
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
                text=(f"Gang Members\n\nTotal: {count}\n"
                      f"{names_list}\n\n{group_status_text}"),
                reply_markup=reply_markup_group
            )
        except Exception as e:
            logging.debug(f"Could not send group update message: {e}")
    else:
        await update.message.reply_text("You are already in the list!")

async def go_draw_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the Draw logic using the Database."""
    query = update.callback_query
    group_id = query.message.chat_id

    # Ensure a game row exists and check its status to avoid double-draws
    database.ensure_game_exists(group_id)
    status = database.get_game_status(group_id)
    if status == 'COMPLETED':
        await query.answer("Draw already completed for this group.", show_alert=True)
        return
    if status == 'DRAWING':
        await query.answer("A draw is already in progress. Please wait.", show_alert=True)
        return

    participants = database.get_participants_data(group_id)

    if len(participants) < 2:
        await query.answer("Need at least 2 people!", show_alert=True)
        return
    
    await query.answer("Drawing names now...")

    # Attempt an atomic status transition to DRAWING; if it fails, another draw is in progress or completed.
    try:
        set_ok = database.try_set_status_to_drawing(group_id)
        if not set_ok:
            current = database.get_game_status(group_id)
            # If DB row exists but status is NULL/empty, fall back to direct update
            if current is None or (isinstance(current, str) and current.strip() == ''):
                try:
                    database.update_game_status(group_id, 'DRAWING')
                except Exception:
                    logging.debug("Fallback: failed to set DRAWING directly")
            else:
                await query.answer(f"Cannot start draw. Current status: {current}", show_alert=True)
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

   
    # This call will save assignments and set status to COMPLETED
    database.update_assignments_and_status(group_id, pairs)
    exchange_date = database.get_exchange_date(group_id)
    date_info = f"\nExchange Day: {exchange_date}" if exchange_date else ""

    
    failed_dms = []
    success_count = 0
    for santa_id, target_id in pairs:
        target_name = id_to_name[target_id]
        try:
            # The assignment message (DM)
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
            # Identify and record the username of the user who failed to receive the DM
            failed_user_info = next((p for p in participants if p[0] == santa_id), None)
            if failed_user_info:
                failed_dms.append(failed_user_info[1]) 

    # Prepare message for group chat with results
    failed_info = ""
    if failed_dms:
        # Only list unique failed users (in case the same user was in the list multiple times, though unlikely here)
        unique_failed_dms = sorted(list(set(failed_dms)))
        failed_list = "\n".join([f"• @{name}" for name in unique_failed_dms])
        failed_info = (
            f"\n\n⚠️ **DM Failures!**\n"
            f"The following users need to start a private chat with me:\n"
            f"{failed_list}"
        )

    await query.message.edit_text(
        f"Draw Complete!\n\n"
        f"Participants: {len(user_ids)}\n"
        f"DMs Sent: {success_count}\n"
        f"{failed_info}\n"
        "Check your DMs to see who you got!"
    )


async def draw_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /draw command to perform the Secret Santa draw (group command)."""
    if update.effective_chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("This command must be used in a group chat.")
        return

    group_id = update.effective_chat.id

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
                text=f"You are {target_name}'s secret santa!\n\n"
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
            f"\n\n⚠️ **DM Failures!**\n"
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


async def participants(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /participants command, listing every participant in the group."""
    if update.effective_chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("This command must be used in a group chat.")
        return

    group_id = update.effective_chat.id
    participants = database.get_participants_data(group_id)

    if not participants:
        await update.message.reply_text(
            "Gang Members\n\nTotal: 0\n\nWaiting for people to join..."
        )
        return

    names_list = "\n".join([f"• @{p[1]}" for p in participants])
    await update.message.reply_text(
        f"Gang Members\n\nTotal: {len(participants)}\n{names_list}"
    )


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
    names_list = "\n".join([f"• @{p[1]}" for p in participants]) if participants else "(no participants)"
    exchange_date = database.get_exchange_date(group_id) or '(not set)'

    await update.message.reply_text(
        f"Secret Santa Summary\n\n"
        f"Participants: {count}\n"
        f"{names_list}\n\n"
        f"Exchange Day: {exchange_date}"
    )


async def summary_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the 'summary_btn' callback pressed by users (typically from a DM). Sends personal assignment(s) or a brief summary."""
    query = update.callback_query
    user = query.from_user
    user_id = user.id

    # Fetch assignments where this user is the santa
    try:
        assignments = database.get_all_assignments_for_user(user_id)
    except Exception as e:
        logging.debug(f"Error fetching assignments for user {user_id}: {e}")
        assignments = []

    if not assignments:
        try:
            await query.answer()
            await context.bot.send_message(chat_id=user_id, text="No assignments found for you yet.")
        except Exception:
            logging.debug("Could not send personal summary DM")
        return

    # Build a readable reply
    lines = []
    for grp_id, target_name, exch_date in assignments:
        exch = exch_date or '(not set)'
        lines.append(f"Group {grp_id}: @{target_name} — Exchange Day: {exch}")

    text = "Your Secret Santa Assignments:\n\n" + "\n".join(lines)
    try:
        await query.answer()
        await context.bot.send_message(chat_id=user_id, text=text)
    except Exception:
        logging.debug("Failed to send assignment summary DM")



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
    application.add_handler(CommandHandler("participants", participants))
    application.add_handler(CommandHandler(["draw", "redraw"], draw_command))
    application.add_handler(CommandHandler("join", join_command))
    application.add_handler(CommandHandler("summary", summary_command))
    application.add_handler(CallbackQueryHandler(summary_callback, pattern='^summary_btn$'))
   
    
    print("Bot started polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == '__main__':
    main()