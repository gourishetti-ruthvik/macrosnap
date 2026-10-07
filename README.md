# 🥗 MacroSnap — AI Vision Nutrition Chatbot

**Live app:** https://macrosnap-aivison.streamlit.app/

Snap a meal photo (or describe it), get calories and macros from **Gemini Vision**, watch an
animated dashboard fill up, and text yourself the summary on **WhatsApp** through Twilio.

Built on **Streamlit**, as in the workshop guide. The animated UI uses Streamlit Components v2 with
**GSAP** (hero timeline, number count-ups) and **Motion** (spring rings, cards, chips), loaded from a CDN.

```
app.py                  # the app: onboarding → chat + dashboard → WhatsApp
prompts.py              # the AI's personality + JSON reply contract
ui.py                   # animated components (hero, macro dashboard) + theme
frontend/               # their HTML / CSS / JS
.streamlit/config.toml  # brand theme (light + dark)
.streamlit/secrets.toml.example
test_app.py             # smoke check (no network)
```

## 1. Get your keys (about 10 minutes, all free)

| Secret | Where to get it |
|---|---|
| `GEMINI_API_KEY` | [aistudio.google.com](https://aistudio.google.com) → **Get API key** → **Create API key** |
| `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` | Sign up at [twilio.com/try-twilio](https://www.twilio.com/try-twilio) → [Console](https://console.twilio.com) home page → **Account Info** box |
| `TWILIO_WHATSAPP_FROM` | `whatsapp:` + the sandbox number shown on your sandbox page, e.g. `whatsapp:+17372508034` (older accounts: `+14155238886`) |
| `TWILIO_CONTENT_SID` | **Optional.** Leave it as the placeholder on a free trial (see below) |

**WhatsApp sandbox (required):**
1. In the Twilio Console go to **Messaging → Try it out → Send a WhatsApp message**.
2. From the phone you'll test with, send the join code shown there (e.g. `join happy-tiger`) to the **sandbox number shown on that page** on WhatsApp.
   - The opt-in lapses after about 72 hours of inactivity. Just send it again.
3. **Trial accounts only:** verify that same number in **Phone Numbers → Manage → Verified Caller IDs →
   Add a new Caller ID**, using an SMS or call code. Without this Twilio rejects every send with
   `HTTP 422 … add the 'to' number as a verified recipient`.

**Free trial vs template:** Twilio trial accounts can't use Content Templates. Without one,
MacroSnap sends the summary as plain text, which WhatsApp delivers only within **24 hours of your
last message to the sandbox**. If a summary doesn't arrive, send "hi" to the sandbox number and
press Send again. On a paid account you can create a Text template
`Hi {{1}}, here's your MacroSnap summary: {{2}}` in **Messaging → Content Template Builder** and put its
`HX…` SID in `TWILIO_CONTENT_SID`. Summaries then arrive any time.

Then copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill in the values.
That file is gitignored, so never commit it.

**For reviewers or anyone who isn't verified:** when Twilio can't deliver (a trial account messaging
an unverified number, or a number that hasn't joined the sandbox), MacroSnap shows a
**💬 Open in WhatsApp** button. It opens WhatsApp with the same summary filled in, ready to send to
yourself. No Twilio setup is needed, so the WhatsApp step works for everyone.

## 2. Run locally

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1      # if blocked: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
pip install -r requirements.txt
streamlit run app.py             # http://localhost:8501
```

Onboard with the number that joined the sandbox. Ask a text question, attach a meal photo, then hit
**Send to WhatsApp**. Run the smoke check with `python test_app.py`.

## 3. Deploy (Streamlit Community Cloud)

1. Push to GitHub. Only `secrets.toml.example` should be tracked.
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app** → pick the repo, set the main file to `app.py`.
3. Open **Settings → Secrets** and paste the contents of your local `secrets.toml`.
4. Click **Deploy**.

## Notes
- The model is `gemini-3.1-flash-lite`, which has the biggest free quota. If Gemini reports a 404 or 503, change `MODEL_NAME` in `app.py` to another model listed in AI Studio.
- Daily goals (2000 kcal / 120 P / 250 C / 70 F) are set by `DAILY_GOALS` in `app.py`.
- Animations respect the OS "reduce motion" setting. If the CDN is blocked, the UI still works, just without animation.
