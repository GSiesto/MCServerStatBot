# MCServerStatBot

MCServerStatBot is a modern asyncio-based Telegram bot that checks the status of your favourite Minecraft Java edition servers. Ask it for `/status` to see the server description, ping and player counts, or `/players` to list who is currently online.

> Production bot: [@MCServerStatBot](https://t.me/MCServerStatBot)

## ✨ Features

- ✅ Built on `python-telegram-bot` v22 with fully asynchronous handlers
- 🎮 Uses `mcstatus` 12.x for fast server lookups and query fallbacks
- 🔒 Loads the Telegram bot token from the `TELEGRAM_BOT_TOKEN` environment variable
- 🍓 Lightweight and efficient single-process design
- 💸 Optional affiliate support button controlled entirely via environment variables

## 🧰 Requirements

- Python 3.10 or newer (Python 3.12 works great on Raspberry Pi OS Bookworm)
- A Telegram bot token from [BotFather](https://t.me/BotFather)
- Internet access from your device to the target Minecraft servers

## 🚀 Quick start (Raspberry Pi or any Linux/macOS/Windows machine)

1. **Clone the repository**

	```bash
	git clone https://github.com/GSiesto/MCServerStatBot.git
	cd MCServerStatBot
	```

2. **Create and activate a virtual environment (recommended)**

	```bash
	python -m venv .venv
	# Linux/macOS
	source .venv/bin/activate
	# Windows PowerShell
	.venv\Scripts\Activate.ps1
	```

3. **Install dependencies**

	```bash
	pip install --upgrade pip
	pip install -r requirements.txt
	```

4. **Set the Telegram bot token**

	Replace `123456789:ABC...` with the token provided by BotFather.

	```bash
	# Linux/macOS
	export TELEGRAM_BOT_TOKEN=123456789:ABC...

	# Windows PowerShell
	setx TELEGRAM_BOT_TOKEN "123456789:ABC..."
	$env:TELEGRAM_BOT_TOKEN = "123456789:ABC..."  # also set for the current session
	```

	> Tip: you can create a `.env` file and use tools like `direnv` or `dotenv` if you prefer.

5. **Optional logging tweaks**

	Set `LOG_LEVEL` (e.g., `DEBUG`, `INFO`, `WARNING`) or `LOG_FILE` to write a rotating log file while keeping console output enabled. Example:

	```bash
	# Linux/macOS
	export LOG_LEVEL=INFO
	export LOG_FILE=mcserverstatbot.log

	# Windows PowerShell
	$env:LOG_LEVEL = "INFO"
	$env:LOG_FILE = "C:\\logs\\mcserverstatbot.log"
	```

6. **Optional affiliate support button**

	Set `AFFILIATE_URL` to add a one-tap support button beneath successful responses. Customize the
	button label with `AFFILIATE_LABEL` and the inline hint with `AFFILIATE_BLURB`. When unset, the
	UI stays link-free.

	```bash
	# Linux/macOS
	export AFFILIATE_URL=URL
	export AFFILIATE_LABEL="Create your own server"
	export AFFILIATE_BLURB=$'Sponsored by our hosting partner\nClick to support the bot!'

	# Windows PowerShell
	$env:AFFILIATE_URL = "URL"
	$env:AFFILIATE_LABEL = "Create your own server"
	$env:AFFILIATE_BLURB = "Sponsored by our hosting partner`nClick to support the bot!"
	```

7. **Run the bot**

	```bash
	python main.py
	```

	You should see log output confirming the bot is polling Telegram. Send `/start` to your bot to begin.

## 🔁 Commands

- `/start` – display a quick introduction and inline buttons
- `/status <host[:port]>` – fetch latency, MOTD, version and player counts
- `/players <host[:port]>` – list online players (falls back to counts if the server disables queries)

## 📒 Notes

- Inline buttons refresh the last server you requested in the current chat. If the bot restarts, run the command again before using the buttons.
- Some servers disable the query protocol. In that case the bot will still show player counts, but not individual names.
- Keep your `TELEGRAM_BOT_TOKEN` secret. Never commit it to version control.

## 💸 Monetization (optional)

- Leave monetization disabled by default. When you want to show a support button, set the following environment variables before launching the bot:
	- `AFFILIATE_URL` – the referral link to open when the button is tapped (required to enable the UI)
	- `AFFILIATE_LABEL` – button label (defaults to `Create your own server`)
	- `AFFILIATE_BLURB` – short inline hint above the button (defaults to a two-line message: `Sponsored by our hosting partner` on the first line and `Click to support the bot!` on the second)
- See [`MONETIZATION.md`](./MONETIZATION.md) for details on how the official instance uses affiliate links while keeping self-hosted copies optional.

## 🛠️ Ideas for running 24/7 on a Raspberry Pi

- Use `tmux` or `screen` to keep the bot alive after closing SSH.
- Create a `systemd` service that runs `python main.py` on boot.
- Pair the bot with a watchdog (e.g. `systemd` `Restart=on-failure`) for extra resilience.

## 🤝 Contributing

Feel free to open issues or PRs with improvements. Suggestions for new commands, better status formatting, or monetization ideas are always welcome!

## 💰 Monetization transparency

The official hosted instance may include an affiliate link to help cover infrastructure costs. Self-hosted deployments keep the feature disabled unless you provide `AFFILIATE_URL`. See [`MONETIZATION.md`](MONETIZATION.md) for details and best practices.

## 💬 Stay in touch

For updates, feature requests, or just to say hi, you can find the developer here:

- **Telegram:** [@GSiesto](https://t.me/GSiesto)
- **GitHub:** [GSiesto](https://github.com/GSiesto)

## 📜 License


