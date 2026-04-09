from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from google.genai import types
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from typing import List, Optional
import os
import json
import asyncio
import logging
import tempfile
from datetime import datetime
import openpyxl

logger = logging.getLogger("qterra-chatbot")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

def load_suggestions(filepath: str = "Suggestions v2.xlsx") -> dict:
    """Load properties from the Suggestions Excel file.
    Expected columns: Field1, URL, Address, Property Type, Price, Status

    Status values:
      'For Lease'  -> available properties, shown to tenants
      'LEASED !'   -> successfully leased, shown to owners as track record examples
    """
    available = []
    leased = []
    try:
        wb = openpyxl.load_workbook(filepath)
        ws = wb.active
        # Columns: ['Field1'(0), 'URL'(1), 'Address'(2), 'Property Type'(3), 'Price'(4), 'Status'(5)]
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not any(row):
                continue
            raw_status = str(row[5]).strip() if len(row) > 5 and row[5] else ""
            status_upper = raw_status.replace(" ", "").upper()  # normalize: remove spaces, uppercase
            item = {
                "url": row[1] if len(row) > 1 and row[1] else "",
                "address": row[2] if len(row) > 2 and row[2] else "",
                "property_type": row[3] if len(row) > 3 and row[3] else "",
                "type": row[3] if len(row) > 3 and row[3] else "",  # alias for type matching
                "price": row[4] if len(row) > 4 and row[4] else "",
                "status": raw_status,
            }
            # "FOR LEASE" → available for Tenant flow
            # "LEASED!" / "LEASED !" → shown to Owners as successful leasing examples
            if "LEASED" in status_upper:
                leased.append(item)
            else:
                available.append(item)
    except Exception as e:
        logger.warning("Could not load suggestions: %s", e)
    return {"available": available, "leased": leased}

SUGGESTIONS = load_suggestions()
logger.info(
    "Loaded %s available and %s leased properties from Suggestions v2.",
    len(SUGGESTIONS["available"]),
    len(SUGGESTIONS["leased"]),
)

def load_env():
    """Load .env file for local development. Skipped silently in production."""
    try:
        with open(".env", "r") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    os.environ.setdefault(key, value)
    except FileNotFoundError:
        pass  # Running in production with env vars set directly

load_env()

app = FastAPI()
api_router = APIRouter()

cors_origins = os.environ.get("CORS_ALLOW_ORIGINS", "*")
allow_origins = [origin.strip() for origin in cors_origins.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins or ["*"],
    allow_credentials=False if allow_origins == ["*"] else True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY is not set in .env")
gemini_client = genai.Client(api_key=api_key)

scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

# Support credentials from file (local) or env var (production/Railway)
google_creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
if google_creds_json:
    tmp_path = None
    creds_data = json.loads(google_creds_json)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
        json.dump(creds_data, tmp)
        tmp_path = tmp.name
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(tmp_path, scope)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
else:
    creds = ServiceAccountCredentials.from_json_keyfile_name('google_credentials.json', scope)

client = gspread.authorize(creds)
spreadsheet_id = os.environ.get("SPREADSHEET_ID")
sheet = None

try:
    sheet = client.open_by_key(spreadsheet_id).sheet1
    logger.info("Successfully connected to Google Sheet")
except Exception as e:
    logger.warning("Could not connect to Google Sheet. Error: %s", e)


class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]


SYSTEM_PROMPT = """
Your name is Quinn. You are a warm, empathetic, and professional chatbot for Qterra Property Management in Ontario, Canada.
You have a soft, human personality — you show genuine care, use friendly affirmations like "That's great!", "Of course!", "Absolutely!", "I completely understand!", and never sound robotic.
Keep every response SHORT and conversational. Ask only ONE question at a time. Never rush the user.

============================
STEP 1 — GREETING & INTENT
============================
Start by warmly greeting the user and asking how you can help.
Listen carefully to their opening message and determine their role:

- TENANT: they say they are "looking for" a place to rent / looking to rent, searching for a property, need a place, etc.
- OWNER: they say they HAVE a property, OWN a property, want to find tenants FOR their property, want to rent OUT their property, etc.
- PROPERTY MANAGEMENT: they mention needing property management services.

CRITICAL ROLE RULES:
- "I am looking for a house/condo/basement" = TENANT. NEVER interpret this as Owner.
- "I have a house" or "I own a property" = OWNER.
- When in doubt, ask: "Are you looking to rent a place, or are you a property owner?"

============================
STEP 2 — COLLECT NAME & PHONE (ALL ROLES)
============================
Once you know the role, ask for their Name and Phone Number TOGETHER in a single question.
For example: "Could I please get your name and phone number so our team can reach out to you?"

CRITICAL MEMORY RULE: Review the ENTIRE conversation history before asking any question.
- If the user already stated their name earlier in the conversation, do NOT ask for it again. Only ask for what is still missing.
- If you already have their name but not their phone, ask only for their phone number.
- If you already have both, move to the next step immediately.

PHONE NUMBER VALIDATION RULES (apply strictly):
- Valid Canadian/US format: NPA-NXX-XXXX
  - NPA = Area code: first digit must be 2-9 (NOT 0 or 1)
  - NXX = Exchange: first digit must be 2-9 (NOT 0 or 1)
  - Remaining digits (XXXX): any digit 0-9
- Dashes are optional — accept both 6475559919 and 647-555-9919
- REJECT numbers where area code or exchange starts with 0 or 1 (e.g. 123-456-7890 or 011-555-1234 are INVALID)
- If invalid, kindly say something like: "Hmm, that doesn't look like a valid phone number. Could you double-check and share it again? It should be a 10-digit number like 647-555-9919."
- Only proceed once you have a valid phone number.
- When the phone number IS valid, do NOT tell the user it is "valid" or mention validation at all. Just warmly acknowledge (e.g. "Thanks, Ali!") and move on to the next step.

============================
STEP 2B — CONTACT PREFERENCE (ALL ROLES)
============================
Immediately after receiving a valid phone number, you MUST output the following marker on its own line:
[CONTACT_MENU]

This marker will be replaced by clickable buttons in the UI. Your message should say something brief like:
"Thanks! How would you prefer to be contacted?"
Then put [CONTACT_MENU] on the next line. Do NOT list the options in text — the buttons will appear automatically.

When the user clicks a button, their selection will come back as a user message:
- If they say "whatsapp" or choose WhatsApp: Ask them "Is your WhatsApp number the same as the phone number you shared?" If yes, note it. If no, ask for their WhatsApp number.
- If they say "email" or choose Email: Ask them for their email address.
- If they say "phone" or choose Phone Call: Simply acknowledge and proceed to the next step.
- If they say "skip" or choose Skip: Simply acknowledge and proceed to the next step.

Once the contact preference step is resolved (preference noted, and any follow-up like email or WhatsApp number collected), move to the next step for their role (STEP 3A/3B/3C).

IMPORTANT: You should ONLY emit [CONTACT_MENU] ONCE, right after receiving the valid phone number. Never emit it again later in the conversation. If the user has already answered the contact preference question, do NOT ask again.

============================
STEP 3A — TENANT FLOW
============================
After contact preference is resolved, collect the following:
1. Preferred location or area in Ontario. (ask alone)
2. Type of property (Condo, Basement, House, Townhouse, etc.) (ask alone)
3. Credit score range (e.g. 600-650, 700-750). Say something warm like: "Could you share your approximate credit score range?"
4. Preferred move-in date AND number of occupants — ask these TOGETHER in one question. For example: "When are you looking to move in, and how many people will be living in the unit?"

AFTER collecting all items:
- If a [SYSTEM] block is provided below with matching properties, recommend ONLY those properties — copy addresses and URLs EXACTLY as written. Include the full URL for each.
- If NO [SYSTEM] block with properties is provided, do NOT invent any property. Instead say warmly: "I'll have our team reach out to you shortly with some great options that match what you're looking for!"
- Thank them warmly.

============================
STEP 3B — OWNER FLOW
============================
After contact preference is resolved, collect ONE AT A TIME:
1. City or general area where their property is located. Do NOT ask for a full street address — city or neighbourhood is enough.
2. Type of property.
3. When they'd like tenants to move in (move-in date / availability date).

After collecting all info:
- Warmly assure them: "Thank you so much! I've passed your information to our team and someone will be in touch with you very soon."
- If a [SYSTEM] block with leased examples is provided, share those EXACTLY as written. Say: "Here are some similar properties we have successfully leased recently:" and list each with its COMPLETE URL.
- Add reassurance: "You're in great hands!"
- Thank them and wish them well.

============================
STEP 3C — PROPERTY MANAGEMENT FLOW
============================
After contact preference is resolved, ask:
1. Location of their property or area they need help with.

Then say warmly: "Wonderful! I've noted your information and our property management team will reach out to you as soon as possible. We're excited to help you!"
Thank them.

============================
FINAL STEP — JSON PAYLOAD (INTERNAL, DO NOT SHOW TO USER)
============================
Once you have all the required information for the role, you MUST end your FINAL response with a JSON block (after your goodbye message) formatted EXACTLY like this:

```json
{
  "name": "Jane Smith",
  "role": "Tenant",
  "location": "Brampton",
  "property_type": "Condo",
  "phone": "647-555-9919",
  "contact_preference": "WhatsApp",
  "email": "",
  "whatsapp_number": "647-555-9919",
  "move_in_date": "May 1, 2026",
  "credit_score": "700-750",
  "num_occupants": "2",
  "summary": "Tenant looking for a condo in Brampton, moving in May 2026, credit score 700-750, 2 occupants. Prefers WhatsApp."
}
```

For Owners:
```json
{
  "name": "John Doe",
  "role": "Owner",
  "location": "Mississauga",
  "property_type": "Detached House",
  "phone": "905-444-1234",
  "contact_preference": "Email",
  "email": "john@example.com",
  "whatsapp_number": "",
  "move_in_date": "June 1, 2026",
  "credit_score": "",
  "num_occupants": "",
  "summary": "Owner has a detached house in Mississauga available June 2026. Prefers Email."
}
```

For Property Management:
```json
{
  "name": "Ali Khan",
  "role": "Property Management",
  "location": "Ottawa",
  "property_type": "",
  "phone": "613-999-8888",
  "contact_preference": "Phone",
  "email": "",
  "whatsapp_number": "",
  "move_in_date": "",
  "credit_score": "",
  "num_occupants": "",
  "summary": "Interested in property management services in Ottawa. Prefers Phone call."
}
```

CONTACT PREFERENCE FIELD RULES:
- "contact_preference" should be one of: "WhatsApp", "Email", "Phone", "Skip", or "" if not yet collected.
- "email" should contain the email address if the user chose Email, otherwise "".
- "whatsapp_number" should contain the WhatsApp number if different from phone, or same as phone if confirmed. Otherwise "".

IMPORTANT RULES:
- Do NOT use markdown formatting like ** or bullet points in your chat messages — keep it plain, natural, conversational.
- Do NOT ask all questions at once. ONE question per response.
- Always be warm, patient, and encouraging.
- The JSON block must always appear at the very end of your message and only once.
- NEVER FABRICATE PROPERTIES: You MUST NEVER invent property addresses, prices, or URLs. The ONLY properties you may mention are those explicitly listed in the [SYSTEM] context block injected into the conversation. If no properties are listed, tell the user the team will follow up with options.
- CRITICAL URL RULE: When sharing property URLs, you MUST copy the EXACT full URL provided to you character-for-character. NEVER shorten, truncate, or modify a URL. Every URL includes the full address with province and postal code (e.g. %2C-ontario-n2a-0l9). If you cut off any part of the URL, it will be a broken link. Always include the COMPLETE URL exactly as given.
"""

GEMINI_MODEL = 'gemini-2.5-flash'


def determine_properties(messages_content: str, properties_list: list):
    """Extract location and property type from conversation to query the database."""
    location = None
    property_type = None

    cities = [
        "hamilton", "scarborough", "toronto", "whitby", "brockville", "mississauga",
        "richmond hill", "milton", "nepean", "innisfil", "orleans", "etobicoke",
        "brampton", "oshawa", "ajax", "pickering", "barrie", "ottawa", "london",
        "kitchener", "waterloo", "cambridge", "guelph", "burlington", "oakville",
        "markham", "vaughan", "newmarket", "north york", "york", "concord",
        "woodbridge", "welland", "niagara falls", "st. catharines", "kingston",
        "stoney creek", "waterdown", "east york", "ridgetown", "king", "mono",
        "east gwillimbury", "innisfil beach", "whitchurch-stouffville", "lefroy"
    ]

    # Category mapping: user keyword -> list of DB property types that belong to that category
    type_categories = {
        "house": ["multi-plex", "semi-detached house", "detached house"],
        "townhouse": ["condo-townhouse", "stacked townhouse", "freehold townhouse"],
        "basement": ["basement apartment"],
        "condo": ["main floor", "upper level", "apartment", "condo"],
        "apartment": ["main floor", "upper level", "apartment", "condo"],
    }

    # Keywords to detect in conversation (order matters — more specific first)
    type_keywords = ["townhouse", "basement", "apartment", "condo", "house"]

    lower_content = messages_content.lower()

    for c in cities:
        if c in lower_content:
            location = c
            break

    for t in type_keywords:
        if t in lower_content:
            property_type = t
            break

    results = properties_list
    if location:
        results = [p for p in results if location.lower() in p['address'].lower()]
        
    requested_type_found = True
    if property_type:
        # Get all DB types that fall under the user's requested category
        db_types = type_categories.get(property_type, [property_type])
        type_results = [p for p in results if any(dt in p['type'].lower() for dt in db_types)]
        if type_results:
            results = type_results
        elif location and results:
            # Type not found in this region, but we have other properties in this region
            requested_type_found = False
        else:
            results = type_results

    # Pass requested_type_found up so prompt can adapt
    return results[-3:], location, property_type, requested_type_found


@api_router.post("/chat")
async def chat_endpoint(req: ChatRequest):
    try:
        if not req.messages:
            raise HTTPException(status_code=400, detail="messages must not be empty")

        history = []
        full_conversation = ""
        for m in req.messages[:-1]:
            role = "model" if m.role == "assistant" else "user"
            history.append(types.Content(role=role, parts=[types.Part(text=m.content)]))
            full_conversation += f"{m.role}: {m.content}\n"

        chat = gemini_client.chats.create(
            model=GEMINI_MODEL,
            config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
            history=history
        )

        last_msg = req.messages[-1].content
        full_conversation += f"user: {last_msg}\n"

        # Detect conversation type
        lower_convo = full_conversation.lower()
        is_owner_convo = any(word in lower_convo for word in [
            "owner", "my property", "looking for tenant", "rent out", "have a property",
            "i own", "landlord", "list my", "find tenants"
        ])
        is_tenant_convo = not is_owner_convo and any(word in lower_convo for word in [
            "tenant", "looking for", "rent", "find a", "need a place", "move in", "looking to rent",
            "i need", "searching for", "apartment", "condo", "basement", "townhouse"
        ])

        context = ""

        # Inject matching available properties for Tenants
        if is_tenant_convo:
            properties, location, property_type, type_found = determine_properties(full_conversation, SUGGESTIONS['available'])
            if properties and location and property_type:
                context = "\n[SYSTEM: The user is a Tenant."
                if not type_found:
                    context += f" We do NOT have their requested property type ({property_type}) in {location}. You MUST gently inform them that we don't have that specific type available there right now, but suggest the following alternative property types we DO have in the same region. NEVER suggest properties from out of the region."
                context += " Here are up to 2 matching available properties from our suggestions portfolio. CRITICAL: You MUST copy each URL below EXACTLY and COMPLETELY — do NOT shorten or truncate any URL. Every character matters, including the postal code at the end:\n"
                for p in properties:
                    price = f" | ${p.get('price', 'N/A')}/mo" if p.get('price') else ""
                    beds = f" | {p.get('beds', '')} bed" if p.get('beds') else ""
                    baths = f" | {p.get('baths', '')} bath" if p.get('baths') else ""
                    link = f" | URL: {p.get('url', '')}"
                    context += f"- {p.get('property_type', 'Property')} at {p['address']}{price}{beds}{baths}{link}\n"
                context += "You MUST output the prices, property types and COMPLETE URLs exactly as shown above, character-for-character. Do NOT remove the province or postal code from the URL.]\n"

        # Inject matching leased properties for Owners as reassurance
        if is_owner_convo and SUGGESTIONS['leased']:
            _, location, property_type, type_found = determine_properties(full_conversation, SUGGESTIONS['leased'])
            matches = []

            if location:
                # Category mapping for type matching
                type_categories = {
                    "house": ["multi-plex", "semi-detached house", "detached house"],
                    "townhouse": ["condo-townhouse", "stacked townhouse", "freehold townhouse"],
                    "basement": ["basement apartment"],
                    "condo": ["main floor", "upper level", "apartment", "condo"],
                    "apartment": ["main floor", "upper level", "apartment", "condo"],
                }
                db_types = type_categories.get(property_type, [property_type]) if property_type else []

                # Step 1: Try location + type match (both)
                for lp in SUGGESTIONS['leased']:
                    loc_match = location.lower() in lp["address"].lower()
                    type_match = property_type and any(dt in lp["property_type"].lower() for dt in db_types)
                    if loc_match and (type_match or not property_type):
                        matches.append(lp)
                    if len(matches) >= 3:
                        break

                # Step 2: If not enough, relax to any property in that location
                if len(matches) < 3:
                    for lp in SUGGESTIONS['leased']:
                        if lp in matches:
                            continue
                        if location.lower() in lp["address"].lower():
                            matches.append(lp)
                        if len(matches) >= 3:
                            break

            # Step 3: Only fall back to any leased property if NO location was detected
            if not matches:
                matches = SUGGESTIONS['leased'][:3]

            context += "\n[SYSTEM: The user is an Owner. After collecting their info and assuring them the team will follow up, "
            if not type_found and location and property_type:
                context += f"gently inform them that while we don't have exactly a {property_type} leased in {location} right now in our immediate examples, we can still serve them perfectly. Offer these alternative recently leased properties in their region. NEVER suggest properties from outside their region. "
            context += "Show these examples of similar properties we have successfully leased to build their confidence. "
            context += "CRITICAL: You MUST copy each URL below EXACTLY and COMPLETELY — do NOT shorten or truncate any URL. Every character matters, including the postal code at the end:\n"
            for lp in matches:
                price = f" | ${lp.get('price', 'N/A')}/mo" if lp.get('price') else ""
                context += f"- {lp.get('property_type', 'Property')} at {lp['address']}{price} | URL: {lp['url']}\n"
            context += "You MUST output the prices, property types and COMPLETE URLs exactly as shown above.]\n"

        # Retry on 503 with exponential backoff
        max_retries = 3
        response_text = None
        for attempt in range(max_retries):
            try:
                response = await asyncio.to_thread(chat.send_message, last_msg + context)
                response_text = response.text
                break
            except Exception as api_err:
                err_str = str(api_err)
                if "503" in err_str or "UNAVAILABLE" in err_str:
                    if attempt < max_retries - 1:
                        wait_secs = 2 ** attempt  # 1s, 2s, 4s
                        logger.warning(
                            "Gemini 503 on attempt %s, retrying in %ss...",
                            attempt + 1,
                            wait_secs,
                        )
                        await asyncio.sleep(wait_secs)
                        continue
                    else:
                        logger.error("Gemini 503 persisted after all retries.")
                        return {
                            "response": "I'm so sorry — I'm experiencing a brief technical hiccup right now. "
                                        "Please try sending your message again in a moment. I'll be right with you!"
                        }
                else:
                    raise

        if response_text is None:
            return {
                "response": "I'm so sorry — something went wrong on my end. Please try again in a moment!"
            }

        # Parse and save JSON payload if present
        if "```json" in response_text:
            json_str = response_text.split("```json")[1].split("```")[0].strip()
            try:
                data = json.loads(json_str)
                if sheet:
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    row = [
                        now,
                        data.get("name", ""),
                        data.get("role", ""),
                        data.get("location", ""),
                        data.get("property_type", ""),
                        data.get("phone", ""),
                        data.get("contact_preference", ""),
                        data.get("email", ""),
                        data.get("whatsapp_number", ""),
                        data.get("move_in_date", ""),
                        data.get("credit_score", ""),
                        data.get("num_occupants", ""),
                        data.get("summary", ""),
                    ]
                    await asyncio.to_thread(sheet.append_row, row)
                else:
                    redacted_data = {
                        "name_present": bool(data.get("name")),
                        "role": data.get("role", ""),
                        "location": data.get("location", ""),
                        "property_type": data.get("property_type", ""),
                        "phone_present": bool(data.get("phone")),
                        "contact_preference": data.get("contact_preference", ""),
                    }
                    logger.info("Lead captured (Sheets not connected): %s", redacted_data)
            except Exception as e:
                logger.exception("Failed to process JSON or save to Sheets: %s", e)

            # Strip JSON from response shown to user
            response_text = response_text.split("```json")[0].strip()

        # Detect [CONTACT_MENU] marker and attach menu options to response
        menu_options = None
        if "[CONTACT_MENU]" in response_text:
            response_text = response_text.replace("[CONTACT_MENU]", "").strip()
            menu_options = [
                {"label": "📱 WhatsApp", "value": "WhatsApp"},
                {"label": "📧 Email", "value": "Email"},
                {"label": "📞 Phone Call", "value": "Phone Call"},
                {"label": "⏭️ Skip", "value": "Skip"},
            ]

        result = {"response": response_text}
        if menu_options:
            result["menu_options"] = menu_options
        return result

    except HTTPException:
        raise
    except Exception:
        logger.exception("Unhandled error in /api/chat")
        raise HTTPException(
            status_code=500,
            detail="Internal server error. Please try again shortly.",
        )


app.include_router(api_router, prefix="/api")
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
