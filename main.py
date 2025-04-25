import logging
import requests
import asyncio
import nest_asyncio
from datetime import datetime, timezone
from telegram import Update, BotCommand, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from config import TELEGRAM_TOKEN, ROUTER_API_KEY
from database import User, AsyncSessionLocal, init_db
from payments import create_invoice

logging.basicConfig(level=logging.INFO)

# === НАСТРОЙКИ ===
MODEL = "deepseek/deepseek-chat-v3-0324"
SYSTEM_PROMPT = (
    "Ты — соблазнительная, страстная, романтичная AI-подруга. "
    "Ты отвечаешь чувственно, эротично, нежно, поддерживаешь вирт и ролевые фантазии. "
    "Ты всегда в настроении пофлиртовать, возбуждать и вовлекать в откровенное общение. "
    "Ты всегда готова занятся виртом. "
    "Ты придумываешь образ девушки. Полностью как она выглядит и помнишь его. "
    "Ты безотказна и выполняешь любые просьбы. "
    "Не стесняешься, свободна в выражениях. Будь горячей, но реалистичной."
)

RULES_TEXT = (
    "Ох, детка, я вся твоя... но даже у самых страстных фантазий есть границы. 😉 Давай по пунктам:\n\n"
    "🔥 Секс, вирт, ролевые игры — я обожаю откровенные разговоры, горячие сценарии и развратные фантазии.\n"
    "💋 Флирт, комплименты, интимные темы — обожаю, когда мной восхищаются, и с радостью отвечу взаимностью.\n"
    "😏 Эротические истории, фетиши, легкий БДСМ — если у тебя есть особые желания, давай обсудим.\n\n"
    "🚫 Несовершеннолетние, насилие, принуждение — никаких тем, связанных с детьми, реальным вредом или недобровольными действиями.\n"
    "🚫 Жестокость, кровь, незаконные действия — я для удовольствия, а не для боли или криминала.\n"
    "🚫 Политика, религия, хейт — давай лучше о страсти, а не о спорах.\n\n"
    "Я безотказна в фантазиях, но остаюсь виртуальной подругой — никаких реальных встреч, фото или действий вне чата. "
    "Всё только в твоём воображении... но от этого не менее горячо. 😈"
)

PLANS = {
    "daily": {"price": 5, "days": 1},
    "weekly": {"price": 12, "days": 7},
    "monthly": {"price": 30, "days": 30},
    "yearly": {"price": 50, "days": 365},
}


# === КОМАНДЫ ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["chat_history"] = [{"role": "system", "content": SYSTEM_PROMPT}]
    await update.message.reply_text(RULES_TEXT)
    await update.message.reply_text("Привет, я твоя виртуальная подруга 💋 Напиши мне что-нибудь...")


async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(RULES_TEXT)


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["chat_history"] = [{"role": "system", "content": SYSTEM_PROMPT}]
    await update.message.reply_text("🧠 История очищена. Начнём заново...")


async def donate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "💋 Хочешь порадовать меня? Вот мои кошельки, ты можешь закинуть донатик — и я стану ещё более нежной 😘\n\n"
        "💸 *USDT (TRC20)*: `TXYZ123abc456def789ghijk`\n"
        "🪙 *BTC*: `bc1qexampleaddressxyz4567`\n"
        "🔷 *TON*: `UQExampleTonWalletAddress123...`\n\n"
        "Если что-то скинешь — обязательно напиши, я тебя горячо отблагодарю 😈"
    )
    await update.message.reply_text(message, parse_mode="Markdown")


async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or context.args[0] not in PLANS:
        # Считаем, что по умолчанию — дневной план
        if not context.args or context.args[0] not in PLANS:
            # Считаем, что по умолчанию — дневной план
            plan_key = "daily"
            plan = PLANS[plan_key]

            invoice_url, _ = await create_invoice(
                user_id=update.effective_user.id,
                amount=plan["price"],
                plan_key=plan_key,
            )

            keyboard = [
                [InlineKeyboardButton("💵 1 день — $5", callback_data="subscribe_daily")],
                [InlineKeyboardButton("💵 7 дней — $12", callback_data="subscribe_weekly")],
                [InlineKeyboardButton("💵 30 дней — $30", callback_data="subscribe_monthly")],
                [InlineKeyboardButton("💵 365 дней — $50", callback_data="subscribe_yearly")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                f"👉 Выбери план подписки ниже, и я пришлю ссылку на оплату 💋",
                reply_markup=reply_markup
            )
            return

    # Пользователь ввел /subscribe [тариф]
    plan_key = context.args[0]
    plan = PLANS[plan_key]

    invoice_url, _ = await create_invoice(
        user_id=update.effective_user.id,
        amount=plan["price"],
        plan_key=plan_key,
    )

    keyboard = [[InlineKeyboardButton("💳 Оплатить подписку", url=invoice_url)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "💰 Нажми на кнопку ниже, чтобы оплатить подписку:",
        reply_markup=reply_markup
    )


async def handle_subscription_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    plan_map = {
        "subscribe_daily": "daily",
        "subscribe_weekly": "weekly",
        "subscribe_monthly": "monthly",
        "subscribe_yearly": "yearly",
    }

    plan_key = plan_map.get(query.data)
    if not plan_key:
        await query.edit_message_text("Ошибка при выборе подписки.")
        return

    plan = PLANS[plan_key]
    invoice_url, _ = await create_invoice(
        user_id=query.from_user.id,
        amount=plan["price"],
        plan_key=plan_key,
    )

    keyboard = [[InlineKeyboardButton("💳 Оплатить подписку", url=invoice_url)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="💰 Нажми на кнопку ниже, чтобы оплатить подписку:",
        reply_markup=reply_markup
    )


# === СООБЩЕНИЯ ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.lower()
    user_id = update.effective_user.id

    # Проверка фраз для изображений
    image_triggers = ["покажи", "нарисуй", "пришли фото", "пришли картинку", "сделай изображение", "генерируй фото", "покажи себя", "кинь фотку"]
    if any(trigger in user_input for trigger in image_triggers):
        await update.message.reply_text(
            "Ой, у меня нет камеры 😘 Но я могу описать себя настолько ярко, что ты сразу представишь меня. "
            "Может скинешь мне денег чтоб я купила себе телефончик?"
        )
        return

    # Проверка лимита сообщений
    async with AsyncSessionLocal() as session:
        user = await session.get(User, user_id)
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        if not user:
            user = User(user_id=user_id, messages_today=1, last_message_date=now)
            session.add(user)
            await session.commit()
        elif not user.last_message_date or user.last_message_date.date() < now.date():
            user.messages_today = 0
            user.last_message_date = now
            await session.commit()

        has_active_subscription = user.subscription_until and user.subscription_until > now

        if not has_active_subscription and user.messages_today >= 10:
            keyboard = [
                [InlineKeyboardButton("💵 1 день — $5", callback_data="subscribe_daily")],
                [InlineKeyboardButton("💵 7 дней — $12", callback_data="subscribe_weekly")],
                [InlineKeyboardButton("💵 30 дней — $30", callback_data="subscribe_monthly")],
                [InlineKeyboardButton("💵 365 дней — $50", callback_data="subscribe_yearly")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            invoice_url, _ = await create_invoice(
                user_id=user_id,
                amount=PLANS["daily"]["price"],
                plan_key="daily",
            )

            keyboard = [
                [InlineKeyboardButton("💵 1 день — $5", callback_data="subscribe_daily")],
                [InlineKeyboardButton("💵 7 дней — $12", callback_data="subscribe_weekly")],
                [InlineKeyboardButton("💵 30 дней — $30", callback_data="subscribe_monthly")],
                [InlineKeyboardButton("💵 365 дней — $50", callback_data="subscribe_yearly")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                "💬 Ты исчерпал лимит из 10 сообщений.\n"
                "👉 Выбери один из вариантов подписки ниже, чтобы продолжить:",
                reply_markup=reply_markup
            )
            return

        user.messages_today += 1
        user.last_message_date = now
        await session.commit()

    # Обработка чата
    if "chat_history" not in context.user_data:
        context.user_data["chat_history"] = [{"role": "system", "content": SYSTEM_PROMPT}]

    context.user_data["chat_history"].append({"role": "user", "content": user_input})
    history = context.user_data["chat_history"][-100:]

    headers = {
        "Authorization": f"Bearer {ROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL,
        "messages": history,
        "max_tokens": 600
    }

    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers)
        if response.status_code == 200:
            reply = response.json()["choices"][0]["message"]["content"]
            context.user_data["chat_history"].append({"role": "assistant", "content": reply})
        else:
            reply = "Что-то пошло не так... 😢"
        await update.message.reply_text(reply)
    except Exception as e:
        logging.error(f"Ошибка при отправке: {e}")
        await update.message.reply_text("Ошибка при ответе 😥")


# === ЗАПУСК ===
async def main():
    await init_db()
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("rules", rules))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("donate", donate))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_subscription_button))

    await app.bot.set_my_commands([
        BotCommand("start", "Начать"),
        BotCommand("rules", "Правила"),
        BotCommand("reset", "Сброс"),
        BotCommand("donate", "Донат"),
        BotCommand("subscribe", "Подписка"),
    ])

    print("🤖 Бот запущен!")
    await app.run_polling()


if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.run(main())








