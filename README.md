# MCServerStatBot
Telegram Bot that helps you to check if your favorite Minecraft Servers are online. You can even see the players that are connected.

*The Bot is deployed in a Raspberry Pi, you can chat with it now*

> [@MCServerStatBot](https://t.me/MCServerStatBot)

---

## 🚀 Refactoring & AWS Modernization Plan

> **This repository is being refactored for AWS deployment. See comprehensive documentation below:**

### 📚 Documentation
- **[REFACTORING_INDEX.md](./REFACTORING_INDEX.md)** - Start here! Navigation guide for all documents
- **[REFACTORING_SUMMARY.md](./REFACTORING_SUMMARY.md)** - Quick overview (5-10 min read)
- **[REFACTORING_PLAN.md](./REFACTORING_PLAN.md)** - Complete implementation plan (45-60 min read)
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - Technical architecture & diagrams (30-45 min read)

### 🎯 Quick Summary
- **Current:** Python 3.6.14, Heroku, monolithic, no tests
- **Target:** Python 3.12, AWS ECS, microservices, 80%+ test coverage
- **Timeline:** 8-13 weeks (5 milestones)
- **AWS Services:** ECS Fargate, DynamoDB, ElastiCache, API Gateway, CloudWatch

---

## ScreenShots
<img src="https://user-images.githubusercontent.com/6242946/62581401-5d8cc080-b8a9-11e9-93c5-fd5cc0ffab44.jpg" width="360"> <img src="https://user-images.githubusercontent.com/6242946/62581402-5d8cc080-b8a9-11e9-833e-a7e51a376c11.jpg" width="360"> <img src="https://user-images.githubusercontent.com/6242946/62581403-5d8cc080-b8a9-11e9-86eb-b2b8213ab9b8.jpg" width="360"> <img src="https://user-images.githubusercontent.com/6242946/62581404-5d8cc080-b8a9-11e9-8e0e-f031e513d354.jpg" width="360">

## How to Execute in your local machine
### Enviroment Variables

TOKEN = **Your telegram TOKEM ID**

MODE = "DEV" (Local Machine) or "PROD" (For a Heroku deployment)

### Usage
Execute with python the file `main.py`.
If everything was set up fine, you will be able to start chatting with your own bot.
A file called persistent_data will be generated. This file makes it possible for the instance to know again what the link was, and thus be able to use the inline buttons (CallBacks) on the screen.

Example

```
pip install -r requirements.txt
MODE=dev TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx python main.py
```

## Notes
* If the Minecraft Servers doesn't allow Queries `enable-query=true` in `server.properties`, the bot will not be able to show the players that are connected to the game.
* It is only possible to use the inline buttons for the last petition that was made. For example, if you called two status instances, the inline buttons will only work for the last one.


