# 📰 EMCL Bot
The earthmc live news bot

---

## 🌍 Features

- 🎙️ **News Submission**: Registered reporters can post news with a title, description, image, credit, and tags (region, category, language).
- 📢 **Auto-Broadcasting**: Automatically distributes news to all Discord channels subscribed to specific categories, regions, and languages.
- 🔐 **Reporter System**: Only verified reporters can post news.
- 🔄 **Language-Aware Routing**: Delivers news in the subscriber’s preferred language channel (e.g., `EN`, `FR`, `TURK`).
- 🔎 **Deduplication**: Prevents the same news from being sent to the same channel more than once.

---

## 📦 Frameworks Used Bot

- [`discord.py`](https://github.com/Rapptz/discord.py) 
- [`TortoiseORM`](https://github.com/tortoise/tortoise-orm)
- [`fastapi`](https://github.com/fastapi/fastapi)
- python version 3.12+ (ik its not a framework but eh)

---

## 🛠️ Setup Instructions

1. **Clone the Repository**

```bash
git clone https://github.com/chariskar/emcl
cd emcl
python -m venv venv
venv/scripts/activate
python -m pip install -r dependencies.txt
python src/main.py
```
## note that the api runs on port 3000 by default
## enable strict type checking for a fun time