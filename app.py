import json
import re
from urllib.parse import quote

import streamlit as st
from google import genai
from google.genai import types
from twilio.rest import Client as TwilioClient

import ui
from prompts import MacroReply, SUMMARY_REQUEST_PROMPT, SYSTEM_PROMPT, WELCOME_MESSAGE_TEMPLATE

# Flash-Lite: highest free-tier quota, less busy than full Flash; still does vision + JSON.
MODEL_NAME = "gemini-3.1-flash-lite"
# ponytail: fixed daily goals; make them a sidebar setting if users ask.
DAILY_GOALS = {"calories": 2000, "protein_g": 120, "carbs_g": 250, "fat_g": 70}
AVATARS = {"assistant": "🥗", "user": "🧑"}
st.set_page_config(page_title="MacroSnap", page_icon="🥗")
ui.inject_theme()

GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
TWILIO_ACCOUNT_SID = st.secrets["TWILIO_ACCOUNT_SID"]
TWILIO_AUTH_TOKEN = st.secrets["TWILIO_AUTH_TOKEN"]
TWILIO_WHATSAPP_FROM = st.secrets["TWILIO_WHATSAPP_FROM"]
TWILIO_CONTENT_SID = st.secrets.get("TWILIO_CONTENT_SID", "")  # optional: trial accounts can't create templates


# Cached so the client survives Streamlit reruns (a fresh client per rerun
# closes the old connection and breaks the chat session).
@st.cache_resource
def get_gemini_client():
    return genai.Client(api_key=GEMINI_API_KEY)


@st.cache_resource
def get_twilio_client():
    return TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


gemini_client = get_gemini_client()
twilio_client = get_twilio_client()


def render_message(message):
    with st.chat_message(message["role"], avatar=AVATARS[message["role"]]):
        if message["kind"] == "text":
            st.write(message["content"])
        elif message["kind"] == "image":
            st.image(message["content"], width=320)


def add_message(role, kind, content):
    st.session_state.messages.append({"role": role, "kind": kind, "content": content})
    render_message(st.session_state.messages[-1])


def ask_gemini(parts):
    """Returns (reply_text, meals). meals is None if the reply wasn't valid JSON."""
    response = st.session_state.chat.send_message(parts)
    if isinstance(response.parsed, MacroReply):
        return response.parsed.reply, [meal.model_dump() for meal in response.parsed.meals]
    return response.text, None


def meal_totals(meals):
    return {key: sum(meal[key] for meal in meals) for key in DAILY_GOALS}


def normalize_number(raw):
    """'+91 98765-43210' -> '+919876543210'; None if it isn't +countrycode digits."""
    number = re.sub(r"[\s()-]", "", raw)
    return number if re.fullmatch(r"\+\d{8,15}", number) else None


def clean_whatsapp_text(text):
    # WhatsApp template variables can't contain newlines or tabs.
    if not text:
        return "No nutrition summary available."
    text = " ".join(text.split())
    return text[:1500] + "..." if len(text) > 1500 else text


def send_whatsapp(to_number, user_name, summary):
    """Raises on failure.

    With a Content Template (HX... SID, paid accounts) the message works any time:
    {{1}} = name, {{2}} = summary. Without one (free trial) it's plain text, which
    WhatsApp only delivers within 24h of the user's last message to the sandbox.
    """
    if TWILIO_CONTENT_SID.startswith("HX"):
        content = {
            "content_sid": TWILIO_CONTENT_SID,
            "content_variables": json.dumps(
                {"1": user_name, "2": clean_whatsapp_text(summary)}, ensure_ascii=False
            ),
        }
    else:
        content = {"body": summary_message(user_name, summary)}
    twilio_client.messages.create(from_=TWILIO_WHATSAPP_FROM, to=f"whatsapp:{to_number}", **content)


def summary_message(user_name, summary):
    return f"Hi {user_name}, here's your MacroSnap summary:\n\n{(summary or '')[:1500]}"


def whatsapp_link(to_number, text):
    """wa.me click-to-chat link: opens WhatsApp with `text` prefilled, no Twilio needed."""
    return f"https://wa.me/{to_number.lstrip('+')}?text={quote(text)}"


# Step 1: onboarding
if "onboarded" not in st.session_state:
    ui.hero()
    with st.form("onboarding_form"):
        name = st.text_input("Your name")
        whatsapp_number = st.text_input(
            "WhatsApp number (with country code)",
            placeholder="+91XXXXXXXXXX",
            help="Use the number that joined the Twilio WhatsApp sandbox.",
        )
        submitted = st.form_submit_button("Let's go 🚀", type="primary", width="stretch")
    if submitted:
        number = normalize_number(whatsapp_number)
        if not name.strip() or not whatsapp_number.strip():
            st.warning("Please fill in both your name and WhatsApp number.")
        elif number is None:
            st.warning("Enter the number with its country code, e.g. +919876543210.")
        else:
            st.session_state.name = name.strip()
            st.session_state.whatsapp_number = number
            st.session_state.chat = gemini_client.chats.create(
                model=MODEL_NAME,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=MacroReply,
                ),
            )
            st.session_state.messages = []
            st.session_state.meals = []
            st.session_state.onboarded = True
            st.rerun()
    st.stop()

# Step 2: sidebar - profile, reset, tips
with st.sidebar:
    st.header(f"👋 Hi, {st.session_state.name}")
    st.caption(f"Summaries go to **{st.session_state.whatsapp_number}**")
    if st.button("🔄 Start over", width="stretch"):
        st.session_state.clear()
        st.rerun()
    st.divider()
    st.markdown(
        "**Tips for better estimates**\n"
        "- Shoot from above, in good light\n"
        "- Mention portions (\"2 rotis\", \"a big bowl\")\n"
        "- Correct me (\"it was 2 rotis, not 3\") - the rings update\n"
        "- Ask follow-ups like \"how much protein was that?\"\n\n"
        "**WhatsApp not arriving?** Send any message to the sandbox number "
        "on WhatsApp, then hit Send again (sandbox 24-hour rule)."
    )

# Step 3: header + dashboard. Both are filled at the end of the script so they
# reflect the message/meal this run just added.
header_col, button_col = st.columns([5, 2], vertical_alignment="center")
header_col.title("MacroSnap", anchor=False)
send_slot = button_col.empty()
dashboard_slot = st.container()

# Step 4: chat
if not st.session_state.messages:
    add_message("assistant", "text", WELCOME_MESSAGE_TEMPLATE.format(name=st.session_state.name))
else:
    for message in st.session_state.messages:
        render_message(message)

user_input = st.chat_input(
    "Ask a question, or attach a photo of your meal",
    accept_file=True,
    file_type=["jpg", "jpeg", "png"],
)

if user_input:
    photo = user_input.files[0] if user_input.files else None
    text = user_input.text
    parts = []

    if photo is not None:
        photo_bytes = photo.getvalue()
        add_message("user", "image", photo_bytes)
        parts.append(types.Part.from_bytes(data=photo_bytes, mime_type=photo.type))
    if text:
        add_message("user", "text", text)
        parts.append(text)
    elif photo is not None:
        parts.append("What is this meal? Give me the calories and macros.")

    with st.spinner("Crunching the numbers..."):
        try:
            answer, meals = ask_gemini(parts)
        except Exception as error:
            answer, meals = f"Sorry, something went wrong: {error}", None
    if meals is not None:
        st.session_state.meals = meals
    add_message("assistant", "text", answer or "Hmm, I couldn't read that one - try rephrasing?")

with dashboard_slot:
    ui.macro_dashboard(meal_totals(st.session_state.meals), DAILY_GOALS, st.session_state.meals)

# Step 5: WhatsApp summary (disabled until there's a real exchange, not just the welcome)
if send_slot.button(
    "📤 Send to WhatsApp",
    type="primary",
    disabled=len(st.session_state.messages) <= 2,
    width="stretch",
):
    name, number = st.session_state.name, st.session_state.whatsapp_number
    with st.spinner("Summarizing your day..."):
        try:
            summary, _ = ask_gemini([SUMMARY_REQUEST_PROMPT])
        except Exception as error:
            summary = None
            st.error(f"Couldn't create the summary: {error}")
    if summary:
        try:
            send_whatsapp(number, name, summary)
            st.toast("Sent! Check your WhatsApp 📲", icon="✅")
        except Exception as error:
            # Twilio trial accounts only reach verified numbers that joined the sandbox,
            # so anyone else (e.g. a reviewer) gets the same summary as a one-tap link.
            st.warning(
                "Twilio couldn't deliver this one (free-trial accounts can only message "
                "verified numbers). Tap below to send the summary to yourself on WhatsApp."
            )
            st.link_button("💬 Open in WhatsApp", whatsapp_link(number, summary_message(name, summary)), type="primary")
            st.caption(f"Twilio said: {error}")
