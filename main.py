import logging

from google import genai
from google.genai import types
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CallbackContext, MessageHandler, filters

from config import BOT_TOKEN, GOOGLE_API_KEY, SYSTEM_INSTRUCTIONS

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


client = genai.Client(api_key=GOOGLE_API_KEY)


async def messages(update: Update, context: CallbackContext):

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

        await update.message.reply_text(response.text, parse_mode="MARKDOWN")


def main() -> None:
    """Start the bot."""
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(
        MessageHandler(filters=filters.ChatType.GROUPS, callback=messages)
    )

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
