import html
import json
import logging
import traceback

from google import genai
from google.genai import types
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from config import BOT_TOKEN, DEVELOPER_CHAT_ID, GOOGLE_API_KEY, SYSTEM_INSTRUCTIONS

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

client = genai.Client(
    api_key=GOOGLE_API_KEY,
    http_options=types.HttpOptions(client_args={"proxy": "socks5://43.153.81.153:443"}),
)


def split_text(text: str, max_chars=1024):
    sections = []
    while len(text) > max_chars:
        corte = text.rfind(" ", 0, max_chars)
        if corte == -1:
            corte = max_chars
        sections.append(text[:corte])
        text = text[corte:].lstrip()
    if text:
        sections.append(text)
    return sections


async def messages(update: Update, context: ContextTypes.DEFAULT_TYPE):

    content = None

    if (
        update.message.reply_to_message
        and update.message.reply_to_message.from_user.id == context.bot.id
    ):

        msg_user = f"{update.effective_user.first_name}: {update.message.text}"

        content = [
            types.Content(
                role="model",
                parts=[types.Part.from_text(text=update.message.reply_to_message.text)],
            ),
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=msg_user)],
            ),
        ]

    elif (
        f"@{context.bot.username}" in update.message.text
        and not update.message.reply_to_message
    ):

        content = f"{update.effective_user.first_name}: {update.message.text}"

    elif (
        f"@{context.bot.username}" in update.message.text
        and update.message.reply_to_message
        and update.message.reply_to_message.from_user.id != context.bot.id
    ):

        msg_user1 = f"{update.message.reply_to_message.from_user.first_name}: {update.message.reply_to_message.text}"

        msg_user2 = f"{update.effective_user.first_name}: {update.message.text}"

        content = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=msg_user1)],
            ),
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=msg_user2)],
            ),
        ]

    if content:

        await context.bot.send_chat_action(
            chat_id=update.message.chat_id, action=ChatAction.TYPING
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=content,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTIONS.format_map(
                    {
                        "name": context.bot.first_name,
                        "username": context.bot.username,
                    }
                ),
            ),
        )

        texts = split_text(response.text)

        for text in texts:

            await update.message.reply_text(text, parse_mode="MARKDOWN")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""

    logger.error("Exception while handling an update:", exc_info=context.error)

    tb_list = traceback.format_exception(
        None, context.error, context.error.__traceback__
    )
    tb_string = "".join(tb_list)

    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message = (
        "An exception was raised while handling an update\n"
        f"update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}"
        "\n\n"
        f"context.chat_data = {html.escape(str(context.chat_data))}\n\n"
        f"context.user_data = {html.escape(str(context.user_data))}\n\n"
        f"{html.escape(tb_string)}"
    )

    texts = split_text(message, max_chars=4096)

    for text in texts:

        await context.bot.send_message(chat_id=DEVELOPER_CHAT_ID, text=text)


def main() -> None:
    """Start the bot."""
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(
        MessageHandler(filters=filters.ChatType.GROUPS, callback=messages)
    )
    application.add_error_handler(error_handler)

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
