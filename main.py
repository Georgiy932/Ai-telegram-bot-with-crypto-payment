import asyncio
import logging
from datetime import datetime, timedelta, timezone
import json
import httpx
from fastapi import FastAPI, Request
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, DateTime, BigInteger, func
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import os

load_dotenv()  # Загружает переменные из .env файла
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ROUTER_API_KEY = os.getenv("ROUTER_API_KEY")
NOWPAYMENTS_API_KEY = os.getenv("NOWPAYMENTS_API_KEY")
NOWPAYMENTS_API_URL = os.getenv("NOWPAYMENTS_API_URL")
DB_URL = os.getenv("DB_URL")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
SUCCESS_URL = os.getenv("SUCCESS_URL")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
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
    "daily": {"price": 3, "days": 1},
    "weekly": {"price": 9, "days": 7},
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
    referrals = Column(Integer, default=0)

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
        try:
            res = await client.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers)
            res.raise_for_status()
            return res.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logging.error(f"Ошибка запроса к OpenRouter: {e}")
            return "Упс, произошла ошибка при генерации ответа 😢"

# ======================== БОТ ========================
logging.basicConfig(level=logging.INFO)



async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(RULES_TEXT)

async def donate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💖 *Поддержи проект донатом!*\n\n"
            "USDT (TRC20): TYekNc1RYKyjWgJDX9GmEJ3vKtbDRTv49y \n\n"
            "Любая сумма помогает развитию и поддержке бота.\n"
            "Спасибо за твою щедрость! 🙏")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    context.user_data["chat_history"] = [{"role": "system", "content": SYSTEM_PROMPT}]

    await update.message.reply_text(RULES_TEXT)
    await update.message.reply_text("Привет, я твоя виртуальная подруга 💋 Напиши мне что-нибудь...")

    # Если есть аргумент - вызываем обработчик реферала
    if context.args:
        try:
            referrer_id = int(context.args[0])
            await process_referral(user_id, referrer_id, context)
        except Exception as e:
            logging.warning(f"Ошибка при обработке реферала: {e}")



async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    async with AsyncSessionLocal() as session:
        user = await session.get(User, user_id)
        now = datetime.utcnow()

        if not user:
            await update.message.reply_text("Ты ещё не начинал со мной... Напиши что-нибудь 💌")
            return

        if user.last_message_date.date() < now.date():
            messages_left = 10
        else:
            messages_left = max(0, 10 - user.messages_today)

        if user.subscription_until and user.subscription_until > now:
            sub_text = f"🗓 Подписка активна до {user.subscription_until.strftime('%d.%m.%Y %H:%M')}"
            messages_left = "∞"
        else:
            sub_text = "🔒 Подписка неактивна"

        await update.message.reply_text(
            f"📊 *Твой профиль:*\n"
            f"{sub_text}\n"
            f"💬 Осталось сообщений сегодня: *{messages_left}*",
            parse_mode="Markdown"
        )

async def invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    invite_link = f"https://t.me/HotAIGirrl?start={user_id}"
    async with AsyncSessionLocal() as session:
        user = await session.get(User, user_id)
        count = user.referrals if user else 0

    await update.message.reply_text(
        f"📨 Приглашай друзей по этой ссылке:\n\n"
        f"{invite_link}\n\n"
        f"🎁 За 3 приглашённых ты получаешь 1 день подписки.\n"
        f"👥 Приглашено: {count}/3"
    )


async def process_referral(user_id: int, referrer_id: int, context: ContextTypes.DEFAULT_TYPE):
    if user_id == referrer_id:
        return  # нельзя пригласить самого себя

    async with AsyncSessionLocal() as session:
        referrer = await session.get(User, referrer_id)
        new_user = await session.get(User, user_id)

        if new_user:
            return  # пользователь уже есть, реферал не начисляется

        # создаём нового пользователя
        session.add(User(id=user_id))

        if referrer:
            referrer.referrals += 1
            message = f"🎉 Тебя пригласил пользователь {referrer_id}!\n"
            if referrer.referrals >= 3:
                now = datetime.utcnow()
                referrer.subscription_until = max(referrer.subscription_until or now, now) + timedelta(days=1)
                referrer.referrals = 0
                message += "🎁 Он пригласил 3 друзей и получил 1 день подписки!"
            else:
                message += f"👥 Он пригласил уже {referrer.referrals}/3 друзей."

            await session.commit()

            # уведомим реферера
            try:
                await context.bot.send_message(chat_id=referrer_id, text=message)
            except Exception:
                pass


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["chat_history"] = [{"role": "system", "content": SYSTEM_PROMPT}]
    await update.message.reply_text("🧠 История очищена. Начнём заново...")

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💵 1 день — $3", callback_data="subscribe_daily")],
        [InlineKeyboardButton("💸 7 дней — $9", callback_data="subscribe_weekly")],
        [InlineKeyboardButton("💰 30 дней — $30", callback_data="subscribe_monthly")],
        [InlineKeyboardButton("🏆 365 дней — $50", callback_data="subscribe_yearly")],
    ]
    await update.message.reply_text("Выбери план подписки👇:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_subscription_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "subscribe_daily":
        # Показываем список тарифов
        keyboard = [
            [InlineKeyboardButton("💵 1 день — $3", callback_data="plan_1d")],
            [InlineKeyboardButton("💸 7 дней — $9", callback_data="plan_7d")],
            [InlineKeyboardButton("💰 30 дней — $30", callback_data="plan_30d")],
            [InlineKeyboardButton("🏆 365 дней — $50", callback_data="plan_365d")],
        ]
        await query.message.reply_text(
            "Выбери план подписки👇:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    elif query.data == "invite_friends":
        user_id = query.from_user.id
        invite_link = f"https://t.me/HotAIGirrl_bot?start={user_id}"
        async with AsyncSessionLocal() as session:
            user = await session.get(User, user_id)
            count = user.referrals if user else 0

        await query.message.reply_text(
            f"📨 Приглашай друзей по этой ссылке:\n\n"
            f"{invite_link}\n\n"
            f"🎁 За 3 приглашённых ты получаешь 1 день подписки.\n"
            f"👥 Приглашено: {count}/3"
        )
        return


    elif query.data.startswith("plan_"):
        duration_map = {
            "plan_1d": ("1 день", 5),
            "plan_7d": ("7 дней", 12),
            "plan_30d": ("30 дней", 30),
            "plan_365d": ("365 дней", 50),
        }
        plan_key = query.data
        label, amount = duration_map.get(plan_key, ("1 день", 5))

        try:
            invoice_url = await create_invoice(user_id=query.from_user.id, amount=amount, plan_key=plan_key)
            await query.message.reply_text(
                f"✅ План: {label}\n💵 Стоимость: ${amount}\n\n"
                f"🔗 Перейди по ссылке для оплаты:\n{invoice_url}"
            )
        except Exception as e:
            await query.message.reply_text(f"❌ Ошибка при создании платежа: {e}")

    query = update.callback_query
    await query.answer()


    plan_map = {
        "subscribe_daily": "daily",
        "subscribe_weekly": "weekly",
        "subscribe_monthly": "monthly",
        "subscribe_yearly": "yearly",
    }

    plan_key = plan_map.get(query.data)
    if not plan_key or plan_key not in PLANS:
        await query.message.reply_text("Ошибка: выбранный тариф не найден.")
        return

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
        else:
            # Если день изменился, сбрасываем счётчик сообщений
            if user.last_message_date.date() < now.date():
                user.messages_today = 0
                user.last_message_date = now
                await session.commit()

        has_active_subscription = user.subscription_until and user.subscription_until > now
        invite_link = f"https://t.me/HotAIGirrl_bot?start={user_id}"

        if not has_active_subscription and user.messages_today >= 10:
            keyboard = [
                [InlineKeyboardButton("💳 Купить подписку", callback_data="subscribe_daily")],
                [InlineKeyboardButton("🎁 Пригласить 3 друзей и получить 1 день", callback_data="invite_friends")],
            ]

            await update.message.reply_text(
                "🔔 У тебя закончились 10 бесплатных сообщений на сегодня.\n\n"
                "Выбери, как продолжить:\n"
                "1. Купить подписку 💵\n"
                "2. Пригласить 3 друзей по ссылке — и получить 1 день премиума бесплатно 🎁",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

            return

        # Увеличиваем счётчик сообщений, если пользователь без подписки
        if not has_active_subscription:
            user.messages_today += 1
            user.last_message_date = now
            await session.commit()

    # Чат-история
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
    bot_app.add_handler(CommandHandler("donate", donate))
    bot_app.add_handler(CommandHandler("profile", profile))
    bot_app.add_handler(CommandHandler("invite", invite))
    bot_app.add_handler(CommandHandler("subscribe", subscribe))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    bot_app.add_handler(CallbackQueryHandler(handle_subscription_button, pattern=r"^subscribe_"))
    bot_app.add_handler(CallbackQueryHandler(subscribe, pattern=r"^show_subscribe$"))

    await bot_app.bot.set_my_commands([
        BotCommand("start", "Начать"),
        BotCommand("rules", "Правила"),
        BotCommand("reset", "Сброс"),
        BotCommand("donate", "Поддержать проект"),
        BotCommand("subscribe", "Подписка"),
        BotCommand("profile", "Профиль"),
    ])

    return bot_app

# ======================== FASTAPI ========================
@asynccontextmanager
async def lifespan(app: FastAPI):
    global bot_app

    await init_db()
    bot_app = await create_bot()

    await bot_app.initialize()
    await bot_app.start()
    await bot_app.bot.set_webhook(WEBHOOK_URL)

    print("✅ Бот запущен!")

    yield

    if bot_app:
        await bot_app.stop()
        await bot_app.shutdown()
        print("🛑 Бот остановлен!")



bot_app = None
# ======================== FASTAPI ========================

app = FastAPI(lifespan=lifespan)  # Перенеси СЮДА

@app.get("/")
async def root():
    return {"message": "Бот работает! 🔥"}

@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    await bot_app.update_queue.put(Update.de_json(data, bot_app.bot))
    return {"status": "ok"}

@app.post("/nowpayments-webhook")
async def payment_webhook(request: Request):
    try:
        data = await request.json()
    except Exception as e:
        logging.error(f"Ошибка парсинга JSON: {e}")
        return {"status": "invalid json"}

    if data.get("payment_status") == "finished":
        user_id = int(data.get("order_id"))
        plan_key = data.get("order_description", "")
        days = PLANS.get(plan_key, {}).get("days", 0)
        days = {
            "daily": 1,
            "weekly": 7,
            "monthly": 30,
            "yearly": 365
        }.get(plan_key, 0)

        async with AsyncSessionLocal() as session:
            user = await session.get(User, user_id)
            if not user:
                user = User(id=user_id)

            user.subscription_until = datetime.utcnow() + timedelta(days=days)
            session.add(user)
            await session.commit()

    return {"status": "ok"}









