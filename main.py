import asyncio
import logging
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import FastAPI, Request
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, DateTime, BigInteger, func
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from contextlib import asynccontextmanager

# ======================== КОНФИГ ========================
TELEGRAM_TOKEN = "7100808154:AAGGeC57S4T-_eXqpXowI-ZB-vv-ltqjSmY"
ROUTER_API_KEY = "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"
DB_URL = "postgresql+asyncpg://georgiy:19A0DjfgzwFazftwluXKKFaZU60jeY3T@dpg-d07spb2dbo4c73bs7l4g-a:5432/virtbot"
NOWPAYMENTS_API_KEY = "BVVS1E5-A2X4H0X-N9S5YTD-EA9MVRS"
NOWPAYMENTS_API_URL = "https://api.nowpayments.io/v1/invoice"
WEBHOOK_URL = "https://bottg-sgjr.onrender.com/webhook"
SUCCESS_URL = "https://t.me/HotAIGirrl_bot"
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

# ======================== БАЗА ДАННЫХ ========================
engine = create_async_engine(DB_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(BigInteger, primary_key=True)
    messages_today = Column(Integer, default=0)
    last_message_date = Column(DateTime, default=func.now())
    subscription_until = Column(DateTime, nullable=True)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# ======================== ПЛАТЕЖИ ========================
async def create_invoice(user_id: int, amount: float, plan_key: str):
    payload = {
        "price_amount": amount,
        "price_currency": "usd",
        "order_id": str(user_id),
        "order_description": plan_key,
        "ipn_callback_url": WEBHOOK_URL,
        "success_url": SUCCESS_URL,
    }
    headers = {
        "x-api-key": NOWPAYMENTS_API_KEY,
        "Content-Type": "application/json"
    }
    async with httpx.AsyncClient() as client:
        res = await client.post(NOWPAYMENTS_API_URL, json=payload, headers=headers)
    data = res.json()
    if "invoice_url" not in data:
        raise ValueError(f"Ошибка создания инвойса: {data}")
    return data["invoice_url"]

# ======================== CHAT API ========================
async def get_model_response(history):
    headers = {
        "Authorization": f"Bearer {ROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL,
        "messages": history,
        "max_tokens": 600
    }
    async with httpx.AsyncClient() as client:
        res = await client.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers)
    if res.status_code == 200:
        return res.json()["choices"][0]["message"]["content"]
    else:
        return "Что-то пошло не так... 😢"

# ======================== БОТ ========================
logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["chat_history"] = [{"role": "system", "content": SYSTEM_PROMPT}]
    await update.message.reply_text(RULES_TEXT)
    await update.message.reply_text("Привет, я твоя виртуальная подруга 💋 Напиши мне что-нибудь...")

async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(RULES_TEXT)

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["chat_history"] = [{"role": "system", "content": SYSTEM_PROMPT}]
    await update.message.reply_text("🧠 История очищена. Начнём заново...")

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💵 1 день — $5", callback_data="subscribe_daily")],
        [InlineKeyboardButton("💵 7 дней — $12", callback_data="subscribe_weekly")],
        [InlineKeyboardButton("💵 30 дней — $30", callback_data="subscribe_monthly")],
        [InlineKeyboardButton("💵 365 дней — $50", callback_data="subscribe_yearly")],
    ]
    await update.message.reply_text("👉 Выбери план подписки ниже:", reply_markup=InlineKeyboardMarkup(keyboard))

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
    plan = PLANS[plan_key]

    invoice_url = await create_invoice(query.from_user.id, plan["price"], plan_key)
    keyboard = [[InlineKeyboardButton("💳 Оплатить подписку", url=invoice_url)]]

    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="💰 Нажми на кнопку ниже для оплаты:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    user_id = update.effective_user.id

    async with AsyncSessionLocal() as session:
        user = await session.get(User, user_id)
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        if not user:
            user = User(id=user_id, messages_today=0, last_message_date=now)
            session.add(user)
            await session.commit()
        elif user.last_message_date.date() < now.date():
            user.messages_today = 0
            user.last_message_date = now
            await session.commit()

        has_active_subscription = user.subscription_until and user.subscription_until > now

        if not has_active_subscription and user.messages_today >= 10:
            await subscribe(update, context)
            return

        user.messages_today += 1
        user.last_message_date = now
        await session.commit()

    if "chat_history" not in context.user_data:
        context.user_data["chat_history"] = [{"role": "system", "content": SYSTEM_PROMPT}]

    context.user_data["chat_history"].append({"role": "user", "content": user_input})
    history = context.user_data["chat_history"][-100:]

    reply = await get_model_response(history)
    context.user_data["chat_history"].append({"role": "assistant", "content": reply})
    await update.message.reply_text(reply)

async def create_bot():
    bot_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("rules", rules))
    bot_app.add_handler(CommandHandler("reset", reset))
    bot_app.add_handler(CommandHandler("subscribe", subscribe))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    bot_app.add_handler(CallbackQueryHandler(handle_subscription_button))

    await bot_app.bot.set_my_commands([
        BotCommand("start", "Начать"),
        BotCommand("rules", "Правила"),
        BotCommand("reset", "Сброс"),
        BotCommand("subscribe", "Подписка"),
    ])

    return bot_app

# ======================== FASTAPI ========================
app = FastAPI()
bot_app = None


@app.get("/")
async def root():
    return {"message": "Бот работает! 🔥"}

@app.post("/webhook")
async def payment_webhook(request: Request):
    data = await request.json()

    if data.get("payment_status") == "finished":
        user_id = int(data.get("order_id"))
        plan_title = data.get("order_description", "").split()[-1]
        days = {
            "daily": 1,
            "weekly": 7,
            "monthly": 30,
            "yearly": 365
        }.get(plan_title, 0)

        async with AsyncSessionLocal() as session:
            user = await session.get(User, user_id)
            if not user:
                user = User(id=user_id)

            user.subscription_until = datetime.utcnow() + timedelta(days=days)
            session.add(user)
            await session.commit()

    return {"status": "ok"}

@asynccontextmanager
async def lifespan(app: FastAPI):
    global bot_app

    await init_db()
    bot_app = await create_bot()

    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start_polling()

    print("✅ Бот запущен!")

    yield  # <-- тут FastAPI будет работать

    if bot_app:
        await bot_app.updater.stop()
        await bot_app.stop()
        await bot_app.shutdown()
        print("🛑 Бот остановлен!")

# Применяем lifespan при создании FastAPI
app = FastAPI(lifespan=lifespan)




