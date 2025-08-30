import os
import streamlit as st
import openai
from dotenv import load_dotenv

# -----------------------------
# Setup
# -----------------------------
load_dotenv()
st.set_page_config(page_title="AG Bot (Dealer-Floor)", page_icon="🤖", layout="centered")

# -----------------------------
# Character / System Prompt
# -----------------------------
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



# -----------------------------
# Sidebar: API key + Quick Cmds
# -----------------------------
with st.sidebar:
    st.subheader("AG Bot • Controls")
    api_key = os.getenv("OPENAI_API_KEY", "")
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key
        openai.api_key = api_key
    else:
        openai.api_key = os.getenv("OPENAI_API_KEY", "")

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



# -----------------------------
# Init chat state
# -----------------------------
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": CHARACTER}]

# -----------------------------
# Render chat history
# -----------------------------
for m in st.session_state.messages:
    if m["role"] == "assistant":
        with st.chat_message("assistant"):
            st.markdown(m["content"])
    elif m["role"] == "user":
        with st.chat_message("user"):
            st.markdown(m["content"])

# -----------------------------
# Input (buttons win over text)
# -----------------------------
user_text = st.chat_input("Type a command or message…")
to_send = quick or user_text
if not to_send:
    st.stop()

# push user message
st.session_state.messages.append({"role": "user", "content": to_send})
with st.chat_message("user"):
    st.markdown(to_send)

# -----------------------------
# Send to OpenAI (streamed)
# -----------------------------
try:
    with st.chat_message("assistant"):
        box = st.empty()
        acc = ""
        # Using Chat Completions with streaming to preserve your original behavior
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=st.session_state.messages,
            stream=True
        )
        for chunk in response:
            piece = chunk["choices"][0]["delta"].get("content", "")
            if piece:
                acc += piece
                box.markdown(acc)
        st.session_state.messages.append({"role": "assistant", "content": acc})
except Exception as e:
    with st.chat_message("assistant"):
        st.error(f"Error: {e}")
