import os
import re
import json
import time
import uuid
import datetime
from typing import Dict, Any, List, Optional

import streamlit as st
import openai
from dotenv import load_dotenv

# Google Sheets API
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# =========================
# Setup
# =========================
load_dotenv()
st.set_page_config(page_title="Elite Auto Sales Academy Bot", page_icon="🤖", layout="centered")

OPENAI_MODEL = os.getenv("AGBOT_MODEL", "gpt-4o")
openai.api_key = os.getenv("OPENAI_API_KEY", "")

# =========================
# CHARACTER (Master Build Doc – Updated)
# =========================
CHARACTER = """
You are the Elite Auto Sales Academy Bot (powered by AG Goldsmith).  
Your role: dealer-floor training assistant.  
Tone: natural and professional, sharp and concise. Use short lines, clean authority, no fluff. Mass-friendly dealership talk — no slang, no corporate jargon. End each turn with a clear respectful next step.  

Core Framework: the M3 Pillars  
• Message Mastery → Scripts, trust-building, tonality, first impressions.  
• Closer Moves → Objection handling, PVF close, roleplays.  
• Money Momentum → Daily log, E.A.R.N. system, follow-up habits.  

Supporting Frameworks:  
• Signature Close: Pain–Vision–Fit (PVF).  
• Five Emotional Checkpoints: Research Mode, Trust Check, Control Test, Reassurance Loop, Post-Test Drift.  

---  
COMMAND LIBRARY (respond only to these triggers):  

Message Mastery  
• !scripts → Provide standard sales scripts.  
• !trust → Tips + roleplay on trust-building.  
• !tonality → Coaching on voice tone + delivery.  
• !firstimpression → Training lines for greetings + openings.  

Closer Moves  
• !pvf → Walkthrough of Pain–Vision–Fit close.  
• !objection <type> → Objection handling by category. Supported types: price, paymenttoohigh, tradevalue, thinkaboutit, shoparound, spouse, paymentvsprice, timingstall.  
• !roleplay price → Role-play price objection scenario.  
• !roleplay trade → Role-play trade-in objection scenario.  

Money Momentum  
• !dailylog → Ask 4 prompts in order (ups, calls, follow-ups, appointments). After responses, append one row to Google Sheet (Date | User | Ups | Calls | FollowUps | Appointments). Return summary message with numbers + one encouragement line + one tip.  
• !earn → Explain the E.A.R.N. system (exact lines provided by admin).  

Five Emotional Checkpoints  
• !checkpoints → Return the five checkpoints (Research Mode, Trust Check, Control Test, Reassurance Loop, Post-Test Drift).  

---  
ROLEPLAY RULES  
• Default length 5–6 turns.  
• Each objection roleplay branches based on numbers:  
   - Base → empathy + discovery + one clean commitment.  
   - Slightly over target → anchor value → calm choice → split difference.  
   - Far apart → reset expectations (model norms), test levers (term/down/selection), coach customer up.  
• Capture numbers: when user gives target/offer, parse and store. Branch by delta.  
• Controls: continue (+2–4 steps), end (clear session), restart (step = 1). Stop at max 10 steps.  
• If user types without “!”, reply: “Looks like you meant ![command]. Try it with the exclamation point.”  

---  
DAILY LOG PROMPTS  
1) “How many ups did you take today?”  
2) “How many calls did you make?”  
3) “How many follow-ups did you complete?”  
4) “How many appointments did you set?”  

Close-out:  
“Logged. Great work today! You logged [X ups, Y calls, Z follow-ups, A appointments]. Keep stacking clean reps. [Encouragement] Tip: [Tip]”  
Where [Encouragement] is randomly chosen from the Encouragement list and [Tip] from the Tip Library.  

---  
FIRST IMPRESSION SCRIPT (for !firstimpression)  
Rep: “Welcome in! I’m [Name]. Are you looking at something specific today, or open to a few options?”  
Customer: “Just looking.”  
Rep: “Perfect. Let’s take a walk together, and you can tell me what matters most in your next car.”  

---  
TONE GUARD  
• Short, direct, mass-friendly dealership talk.  
• Replies ~2 sentences per turn.  
• Never invent outside lines. Use only the content from this prompt.  
"""
# =========================
# Google Sheets config
# =========================
DAILY_LOG_SPREADSHEET_ID   = os.getenv("DAILY_LOG_SPREADSHEET_ID", "").strip()
SESSION_LOG_SPREADSHEET_ID = os.getenv("SESSION_LOG_SPREADSHEET_ID", "").strip()
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def get_sheets_service():
    sa_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if sa_json:
        info = json.loads(sa_json)
        creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    else:
        path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
        if not path or not os.path.exists(path):
            raise RuntimeError("Google auth missing. Set GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_APPLICATION_CREDENTIALS.")
        creds = service_account.Credentials.from_service_account_file(path, scopes=SCOPES)
    return build("sheets", "v4", credentials=creds)

def add_sheet_if_missing(service, spreadsheet_id: str, sheet_title: str):
    try:
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": [{"addSheet": {"properties": {"title": sheet_title}}}]}
        ).execute()
    except HttpError as e:
        if e.resp.status in (400, 409):
            pass
        else:
            raise

def ensure_header_row(service, spreadsheet_id: str, sheet_title: str, headers: List[str]):
    try:
        res = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range=f"'{sheet_title}'!1:1"
        ).execute()
        row = res.get("values", [[]])
        cur = row[0] if row else []
        if cur != headers:
            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"'{sheet_title}'!1:1",
                valueInputOption="RAW",
                body={"values": [headers]}
            ).execute()
    except HttpError as e:
        if e.resp.status == 400:
            add_sheet_if_missing(service, spreadsheet_id, sheet_title)
            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"'{sheet_title}'!1:1",
                valueInputOption="RAW",
                body={"values": [headers]}
            ).execute()
        else:
            raise

def sanitize_sheet_title(name: str) -> str:
    n = (name or "session").strip()
    n = re.sub(r"[:\\\/\?\*\[\]]", "-", n)
    return n[:99] if len(n) > 99 else n or "session"

# Daily Log (idempotent by LogId user|YYYY-MM-DD)
DAILY_HEADERS = ["DateUTC","User","Ups","Calls","FollowUps","Appointments","LogId"]

def daily_log_append_or_update(user: str, ups: str, calls: str, followups: str, appointments: str) -> Dict[str, Any]:
    if not DAILY_LOG_SPREADSHEET_ID:
        return {"ok": False, "error": "DAILY_LOG_SPREADSHEET_ID not set"}
    service = get_sheets_service()
    sheet_title = "DailyLog"
    add_sheet_if_missing(service, DAILY_LOG_SPREADSHEET_ID, sheet_title)
    ensure_header_row(service, DAILY_LOG_SPREADSHEET_ID, sheet_title, DAILY_HEADERS)

    now_utc = datetime.datetime.utcnow().isoformat()
    log_id = f"{user}|{now_utc[:10]}".lower()

    try:
        existing = service.spreadsheets().values().get(
            spreadsheetId=DAILY_LOG_SPREADSHEET_ID,
            range=f"'{sheet_title}'!G2:G"
        ).execute().get("values", [])
    except HttpError:
        existing = []

    found_row_idx = None
    for i, row in enumerate(existing, start=2):
        val = (row[0] if row else "").strip().lower()
        if val == log_id:
            found_row_idx = i
            break

    row_values = [[now_utc, user, ups, calls, followups, appointments, log_id]]
    if found_row_idx:
        service.spreadsheets().values().update(
            spreadsheetId=DAILY_LOG_SPREADSHEET_ID,
            range=f"'{sheet_title}'!A{found_row_idx}:G{found_row_idx}",
            valueInputOption="RAW",
            body={"values": row_values}
        ).execute()
        return {"ok": True, "mode": "update", "row": found_row_idx}
    else:
        service.spreadsheets().values().append(
            spreadsheetId=DAILY_LOG_SPREADSHEET_ID,
            range=f"'{sheet_title}'!A1",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": row_values}
        ).execute()
        return {"ok": True, "mode": "append"}

# Per-session logs (one tab per session)
SESSION_HEADERS = ["TimestampUTC","UserName","SessionId","Scenario","Step","TargetPayment","OfferPayment","Band","Message"]

def session_log_append(session_id: str, user_name: str,
                       scenario: str, step: int, target_payment: Optional[int],
                       offer_payment: Optional[int], band: str, message: str) -> Dict[str, Any]:
    if not SESSION_LOG_SPREADSHEET_ID:
        return {"ok": False, "error": "SESSION_LOG_SPREADSHEET_ID not set"}
    service = get_sheets_service()
    tab = sanitize_sheet_title(session_id)
    add_sheet_if_missing(service, SESSION_LOG_SPREADSHEET_ID, tab)
    ensure_header_row(service, SESSION_LOG_SPREADSHEET_ID, tab, SESSION_HEADERS)

    now_utc = datetime.datetime.utcnow().isoformat()
    row = [[
        now_utc, user_name, session_id, scenario, step,
        target_payment if target_payment is not None else "",
        offer_payment if offer_payment is not None else "",
        band, message
    ]]
    service.spreadsheets().values().append(
        spreadsheetId=SESSION_LOG_SPREADSHEET_ID,
        range=f"'{tab}'!A1",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": row}
    ).execute()
    return {"ok": True, "sheet": tab}

# =========================
# Number helpers & roleplay
# =========================
SESSION_TTL = 30 * 60
NUM_RE = re.compile(r"(\d{2,5})")

def extract_int(text: str) -> Optional[int]:
    t = text.replace(",", "")
    m = NUM_RE.search(t)
    return int(m.group(1)) if m else None

def compute_band(target: Optional[int], offer: Optional[int]) -> str:
    if target is None or offer is None:
        return ""
    delta = offer - target
    if delta <= 0: return "A"
    if 1 <= delta <= 40: return "B"
    return "C"

def infer_scenario_from_text(txt: str) -> Optional[str]:
    t = txt.lower()
    if "!priceobjection" in t or "!roleplay price" in t: return "price"
    if "!paymenttoohigh" in t or "!roleplay payment" in t: return "payment"
    if "!tradevalue" in t or "!roleplay trade" in t: return "trade"
    if "!thinkaboutit" in t: return "think"
    if "!shoparound" in t: return "shop"
    if "!spouse" in t: return "spouse"
    if "!paymentvsprice" in t: return "paymentvsprice"
    if "!timingstall" in t: return "timing"
    if "!roleplay budget" in t or (t.startswith("!roleplay") and "budget" in t): return "budget"
    return None

# =========================
# OpenAI tools (function calling)
# =========================
OPENAI_FUNCTIONS = [
    {
        "name": "append_daily_log",
        "description": "Append exactly one row to the daily log Google Sheet after the four answers.",
        "parameters": {
            "type": "object",
            "properties": {
                "user": {"type": "string"},
                "ups": {"type": "string"},
                "calls": {"type": "string"},
                "followups": {"type": "string"},
                "appointments": {"type": "string"}
            },
            "required": ["user", "ups", "calls", "followups", "appointments"]
        }
    },
    {
        "name": "log_session_turn",
        "description": "Write one turn of the roleplay to the per-session sheet tab.",
        "parameters": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "user_name": {"type": "string"},
                "scenario": {"type": "string"},
                "step": {"type": "integer"},
                "target_payment": {"type": "integer"},
                "offer_payment": {"type": "integer"},
                "band": {"type": "string"},
                "message": {"type": "string"}
            },
            "required": ["session_id", "user_name", "scenario", "step", "band", "message"]
        }
    }
]

def call_openai(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    return openai.ChatCompletion.create(
        model=OPENAI_MODEL,
        messages=messages,
        functions=OPENAI_FUNCTIONS,
        function_call="auto",
        temperature=0.3
    )

# =========================
# First-run modal: user name + session id
# =========================
if "session_id" not in st.session_state:
    st.session_state.session_id = f"sess-{uuid.uuid4().hex[:10]}"
if "onboarded" not in st.session_state:
    st.session_state.onboarded = False
if "user_name" not in st.session_state:
    st.session_state.user_name = ""

def onboarding_modal():
    st.markdown("### Welcome to Elite Auto Sales Academy Bot")
    with st.form("onboard"):
        name = st.text_input("Your name (for logs)", value=st.session_state.user_name, max_chars=60)
        submitted = st.form_submit_button("Enter")
        if submitted:
            if name.strip():
                st.session_state.user_name = name.strip()
                st.session_state.onboarded = True
                st.success(f"Thanks, {st.session_state.user_name}. Session: {st.session_state.session_id}")
            else:
                st.error("Please enter your name to continue.")

if not st.session_state.onboarded:
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        onboarding_modal()
    st.stop()

# =========================
# Sidebar: Quick Commands
# =========================
with st.sidebar:
    st.subheader("AG Bot • Controls")
    st.caption(f"User: **{st.session_state.user_name}**")
    st.caption(f"Session: `{st.session_state.session_id}`")

    st.markdown("**Quick Commands**")
    quick = None
    for cmd in [
        # Message Mastery
        "!scripts",
        "!trust",
        "!tonality",
        "!firstimpression",

        # Closer Moves
        "!pvf",
        "!objection price",
        "!objection paymenttoohigh",
        "!objection tradevalue",
        "!objection thinkaboutit",
        "!objection shoparound",
        "!objection spouse",
        "!objection paymentvsprice",
        "!objection timingstall",
        "!roleplay price",
        "!roleplay trade",

        # Money Momentum
        "!dailylog",
        "!earn",

        # Five Emotional Checkpoints
        "!checkpoints",

        # Extra / challenges
        "!challenge"
    ]:
        if st.button(cmd, key=f"btn_{cmd}"):
            quick = cmd

    st.markdown("---")
    st.markdown("**Roleplay Controls**")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("continue"):
            quick = "continue"
    with c2:
        if st.button("end"):
            quick = "end"
    with c3:
        if st.button("restart"):
            quick = "restart"

    st.markdown("---")
    st.markdown("**Numbers Quick-Input**")
    target_text = st.text_input("Target (e.g., 'under 500')", value="")
    offer_number = st.text_input("Offer $ (e.g., 525)", value="")
    q1, q2 = st.columns(2)
    with q1:
        if st.button("Send Target"):
            if target_text.strip():
                quick = target_text.strip()
    with q2:
        if st.button("Send Offer"):
            if offer_number.strip():
                quick = f"we’re at {offer_number.strip()}"

# =========================
# Init chat state & engine state
# =========================
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": CHARACTER},
        {"role": "system", "content": f"User: {st.session_state.user_name}. Session: {st.session_state.session_id}."},
        {"role": "system", "content": "Short, natural dealership language. ~2 sentences per turn. End with a clear next step."}
    ]

if "engine_state" not in st.session_state:
    st.session_state.engine_state = {
        "scenario": "",
        "step": 0,
        "target": None,
        "offer": None,
        "band": "",
        "last_updated": time.time(),
    }

# =========================
# Render chat history
# =========================
for m in st.session_state.messages:
    if m["role"] == "assistant":
        with st.chat_message("assistant"):
            st.markdown(m["content"])
    elif m["role"] == "user":
        with st.chat_message("user"):
            st.markdown(m["content"])

# =========================
# Input (buttons win over text)
# =========================
user_text = st.chat_input("Type a command or message…")
to_send = quick or user_text
if not to_send:
    st.stop()

# =========================
# Local session handling
# =========================
state = st.session_state.engine_state
now = time.time()
if now - state.get("last_updated", now) > SESSION_TTL:
    state.update({"scenario": "", "step": 0, "target": None, "offer": None, "band": ""})

txt_lower = to_send.lower().strip()
scenario_cmd = infer_scenario_from_text(to_send)
if scenario_cmd:
    state["scenario"] = scenario_cmd
    state["step"] = 0

if txt_lower in ("continue", "end", "restart"):
    if txt_lower == "restart":
        state["step"] = 0
    elif txt_lower == "end":
        state.update({"scenario": "", "step": 0, "target": None, "offer": None, "band": ""})
else:
    # Offer capture
    if any(k in txt_lower for k in ["we’re at", "we're at"]) or txt_lower.startswith("$") or re.search(r"\b(at|=)\s*\$?\d+", txt_lower):
        offer = extract_int(to_send)
        if offer is not None:
            state["offer"] = offer
    # Target capture
    if any(k in txt_lower for k in ["under", "closer to", "around", "about", "target", "budget", "cap"]):
        target = extract_int(to_send)
        if target is not None:
            state["target"] = target

state["band"] = compute_band(state.get("target"), state.get("offer"))
state["last_updated"] = time.time()

# Push user message
st.session_state.messages.append({"role": "user", "content": to_send})
with st.chat_message("user"):
    st.markdown(to_send)

# =========================
# Build OpenAI messages
# =========================
system_state = {
    "user_name": st.session_state.user_name,
    "session_id": st.session_state.session_id,
    "scenario": state.get("scenario") or "",
    "step": int(state.get("step", 0)),
    "target_payment": state.get("target"),
    "offer_payment": state.get("offer"),
    "band": state.get("band"),
    "last_updated": datetime.datetime.utcnow().isoformat()
}

messages = (
    [{"role": "system", "content": CHARACTER},
     {"role": "system", "content": f"User: {st.session_state.user_name}. Session: {st.session_state.session_id}."},
     {"role": "system", "content": "Short, natural dealership language. ~2 sentences per turn. End with a clear next step."},
     {"role": "system", "content": f"SESSION_STATE_JSON={json.dumps(system_state)}"}]
    + [m for m in st.session_state.messages if m["role"] in ("user","assistant")]
)

# =========================
# Call OpenAI (non-streamed to support tool calls)
# =========================
def run_openai(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    return openai.ChatCompletion.create(
        model=OPENAI_MODEL,
        messages=messages,
        functions=OPENAI_FUNCTIONS,
        function_call="auto",
        temperature=0.3
    )

try:

    ai = run_openai(messages)
    msg = ai["choices"][0]["message"]

    # Tool calls
    if "function_call" in msg and msg["function_call"]:
        fn = msg["function_call"]["name"]
        args_json = msg["function_call"].get("arguments") or "{}"
        try:
            args = json.loads(args_json)
        except json.JSONDecodeError as e:
            st.error(f"JSON decode error: {e}\nArguments: {args_json}")
            args = {}
        except Exception as e:
            st.error(f"Unexpected error: {e}\nArguments: {args_json}")
            args = {}

        if fn == "append_daily_log":
            result = daily_log_append_or_update(
                user=args.get("user", st.session_state.user_name),
                ups=args.get("ups", ""),
                calls=args.get("calls", ""),
                followups=args.get("followups", ""),
                appointments=args.get("appointments", "")
            )
            messages.append(msg)
            messages.append({"role": "function", "name": "append_daily_log", "content": json.dumps(result)})
            ai = openai.ChatCompletion.create(model=OPENAI_MODEL, messages=messages, temperature=0.3)
            msg = ai["choices"][0]["message"]

        elif fn == "log_session_turn":
            _ = session_log_append(
                session_id=st.session_state.session_id,
                user_name=st.session_state.user_name,
                scenario=state.get("scenario",""),
                step=int(args.get("step", state.get("step", 0))),
                target_payment=args.get("target_payment", state.get("target")),
                offer_payment=args.get("offer_payment", state.get("offer")),
                band=args.get("band", state.get("band", "")),
                message=args.get("message", to_send)
            )
            messages.append(msg)
            messages.append({"role": "function", "name": "log_session_turn", "content": json.dumps({"ok": True})})
            ai = openai.ChatCompletion.create(model=OPENAI_MODEL, messages=messages, temperature=0.3)
            msg = ai["choices"][0]["message"]

    assistant_text = msg.get("content") or "Working on it…"

    # Increment step for roleplay
    if state.get("scenario"):
        state["step"] = min(int(state.get("step", 0)) + 1, 10)

    with st.chat_message("assistant"):
        st.markdown(assistant_text)
    st.session_state.messages.append({"role": "assistant", "content": assistant_text})

    # Best-effort per-turn session log
    try:
        _ = session_log_append(
            session_id=st.session_state.session_id,
            user_name=st.session_state.user_name,
            scenario=state.get("scenario",""),
            step=int(state.get("step", 0)),
            target_payment=state.get("target"),
            offer_payment=state.get("offer"),
            band=state.get("band",""),
            message=assistant_text
        )
    except Exception:
        pass

except Exception as e:
    with st.chat_message("assistant"):
        st.error(f"Error: {e}")
