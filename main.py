from async_lru import alru_cache
from fastapi import FastAPI, HTTPException, Request
from google import genai
from google.genai import types
from pydantic import BaseModel
from telegram import Bot, Update
from telegram.constants import ChatAction
from telegram.error import BadRequest, InvalidToken, TimedOut
from telegram.ext import Application, CallbackContext, ExtBot, MessageHandler, filters

from config import BOT_TOKEN, GOOGLE_API_KEY, SYSTEM_INSTRUCTIONS, TG_SECRET_TOKEN

client = genai.Client(api_key=GOOGLE_API_KEY)


app = FastAPI(
    title="El Yeyo Fit",
)


class Url(BaseModel):
    url: str


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

        await context.bot.send_chat_action(
            chat_id=update.message.chat_id, action=ChatAction.TYPING
        )

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


@alru_cache
async def initialize_bot():
    # pylint: disable=protected-access
    application = Application.builder().token(BOT_TOKEN).updater(None).build()
    bot = Bot(BOT_TOKEN)
    bot_user = await bot.get_me()
    bot_user._bot._initialized = True
    extbot = ExtBot(token=bot.token)
    extbot._bot_user = bot_user
    extbot._initialized = True
    application._initialized = True
    application.bot = extbot
    return application


async def process_telegram_event(update_json):
    application = await initialize_bot()
    update = Update.de_json(update_json, application.bot)
    application.add_handler(
        MessageHandler(filters=filters.ChatType.GROUPS, callback=messages)
    )
    await application.process_update(update)


@app.post("/", tags=["Process Telegram Updates"])
async def webhook(request: Request):
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") == TG_SECRET_TOKEN:
        update_json = await request.json()
        try:
            await process_telegram_event(update_json)
        except TimedOut:
            pass
    return {"message": "ok"}


@app.post("/setWebhook", tags=["Set bot webhook"])
async def set_webhook(request: Request, data: Url):
    """Use this method to specify a url and receive incoming updates via an outgoing webhook."""
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") == TG_SECRET_TOKEN:
        try:
            await Bot(BOT_TOKEN).set_webhook(url=data.url, secret_token=TG_SECRET_TOKEN)
            return {"message": "ok"}
        except (InvalidToken, BadRequest, TimedOut) as exc:
            raise HTTPException(status_code=400, detail=exc.message) from exc
    raise HTTPException(status_code=400, detail="bad requests")
