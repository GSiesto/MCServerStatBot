# Monetization & Affiliate Links

The official MCServerStatBot instance is funded via optional affiliate referrals. Self-hosted
deployments remain link-free unless you explicitly opt in, so the project stays fully open-source and
transparent.

## How affiliate links work

- Responses are assembled through shared helper functions and reuse the same inline keyboard layout.
- If an affiliate URL is configured, the bot displays a short call-to-action plus a dedicated support
  button at the bottom of welcome/status/player messages.
- When no affiliate URL is provided, both the hint and the button disappear automatically.

## Configuration

| Variable | Description | Required | Default |
| --- | --- | --- | --- |
| `AFFILIATE_URL` | Tracking link to promote. | ✅ Yes | – |
| `AFFILIATE_LABEL` | Link text shown to the user. | Optional | `Create your own MC server` |
| `AFFILIATE_BLURB` | Short phrase that introduces the link. | Optional | Two-line default (`Sponsored by our hosting partner` / `Click to support the bot!`) |

Set the variables before launching the bot, for example:

```bash
# Linux/macOS
export AFFILIATE_URL="URL"
export AFFILIATE_LABEL="Create your own MC server"
export AFFILIATE_BLURB=$'Sponsored by our hosting partner\nClick to support the bot!'

# Windows PowerShell
$env:AFFILIATE_URL = "URL"
$env:AFFILIATE_LABEL = "Create your own MC server"
$env:AFFILIATE_BLURB = "Sponsored by our hosting partner`nClick to support the bot!"
```

## Transparency

- The repository ships with monetization disabled. Simply omit `AFFILIATE_URL` to remove the CTA.
- Documentation for the hosted bot explains that affiliate links help pay for uptime.
- Forks are welcome to override or remove the feature—just keep the messaging honest so users know
  when links support your infrastructure.

If you monetize your fork, consider documenting who benefits from the referral revenue and how users
can opt out.
