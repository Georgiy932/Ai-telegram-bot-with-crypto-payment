#payments.py
import requests
from config import NOWPAYMENTS_API_KEY
from database import AsyncSessionLocal, User
from datetime import datetime, timedelta


NOWPAYMENTS_API_URL = "https://api.nowpayments.io/v1/invoice"

async def create_invoice(user_id: int, amount: float, plan_key: str):
    payload = {
        "price_amount": amount,
        "price_currency": "usd",
        "order_id": str(user_id),
        "order_description": plan_key,
        "ipn_callback_url": "https://t.me/HotAIGirrl_bot/webhook",  # Замените на ваш хост
        "success_url": "https://t.me/HotAIGirrl_bot",
    }

    headers = {
        "x-api-key": NOWPAYMENTS_API_KEY,
        "Content-Type": "application/json"
    }

    res = requests.post(NOWPAYMENTS_API_URL, json=payload, headers=headers)
    data = res.json()

    print("🔥 Ответ от NOWPayments:", data)  # Добавим лог

    if "invoice_url" not in data:
        raise ValueError(f"Ошибка создания инвойса: {data}")

    return data["invoice_url"], data["id"]
