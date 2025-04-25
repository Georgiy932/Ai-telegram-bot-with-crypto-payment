#webhook.py
from fastapi import FastAPI, Request
from database import AsyncSessionLocal, User
from datetime import datetime, timedelta
import uvicorn

app = FastAPI()

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

            subscription_until = datetime.utcnow() + timedelta(days=days)
            user.subscription_until = subscription_until
            session.add(user)
            await session.commit()

    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("webhook:app", host="0.0.0.0", port=8000)
