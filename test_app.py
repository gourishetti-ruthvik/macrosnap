"""Smoke check, sends nothing real: venv\\Scripts\\python test_app.py"""
import json
from types import SimpleNamespace

from streamlit.testing.v1 import AppTest

from prompts import MacroReply, Meal

SECRETS = ["GEMINI_API_KEY", "TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_WHATSAPP_FROM", "TWILIO_CONTENT_SID"]


def new_app():
    at = AppTest.from_file("app.py", default_timeout=30)
    for key in SECRETS:
        at.secrets[key] = "test"
    return at.run()


at = new_app()
assert not at.exception, at.exception

# Onboarding rejects a number without a country code...
at.text_input[0].input("Asha")
at.text_input[1].input("98765 43210")
at.button[0].click().run()
assert "country code" in at.warning[0].value

# ...and normalizes a valid one, then lands in the chat with the welcome message.
at.text_input[1].input("+91 98765-43210")
at.button[0].click().run()
assert not at.exception, at.exception
assert at.session_state.whatsapp_number == "+919876543210"
assert "Hey Asha" in at.chat_message[0].markdown[0].value

# Dashboard totals add up the meals Gemini reported.
at.session_state.meals = [
    {"name": "Poha", "calories": 300, "protein_g": 6, "carbs_g": 50, "fat_g": 8},
    {"name": "Chai", "calories": 120, "protein_g": 3, "carbs_g": 18, "fat_g": 4},
]
at.run()
assert not at.exception, at.exception
dashboard = json.loads(at.get("bidi_component")[0].proto.json)
assert dashboard["totals"] == {"calories": 420, "protein_g": 9, "carbs_g": 68, "fat_g": 12}, dashboard

# WhatsApp button stays disabled until a real exchange happens.
assert next(b for b in at.button if "WhatsApp" in b.label).disabled


# A chat turn shows Gemini's reply text (not raw JSON) and updates the meals.
# Regression: a schema class defined inside app.py is re-created on every rerun,
# so isinstance() against the chat's original schema failed.
class FakeChat:
    def send_message(self, parts):
        meal = Meal(name="Idli", calories=150, protein_g=4, carbs_g=30, fat_g=1)
        return SimpleNamespace(parsed=MacroReply(reply="About 150 kcal.", meals=[meal]), text="{json}")


at.session_state.chat = FakeChat()
at.chat_input[0].set_value("2 idlis").run()
assert not at.exception, at.exception
assert at.chat_message[-1].markdown[0].value == "About 150 kcal.", at.chat_message[-1].markdown[0].value
assert at.session_state.meals[0]["name"] == "Idli"
send = next(b for b in at.button if "WhatsApp" in b.label)
assert not send.disabled

# Twilio refuses (fake creds here; an unverified reviewer number on a trial account in real
# life), so the app falls back to a wa.me link with the summary prefilled.
send.click().run()
assert not at.exception, at.exception
link = at.get("link_button")[0].proto.url
assert link.startswith("https://wa.me/919876543210?text=Hi%20Asha"), link
assert "About%20150%20kcal." in link, link

print("OK")
