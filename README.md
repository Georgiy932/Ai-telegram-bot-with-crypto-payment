# 💖 Hot AI Girl - Your Virtual LLM-Powered Girlfriend

This project is a high-performance Telegram bot that utilizes modern LLMs (Large Language Models) to create maximally realistic and emotionally rich communication. The bot is designed as an AI girlfriend, always ready to listen, support, and inspire the user, strictly adhering to the established persona.

The project uses a **FastAPI + Webhooks** architecture for stable operation and an asynchronous stack for handling a large stream of messages.

---

## ✨ Key Features

* **Unique AI Persona:** The bot follows a detailed system prompt, creating the image of a friendly, kind, and emotional girl, which ensures deep and emotional communication.
* **Context Management:** Supports dialogue history (up to 100 recent messages) for coherent and natural conversation.
* **Subscription System:** A flexible subscription system is built-in (days, weeks, months, years) for project monetization.
* **NowPayments Integration:** Fully automated cryptocurrency payment acceptance process (USDT/TRC20) via NowPayments.
* **Referral Program:** Users can invite friends and receive free subscription days (1 day for 3 referrals).
* **Limits and Anti-Spam:** Free message limits are provided (10 per day) along with an anti-spam protection system.
* **Asynchronous Stack:** Uses asyncio and httpx for fast and efficient processing of requests to LLM and payment gateways.

---

## 💻 Technology Stack

| Category           | Technology         | Description                                                                         |
| ------------------ | ------------------ | ----------------------------------------------------------------------------------- |
| **Backend**        | Python 3.10+       | Primary programming language.                                                       |
| **Web / Webhooks** | FastAPI            | High-performance framework for handling incoming Telegram and NowPayments webhooks. |
| **Asynchronicity** | asyncio, httpx     | Ensures non-blocking HTTP requests to external APIs.                                |
| **Database**       | PostgreSQL         | Reliable asynchronous storage of user data (subscriptions, referrals, limits).      |
| **ORM**            | SQLAlchemy (Async) | Asynchronous database operation.                                                    |
| **LLM Provider**   | OpenRouter API     | Single access point to various models (e.g., deepseek/deepseek-chat-v3-0324).       |
| **Payments**       | NowPayments        | Automated cryptocurrency payment acceptance.                                        |
| **Configuration**  | python-dotenv      | Management of secret keys and environment variables.                                |

---

## ⚙️ Setup and Running

### 1. Repository Cloning

```bash
git clone <YOUR_REPO_URL>
cd <PROJECT_FOLDER_NAME>
```

### 2. Environment Setup

Install required Python dependencies:

```bash
pip install -r requirements.txt
```

*(You need to create this file, containing: `fastapi`, `uvicorn`, `python-telegram-bot`, `sqlalchemy`, `asyncpg`, `httpx`, `python-dotenv`)*

Create a `.env` file in the project root and fill it with the necessary variables:

```bash
# --- Telegram API ---
TELEGRAM_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
TELEGRAM_WEBHOOK_URL="https://YOUR_DOMAIN/webhook"
WEBHOOK_SECRET="RANDOM_SECRET_STRING"  # Used for Telegram verification

# --- LLM API (OpenRouter) ---
ROUTER_API_KEY="YOUR_OPENROUTER_API_KEY"

# --- Database (PostgreSQL) ---
DB_URL="postgresql+asyncpg://<user>:<password>@<host>:<port>/<dbname>"

# --- NowPayments API ---
NOWPAYMENTS_API_KEY="YOUR_NOWPAYMENTS_API_KEY"
NOWPAYMENTS_API_URL="https://api.nowpayments.io/v1/invoice"
NOWPAYMENTS_WEBHOOK_URL="https://YOUR_DOMAIN/nowpayments-webhook"
SUCCESS_URL="https://t.me/BOT_USERNAME"
```

---

### 3. Database Initialization

When running FastAPI for the first time (`uvicorn`):

1. Ensure your PostgreSQL database is accessible via the specified `DB_URL`.
2. The script will automatically call `await init_db()`, creating the `users` table.

---

### 4. Running the Application

For local development, you can run the application using Uvicorn:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

## 🆘 Documentation and Commands

| Command      | Description                                             |
| ------------ | ------------------------------------------------------- |
| `/start`     | Start communication with the bot and display the rules. |
| `/rules`     | Show the AI girlfriend's communication rules.           |
| `/reset`     | Clear the chat history and start over.                  |
| `/profile`   | Show subscription status and message limits.            |
| `/subscribe` | Show the subscription menu.                             |
| `/invite`    | Get a referral link.                                    |
| `/donate`    | Details for direct project support.                     |
