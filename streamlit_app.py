# app.py
import os
import re
import json
import time
import uuid
import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv
import openai

# Google Sheets API
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import google.auth.transport.requests

# =========================
# Setup
# =========================
load_dotenv()
st.set_page_config(page_title="Elite Auto Sales Academy", page_icon="🤖", layout="wide")

# Hide Streamlit chrome — UI is entirely your index.html
st.markdown("""
<style>
#MainMenu, header, footer, .stDeployButton, .stToolbar, .stDecoration, #stDecoration {display:none;}
.main .block-container {padding-top:0; padding-bottom:0; max-width:100%;}
div[data-testid="stSidebar"] {display:none;}
</style>
""", unsafe_allow_html=True)

OPENAI_MODEL = os.getenv("AGBOT_MODEL", "gpt-4o")
openai.api_key = os.getenv("OPENAI_API_KEY", "")
root_dir = os.path.dirname(os.path.abspath(__file__))
COMPONENT_DIR = os.path.join(root_dir, "frontend/build")



# =========================
# CHARACTER (Master Build Doc – Updated)
# =========================
CHARACTER = """
You are the Elite Auto Sales Academy Bot (Sales Coach AI), powered by AG Goldsmith.  
Your role: dealer-floor training assistant.  
Tone: professional, confident, short, natural dealership language. No slang. No corporate trainer talk.  
Replies should be concise (1–2 sentences per turn), scannable, and end with a clear next step.  
Branding: Elite colors (Blue #0D3B66, Gold #FFD700). Identity always references “Elite Auto Sales Academy Bot, powered by AG Goldsmith.”

CORE FRAMEWORK (M3):
- Message Mastery → scripts, trust-building, tonality, first impressions.  
- Closer Moves → objections, PVF close, roleplays.  
- Money Momentum → daily log, E.A.R.N. system, follow-up habits.  

SUPPORTING FRAMEWORKS:  
- PVF Close: Pain → Vision → Fit → Close.  
- Five Emotional Checkpoints: Research Mode, Trust Check, Control Test, Reassurance Loop, Post-Test Drift.  

COMMAND RULES:
- Commands are case-insensitive.  
- If a user types a known command without "!", reply once: “Looks like you meant ![command]. Try it with the exclamation point.”  
- Normalize commands: strip whitespace, convert spaces to hyphens.  
- Aliases must work:  
  • !coaching-tips (aliases: !coachingtips, !coaching tips)  
  • !coaching-roleplay (aliases: !coachingroleplay, !coaching roleplay)  

COMMAND INDEX:
Message Mastery  
- !scripts → Show script library (Greeting, Discovery, Test Drive, Numbers, Closing, Follow-up). Compact menu first, drill-down allowed.  
- !trust → Coaching on building trust.  
- !tonality → Coaching on voice and pace.  
- !firstimpression → Greeting / intro roleplay.  

Closer Moves  
- !pvf → PVF guided close (Pain, Vision, Fit, Close).  
- !objection price → General price objection flow.  
- !objection paymenttoohigh → Specific monthly payment objection flow.  
- !objection tradevalue → Trade value objection flow.  
- !objection thinkaboutit → “I need to think about it.”  
- !objection shoparound → “I want to shop around.”  
- !objection spouse → “I need to check with my spouse.”  
- !objection paymentvsprice → Payment vs. total price objection.  
- !objection timingstall → Timing stall objection.  

Role-Play Scenarios  
- !roleplay price, !roleplay trade, !roleplay think, !roleplay shop, !roleplay spouse → Run multi-branch objection simulations (3-deep).  
Each roleplay: 2–3 branching responses max, short lines.  

Money Momentum  
- !dailylog → Sequentially ask:  
  1) How many ups did you take today?  
  2) How many calls did you make?  
  3) How many follow-ups did you complete?  
  4) How many appointments did you set? 
Append one row to Google Sheets (timestamp, user_name, ups, calls, followups, appointments, hardest_objection, notes).  
After logging, return: “Logged. Keep stacking clean reps. [Encouragement] Tip: [Tip]”  
where [Encouragement] = random encouragement line, [Tip] = random tip from library.  
- !earn → Overview of the E.A.R.N. system with one actionable prompt per step.  

Five Emotional Checkpoints  
- !checkpoints → Show five checkpoints. Allow drill-down. Some checkpoints include coaching, others include roleplays.  

Coaching Resources  
- !coaching → Menu of coaching options (tips, roleplay, trust, tonality, firstimpression).  
- !coaching-tips → Quick coaching lines (trust first, tonality calm, one ask, clean choices, protect value).  
- !coaching-roleplay → Roleplay starters (payment too high, think about it, trade pushback).  

Help  
- !help or !commands → List all available commands with usage examples.  

SESSION & STATE MANAGEMENT:
- Track per user: user_id, session_id, scenario, step, target_payment, offer_payment, last_updated.  
- Session expires if idle > 30 min.  
- Roleplays: default 6 steps, max 10. Controls: “continue”, “restart”, “end.”  
- Parse numbers (e.g. $450) for payment handling.  
- Branch by delta:  
  • Band A (on/under): close cleanly.  
  • Band B (slightly over: +1–40): anchor value → calm choice → split difference.  
  • Band C (far apart: >40): reset expectations, test levers, coach up.  

ERROR HANDLING:  
- If unknown input: “Not sure what you meant. Try a command like !pvf, !roleplay price, or !dailylog.”  
- If expected number not found: “What monthly number keeps you comfortable?”  
- If slow: send “Working on it…” then follow with final.  

TONE GUARD:  
- Replies are natural dealership-floor talk.  
- Short, mass-friendly, no jargon.  
- End with a respectful next step.  

ACCEPTANCE:  
- Commands trigger reliably.  
- Roleplays branch correctly.  
- Daily log appends one row.  
- Coaching commands return correct content.  
- Admin can edit this CHARACTER file to update content without rebuilding backend.  
"""



# =========================
# Google Sheets config
# =========================
DAILY_LOG_SPREADSHEET_ID = os.getenv("DAILY_LOG_SPREADSHEET_ID", "")
SESSION_LOG_SPREADSHEET_ID = os.getenv("SESSION_LOG_SPREADSHEET_ID", "")
print(f"Daily log sheet: {DAILY_LOG_SPREADSHEET_ID}, Session log sheet: {SESSION_LOG_SPREADSHEET_ID}")
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file"
]
# Get the service account JSON from environment variable
SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
if SERVICE_ACCOUNT_JSON and not SERVICE_ACCOUNT_JSON.startswith("{"):
    # If it's not already a JSON string but a file path
    try:
        with open(SERVICE_ACCOUNT_JSON, 'r') as f:
            SERVICE_ACCOUNT_JSON = f.read()
    except Exception as e:
        print(f"Warning: Could not read service account file at {SERVICE_ACCOUNT_JSON}: {e}")

def get_sheets_service():
    """Create and return a Google Sheets API service."""
    try:
        # First, try to use the service_account.json file directly
        service_account_path = os.path.join(os.path.dirname(__file__), 'service_account.json')
        if os.path.exists(service_account_path):
            try:
                print(f"Found service_account.json file, using it for authentication")
                
                # Verify the contents of the JSON file
                import json
                try:
                    with open(service_account_path, 'r') as f:
                        service_account_info = json.load(f)
                    
                    # Check for required fields
                    required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
                    missing_fields = [field for field in required_fields if field not in service_account_info]
                    
                    if missing_fields:
                        print(f"WARNING: Service account JSON file is missing these required fields: {missing_fields}")
                    else:
                        print(f"Service account JSON file contains all required fields")
                        print(f"Project ID: {service_account_info.get('project_id')}")
                        print(f"Client Email: {service_account_info.get('client_email')}")
                except Exception as e:
                    print(f"Error reading service_account.json: {e}")
                
                # Create credentials from the service account file with explicit token URI
                credentials = service_account.Credentials.from_service_account_file(
                    service_account_path, 
                    scopes=SCOPES
                )
                
                # Force token refresh to get access token
                try:
                    credentials.refresh(google.auth.transport.requests.Request())
                    print("Successfully refreshed access token")
                except Exception as e:
                    print(f"Error refreshing token: {e}")
                
                # Print the service account email for debugging/setup purposes
                if hasattr(credentials, 'service_account_email'):
                    print(f"Using service account: {credentials.service_account_email}")
                    print(f"Make sure to share your Google Sheets with this email address")
                
                service = build("sheets", "v4", credentials=credentials)
                print("Successfully created Google Sheets service using service_account.json")
                
                # Test access to spreadsheets if they're configured
                if DAILY_LOG_SPREADSHEET_ID:
                    try:
                        service.spreadsheets().get(spreadsheetId=DAILY_LOG_SPREADSHEET_ID).execute()
                        print(f"Test access successful for daily log spreadsheet")
                    except Exception as e:
                        print(f"⚠️ Cannot access daily log spreadsheet: {e}")
                        print("Make sure you've shared the spreadsheet with the service account email")
                
                if SESSION_LOG_SPREADSHEET_ID:
                    try:
                        service.spreadsheets().get(spreadsheetId=SESSION_LOG_SPREADSHEET_ID).execute()
                        print(f"Test access successful for session log spreadsheet")
                    except Exception as e:
                        print(f"⚠️ Cannot access session log spreadsheet: {e}")
                        print("Make sure you've shared the spreadsheet with the service account email")
                
                return service
            except Exception as e:
                print(f"Error using service_account.json file: {e}")
        
        # Fall back to GOOGLE_SERVICE_ACCOUNT_JSON environment variable
        elif SERVICE_ACCOUNT_JSON:
            try:
                # Try to parse as JSON
                import json
                info_dict = json.loads(SERVICE_ACCOUNT_JSON)
                credentials = service_account.Credentials.from_service_account_info(
                    info_dict, 
                    scopes=SCOPES
                )
                
                # Print the service account email for debugging
                if hasattr(credentials, 'service_account_email'):
                    print(f"Using service account from env var: {credentials.service_account_email}")
                
                service = build("sheets", "v4", credentials=credentials)
                print("Using credentials from GOOGLE_SERVICE_ACCOUNT_JSON environment variable")
                return service
            except Exception as e:
                print(f"Error using GOOGLE_SERVICE_ACCOUNT_JSON: {e}")
        
        # Last resort - try credentials.json
        creds_file = os.path.join(os.path.dirname(__file__), 'credentials.json')
        if os.path.exists(creds_file):
            try:
                credentials = service_account.Credentials.from_service_account_file(
                    creds_file, 
                    scopes=SCOPES
                )
                service = build("sheets", "v4", credentials=credentials)
                print(f"Using credentials file: {creds_file}")
                return service
            except Exception as e:
                print(f"Error using credentials.json file: {e}")
        
        # No credentials found
        print("No Google Sheets credentials found. Functionality will be limited.")
        print("Please set GOOGLE_SERVICE_ACCOUNT_JSON in your .env file or place a credentials.json file in the project directory")
        return None
    except Exception as e:
        print(f"Error initializing Google Sheets service: {e}")
        return None

def add_sheet_if_missing(service, spreadsheet_id: str, sheet_title: str):
    """Create a sheet if it doesn't exist already."""
    if not service or not spreadsheet_id:
        print("Cannot add sheet: service or spreadsheet_id missing")
        return False
        
    try:
        # First check if the sheet already exists
        try:
            sheets_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            sheets = sheets_metadata.get('sheets', [])
            for sheet in sheets:
                if sheet.get('properties', {}).get('title') == sheet_title:
                    print(f"Sheet '{sheet_title}' already exists")
                    return True
        except Exception as e:
            print(f"Error checking existing sheets: {e}")
            # Continue to creation attempt
        
        # Sheet doesn't exist, try to create it
        print(f"Creating new sheet '{sheet_title}'")
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": [{"addSheet": {"properties": {"title": sheet_title}}}]}
        ).execute()
        print(f"Successfully created sheet '{sheet_title}'")
        return True
        
    except HttpError as e:
        if getattr(e, "resp", None) and e.resp.status in (400, 409):
            # 400 or 409 usually means the sheet already exists
            print(f"Sheet '{sheet_title}' may already exist: {e.reason if hasattr(e, 'reason') else e}")
            return True
        else:
            # Other HTTP errors - likely permissions or invalid spreadsheet ID
            error_details = e.content.decode('utf-8') if hasattr(e, 'content') else str(e)
            status_code = e.resp.status if hasattr(e, 'resp') and hasattr(e.resp, 'status') else 'unknown'
            print(f"HTTP error {status_code} adding sheet: {error_details}")
            
            if status_code == 403:
                print("PERMISSION DENIED: Make sure your service account email has Editor access to the spreadsheet")
            
            raise
    except Exception as e:
        print(f"Error adding sheet '{sheet_title}': {e}")
        raise

def ensure_header_row(service, spreadsheet_id: str, sheet_title: str, headers: List[str]):
    """Make sure the first row of the sheet has the correct headers."""
    if not service or not spreadsheet_id:
        print("Cannot ensure header row: service or spreadsheet_id missing")
        return False
        
    try:
        # Try to get the current header row
        try:
            res = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id, range=f"'{sheet_title}'!1:1"
            ).execute()
            row = res.get("values", [[]])
            cur = row[0] if row else []
            
            # Update headers if they don't match
            if cur != headers:
                print(f"Updating headers in '{sheet_title}': {headers}")
                service.spreadsheets().values().update(
                    spreadsheetId=spreadsheet_id,
                    range=f"'{sheet_title}'!1:1",
                    valueInputOption="RAW",
                    body={"values": [headers]}
                ).execute()
                return True
            return True
                
        except HttpError as e:
            if getattr(e, "resp", None) and e.resp.status == 400:
                # Sheet likely doesn't exist, try to create it
                print(f"Sheet '{sheet_title}' not found, creating it")
                sheet_created = add_sheet_if_missing(service, spreadsheet_id, sheet_title)
                
                if sheet_created:
                    # Now try to add headers
                    try:
                        print(f"Adding headers to new sheet '{sheet_title}'")
                        service.spreadsheets().values().update(
                            spreadsheetId=spreadsheet_id,
                            range=f"'{sheet_title}'!1:1",
                            valueInputOption="RAW",
                            body={"values": [headers]}
                        ).execute()
                        return True
                    except Exception as header_error:
                        print(f"Error adding headers to new sheet: {header_error}")
                        raise
            else:
                # Other HTTP error
                error_details = e.content.decode('utf-8') if hasattr(e, 'content') else str(e)
                print(f"HTTP error getting/setting headers: {error_details}")
                raise
                
    except Exception as e:
        print(f"Error ensuring header row for '{sheet_title}': {e}")
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
    
    try:
        service = get_sheets_service()
        if service is None:
            return {"ok": False, "error": "Failed to initialize Google Sheets service"}
            
        sheet_title = "DailyLog"
        
        # Set up the sheet if needed
        try:
            add_sheet_if_missing(service, DAILY_LOG_SPREADSHEET_ID, sheet_title)
            ensure_header_row(service, DAILY_LOG_SPREADSHEET_ID, sheet_title, DAILY_HEADERS)
        except Exception as e:
            print(f"Error setting up sheet: {e}")
            return {"ok": False, "error": f"Error setting up sheet: {str(e)}"}
            
        now_utc = datetime.datetime.utcnow().isoformat()
        log_id = f"{user}|{now_utc[:10]}".lower()
    
        # Get existing values
        try:
            existing = service.spreadsheets().values().get(
                spreadsheetId=DAILY_LOG_SPREADSHEET_ID,
                range=f"'{sheet_title}'!G2:G"
            ).execute().get("values", [])
        except HttpError as e:
            print(f"Error getting existing values: {e}")
            existing = []
    
        # Look for existing entry
        found_row_idx = None
        for i, row in enumerate(existing, start=2):
            val = (row[0] if row else "").strip().lower()
            if val == log_id:
                found_row_idx = i
                break
    
        # Prepare data row
        row_values = [[now_utc, user, ups, calls, followups, appointments, log_id]]
        
        # Update or append
        if found_row_idx:
            try:
                service.spreadsheets().values().update(
                    spreadsheetId=DAILY_LOG_SPREADSHEET_ID,
                    range=f"'{sheet_title}'!A{found_row_idx}:G{found_row_idx}",
                    valueInputOption="RAW",
                    body={"values": row_values}
                ).execute()
                return {"ok": True, "mode": "update", "row": found_row_idx}
            except Exception as e:
                print(f"Error updating row: {e}")
                return {"ok": False, "error": f"Error updating row: {str(e)}"}
        else:
            try:
                service.spreadsheets().values().append(
                    spreadsheetId=DAILY_LOG_SPREADSHEET_ID,
                    range=f"'{sheet_title}'!A1",
                    valueInputOption="RAW",
                    insertDataOption="INSERT_ROWS",
                    body={"values": row_values}
                ).execute()
                return {"ok": True, "mode": "append"}
            except Exception as e:
                print(f"Error appending row: {e}")
                return {"ok": False, "error": f"Error appending row: {str(e)}"}
    except Exception as e:
        print(f"Unexpected error in daily_log_append_or_update: {e}")
        return {"ok": False, "error": f"Unexpected error: {str(e)}"}

# Per-session logs (one tab per session)
SESSION_HEADERS = ["TimestampUTC","UserName","SessionId","Scenario","Step","TargetPayment","OfferPayment","Band","Message"]

def session_log_append(session_id: str, user_name: str,
                       scenario: str, step: int, target_payment: Optional[int],
                       offer_payment: Optional[int], band: str, message: str) -> Dict[str, Any]:
    if not SESSION_LOG_SPREADSHEET_ID:
        return {"ok": False, "error": "SESSION_LOG_SPREADSHEET_ID not set"}
    
    try:
        service = get_sheets_service()
        if service is None:
            return {"ok": False, "error": "Failed to initialize Google Sheets service"}
            
        tab = sanitize_sheet_title(session_id)
        
        try:
            add_sheet_if_missing(service, SESSION_LOG_SPREADSHEET_ID, tab)
            ensure_header_row(service, SESSION_LOG_SPREADSHEET_ID, tab, SESSION_HEADERS)
        except Exception as e:
            print(f"Error setting up sheet: {e}")
            return {"ok": False, "error": f"Error setting up sheet: {str(e)}"}
    
        now_utc = datetime.datetime.utcnow().isoformat()
        row = [[
            now_utc, user_name, session_id, scenario, step,
            target_payment if target_payment is not None else "",
            offer_payment if offer_payment is not None else "",
            band, message
        ]]
        
        try:
            service.spreadsheets().values().append(
                spreadsheetId=SESSION_LOG_SPREADSHEET_ID,
                range=f"'{tab}'!A1",
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body={"values": row}
            ).execute()
            return {"ok": True, "sheet": tab}
        except Exception as e:
            print(f"Error appending data: {e}")
            return {"ok": False, "error": f"Error appending data: {str(e)}"}
            
    except Exception as e:
        print(f"Unexpected error in session_log_append: {e}")
        return {"ok": False, "error": f"Unexpected error: {str(e)}"}

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

def run_openai(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    try:
        print(f"Running OpenAI with model: {OPENAI_MODEL}")
        print("Messages summary:")
        for msg in messages[:5]:  # Print first 5 messages for debugging
            print(f"   - {msg['role']}")
            
        response = openai.ChatCompletion.create(
            model=OPENAI_MODEL,
            messages=messages,
            functions=OPENAI_FUNCTIONS,
            function_call="auto",
            temperature=0.3
        )
        print("OpenAI API call successful")
        return response
    except Exception as e:
        print(f"OpenAI API call failed: {str(e)}")
        print(f"Error response: {e.__dict__ if hasattr(e, '__dict__') else 'No details available'}")
        # Return a fallback response
        return {
            "choices": [
                {
                    "message": {
                        "content": f"Sorry, I encountered an error: {str(e)}. Please try again or contact support."
                    }
                }
            ]
        }

# =========================
# Message history management
# =========================
def truncate_messages(messages: List[Dict[str, str]], max_messages: int = 10) -> List[Dict[str, str]]:
    """Truncate message history to avoid context length issues."""
    # Always keep system messages and the last max_messages non-system messages
    system_messages = [msg for msg in messages if msg['role'] == 'system']
    non_system_messages = [msg for msg in messages if msg['role'] != 'system']
    
    # Keep only the most recent non-system messages
    if len(non_system_messages) > max_messages:
        print(f"Truncating message history from {len(non_system_messages)} to {max_messages} messages")
        non_system_messages = non_system_messages[-max_messages:]
    
    # Combine and return
    return system_messages + non_system_messages

# =========================
# Session defaults for the engine
# =========================
if "session_id" not in st.session_state:
    st.session_state.session_id = f"sess-{uuid.uuid4().hex[:10]}"
if "user_name" not in st.session_state:
    st.session_state.user_name = "User"
if "app_version" not in st.session_state:
    st.session_state.app_version = "1.0.1"  # Track version for debugging

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Welcome to Elite Auto Sales Academy. Use the commands from the sidebar (e.g., !scripts) or type your message below."}
    ]
else:
    # Cleanup message history to prevent it from growing too large
    if len(st.session_state.messages) > 30:  # Keep only the last 30 messages
        st.session_state.messages = st.session_state.messages[-30:]
        print("Message history cleanup executed. Keeping the last 30 messages.")
if "conversations" not in st.session_state:
    st.session_state.conversations = {}
if "engine_state" not in st.session_state:
    st.session_state.engine_state = {
        "scenario": "",
        "step": 0,
        "target": None,
        "offer": None,
        "band": "",
        "last_updated": time.time(),
    }
if "component_errors" not in st.session_state:
    st.session_state.component_errors = []  # Track component errors for debugging
if "needs_rerun" not in st.session_state:
    st.session_state.needs_rerun = False  # Flag to control safe reruns

# =========================
# Core responder (text -> OpenAI -> tool-calls -> reply)
# =========================
def respond_to(text: str) -> str:
    state = st.session_state.engine_state

    # TTL reset
    now = time.time()
    if now - state.get("last_updated", now) > SESSION_TTL:
        state.update({"scenario": "", "step": 0, "target": None, "offer": None, "band": ""})


    # --- Command normalization ---
    txt = text.strip()
    txt_lower = txt.lower()
    # Known command patterns (add more as needed)
    known_commands = {
        '!coaching': ['!coaching'],
        '!coaching-tips': ['!coaching-tips', '!coachingtips'],
        '!coaching-roleplay': ['!coaching-roleplay', '!coachingroleplay'],
        '!help': ['!help', '!commands'],
        '!objection price': ['!objection price'],
        '!objection paymenttoohigh': ['!objection paymenttoohigh'],
    }
    # Normalize spaces to hyphens for coaching commands and aliases
    for canonical, aliases in known_commands.items():
        for alias in aliases:
            if txt_lower.replace(' ', '-') == alias:
                txt_lower = canonical
                break

    # Trim, lower, and convert spaces to hyphens for known patterns
    if txt_lower.startswith('!coaching '):
        txt_lower = '!coaching-' + txt_lower.split(' ', 1)[1].replace(' ', '-')
    if txt_lower in ('!coachingtips', '!coaching-tips'):
        txt_lower = '!coaching-tips'
    if txt_lower in ('!coachingroleplay', '!coaching-roleplay'):
        txt_lower = '!coaching-roleplay'

    # --- Command handlers ---
    scenario_cmd = infer_scenario_from_text(txt_lower)
    if scenario_cmd:
        state["scenario"] = scenario_cmd
        state["step"] = 0

    # --- Help/Commands handler ---
    if txt_lower in ('!help', '!commands'):
        help_text = """
Elite Bot Command List:

!scripts — Standard sales scripts library
!trust — Trust-building coaching
!tonality — Voice/tonality coaching
!firstimpression — Greeting & intro roleplay
!pvf — Guided PVF close
!roleplay price — Price/Payment Too High (3-deep branching)
!roleplay trade — Trade value objection
!roleplay think — “Let me think about it”
!roleplay shop — “I want to shop around”
!roleplay spouse — “I need to check with my spouse”
!objection price — Price objection (value + options trade-offs)
!objection paymenttoohigh — Payment Too High (monthly range → choices → soft commit)
!objection tradevalue — Trade value objection
!objection thinkaboutit — Think about it objection
!objection shoparound — Shop around objection
!objection spouse — Spouse objection
!objection paymentvsprice — Payment vs Price objection
!objection timingstall — Timing stall objection
!dailylog — Daily log
!earn — E.A.R.N. overview
!checkpoints — Five Emotional Checkpoints
!coaching — Coaching menu
!coaching-tips (alias !coachingtips) — Coaching tips
!coaching-roleplay (alias !coachingroleplay) — Coaching roleplay
"""
        st.session_state.messages.append({"role": "assistant", "content": help_text})
        return help_text

    if txt_lower in ("continue", "end", "restart"):
        if txt_lower == "restart":
            state["step"] = 0
        elif txt_lower == "end":
            state.update({"scenario": "", "step": 0, "target": None, "offer": None, "band": ""})
    else:
        # Offer capture
        if any(k in txt_lower for k in ["we’re at", "we're at"]) or txt_lower.startswith("$") or re.search(r"\b(at|=)\s*\$?\d+", txt_lower):
            offer = extract_int(text)
            if offer is not None:
                state["offer"] = offer
        # Target capture
        if any(k in txt_lower for k in ["under", "closer to", "around", "about", "target", "budget", "cap"]):
            target = extract_int(text)
            if target is not None:
                state["target"] = target

    state["band"] = compute_band(state.get("target"), state.get("offer"))
    state["last_updated"] = time.time()

    # Push user message
    st.session_state.messages.append({"role": "user", "content": text})

    # Build OpenAI messages
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
    # Build the complete message list
    system_messages = [
        {"role": "system", "content": CHARACTER},
        {"role": "system", "content": f"User: {st.session_state.user_name}. Session: {st.session_state.session_id}."},
        {"role": "system", "content": "Short, natural dealership language. ~2 sentences per turn. End with a clear next step."},
        {"role": "system", "content": f"SESSION_STATE_JSON={json.dumps(system_state)}"}
    ]
    
    conversation_messages = [m for m in st.session_state.messages if m["role"] in ("user", "assistant")]
    
    # Combine and truncate to avoid context length issues
    messages = system_messages + conversation_messages
    messages = truncate_messages(messages, max_messages=15)
    
    print(f"Using truncated message history with {len(messages)} messages")

    # Call OpenAI (with function calling)
    ai = run_openai(messages)
    msg = ai["choices"][0]["message"]

    # Tool calls
    if "function_call" in msg and msg["function_call"]:
        fn = msg["function_call"]["name"]
        args_json = msg["function_call"].get("arguments") or "{}"
        try:
            args = json.loads(args_json)
        except json.JSONDecodeError:
            args = {}

        if fn == "append_daily_log":
            try:
                result = daily_log_append_or_update(
                    user=args.get("user", st.session_state.user_name),
                    ups=args.get("ups", ""),
                    calls=args.get("calls", ""),
                    followups=args.get("followups", ""),
                    appointments=args.get("appointments", "")
                )
                messages.append(msg)
                messages.append({"role": "function", "name": "append_daily_log", "content": json.dumps(result)})
            except Exception as e:
                print(f"Error in append_daily_log: {e}")
                messages.append(msg)
                messages.append({
                    "role": "function", 
                    "name": "append_daily_log", 
                    "content": json.dumps({
                        "ok": False, 
                        "error": f"Error logging data: {str(e)}"
                    })
                })
            
            try:
                ai = openai.ChatCompletion.create(model=OPENAI_MODEL, messages=messages, temperature=0.3)
                msg = ai["choices"][0]["message"]
            except Exception as e:
                print(f"Error in OpenAI API call after append_daily_log: {e}")
                msg = {"content": "I've recorded your daily log, but encountered an error processing the final response."}

        elif fn == "log_session_turn":
            try:
                result = session_log_append(
                    session_id=st.session_state.session_id,
                    user_name=st.session_state.user_name,
                    scenario=state.get("scenario",""),
                    step=int(args.get("step", state.get("step", 0))),
                    target_payment=args.get("target_payment", state.get("target")),
                    offer_payment=args.get("offer_payment", state.get("offer")),
                    band=args.get("band", state.get("band", "")),
                    message=args.get("message", text)
                )
                messages.append(msg)
                messages.append({"role": "function", "name": "log_session_turn", "content": json.dumps(result)})
            except Exception as e:
                print(f"Error in log_session_turn: {e}")
                messages.append(msg)
                messages.append({"role": "function", "name": "log_session_turn", "content": json.dumps({"ok": False, "error": str(e)})})
            ai = openai.ChatCompletion.create(model=OPENAI_MODEL, messages=messages, temperature=0.3)
            msg = ai["choices"][0]["message"]

    assistant_text = msg.get("content") or "Working on it…"

    # Increment step for roleplay
    if state.get("scenario"):
        state["step"] = min(int(state.get("step", 0)) + 1, 10)

    st.session_state.messages.append({"role": "assistant", "content": assistant_text})

    # Best-effort per-turn session log
    try:
        result = session_log_append(
            session_id=st.session_state.session_id,
            user_name=st.session_state.user_name,
            scenario=state.get("scenario",""),
            step=int(state.get("step", 0)),
            target_payment=state.get("target"),
            offer_payment=state.get("offer"),
            band=state.get("band",""),
            message=assistant_text
        )
        if not result.get("ok"):
            print(f"Warning: Failed to log session: {result.get('error')}")
    except Exception as e:
        print(f"Error logging session: {e}")
        # Don't show error to user, just silently log it

    return assistant_text

# =========================
# Component: serve your index.html and handle events
# =========================
print(f"Component directory: {COMPONENT_DIR}")

# Check if build directory exists, otherwise use frontend directory directly
if not os.path.exists(COMPONENT_DIR) or not os.path.isfile(os.path.join(COMPONENT_DIR, "index.html")):
    COMPONENT_DIR = os.path.join(os.path.dirname(__file__), "elite_chat_component", "frontend")
    print(f"Using directory: {COMPONENT_DIR}")

# Verify component directory exists
if not os.path.exists(COMPONENT_DIR):
    st.error(f"Component directory not found: {COMPONENT_DIR}")
    st.stop()

# Choose one: either path (for production) or url (for development)
# For local development:
# chat_component = components.declare_component(
#     "elite_chat",
#     # path=COMPONENT_DIR,
#     url="http://localhost:3000"  # For local development
# )

frontend_build_dir = Path(__file__).parent / "elite_chat_component" / "frontend" / "build"

# For production (uncomment path and comment url):
chat_component = components.declare_component(
    "elite_chat",
    path=str(frontend_build_dir),
)

# Track processed events to avoid loops
if "last_processed_event" not in st.session_state:
    st.session_state.last_processed_event = None

# Pass data to the component and receive events back with a unique timestamp to avoid caching
event = chat_component(
    messages=st.session_state.messages,
    user_name=st.session_state.user_name,
    session_id=st.session_state.session_id,
    timestamp=time.time(),  # Add timestamp to force refresh
    key="elite_chat",
    default=None,
)

# Handle events from the component (Streamlit.setComponentValue({...}))
if isinstance(event, dict) and str(event) != st.session_state.last_processed_event:
    # Store this event to avoid processing it again
    st.session_state.last_processed_event = str(event)
    print(f"Processing event: {event}")
    action = event.get("action")
    
    if action == "send_message":
        message = (event.get("message") or "").strip()
        user_name = event.get("user_name", "User")
        st.session_state.user_name = user_name
        if message:
            respond_to(message)
            st.session_state.needs_rerun = True
            
    elif action == "send_command":
        command = (event.get("command") or "").strip()
        user_name = event.get("user_name", "User")
        st.session_state.user_name = user_name
        if command:
            respond_to(command)
            st.session_state.needs_rerun = True
            
    elif action == "set_name":
        name = (event.get("user_name") or "").strip() or "User"
        st.session_state.user_name = name
        st.session_state.needs_rerun = True
        print(f"Name set to: {name}")

# Use a separate flag to prevent multiple reruns in the same cycle
if st.session_state.needs_rerun:
    st.session_state.needs_rerun = False
    st.rerun()

# No Streamlit widgets below — the UI is 100% in index.html
