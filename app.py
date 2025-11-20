import streamlit as st
from huggingface_hub import InferenceClient
from dotenv import load_dotenv
import os
import sqlite3


conn = sqlite3.connect("chat_history.db", check_same_thread=False)
cursor = conn.cursor()

# -------------------------
# Timezone helpers & DB save function
# Place this near the top of app.py (after imports and DB connection)
# -------------------------
from datetime import datetime, timezone

# timezone setup: ZoneInfo (py3.9+) with pytz fallback
try:
    from zoneinfo import ZoneInfo
    KOLKATA = ZoneInfo("Asia/Kolkata")
except Exception:
    import pytz
    KOLKATA = pytz.timezone("Asia/Kolkata")

# Ensure your table has TEXT timestamp (run once)
cursor.execute("""
CREATE TABLE IF NOT EXISTS chat_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT,
    message TEXT,
    timestamp TEXT
)
""")
conn.commit()

# Save helper that writes IST timestamp into DB
def save_message(role, message):
    try:
        now_ist = datetime.now(KOLKATA)
    except Exception:
        now_ist = datetime.now(timezone.utc).astimezone(KOLKATA)
    ts = now_ist.strftime("%Y-%m-%d %H:%M:%S %z")  # e.g. "2025-11-19 17:18:05 +0530"
    cursor.execute(
        "INSERT INTO chat_history (role, message, timestamp) VALUES (?, ?, ?)",
        (role, message, ts)
    )
    conn.commit()

# Robust parser to convert stored timestamps to IST display format
def parse_to_ist(ts_str):
    """
    Accepts various timestamp formats stored in DB and returns IST string "YYYY-MM-DD HH:MM:SS".
    If parsing fails, returns original string.
    """
    if not ts_str:
        return ""
    # Try with explicit offset first: "YYYY-MM-DD HH:MM:SS +0530"
    try:
        if ("+" in ts_str and ts_str.strip()[-5:].lstrip("+").isdigit()) or ("-" in ts_str and ts_str.strip()[-5:].lstrip("-").isdigit()):
            dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S %z")
            ist_dt = dt.astimezone(KOLKATA)
            return ist_dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        pass
    # Try naive datetime (assume UTC)
    try:
        dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
        dt = dt.replace(tzinfo=timezone.utc)
        ist_dt = dt.astimezone(KOLKATA)
        return ist_dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        pass
    # Try ISO formats
    try:
        dt = datetime.fromisoformat(ts_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        ist_dt = dt.astimezone(KOLKATA)
        return ist_dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        pass
    return ts_str  # fallback: show original


load_dotenv()
HFTOKEN= os.getenv("HFTOKEN")
# Page configuration
st.set_page_config(
    page_title="Legal Advice Chatbot - India",
    page_icon="⚖️",
    layout="centered"
)

# Custom CSS for professional legal theme with chat interface


st.markdown("""
    <style>

    .stButton > button {
        width: 100%;
        background-color: #1e3a8a;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        padding: 0.7rem;
        font-size: 1.1rem;
    }
    .stButton > button:hover {
        background-color: #1e40af;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
            
    .error-box {
        background-color: #fef2f2; 
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #dc2626;
    }
    .disclaimer-box {
        background-color: #fffbeb;
        padding: 1.2rem;
        border-radius: 8px;
        border-left: 4px solid #f59e0b;
        margin: 1.5rem 0;
        font-size: 0.9rem;
    }
    
    .category-badge {
        display: inline-block;
        padding: 0.3rem 0.8rem;
        background: #9D9D9D;
        border: 1px solid #9D9D9D;
        color: black;
        border-radius: 15px;
        font-size: 0.85rem;
        margin: 0.2rem;
        font-weight: 600;
        width: 180px;
        display:flex; 
        text-align: center;
        border: 1px solid black !important;
    }
    
    div.stButton > button[kind="secondary"] {
    background-color: rgba(16, 163, 127, 0.35) !important; /* transparent #10A37F */
    color: white !important;      /* text color */
    border: 1px solid #10A37F !important;
    border-radius: 10px !important;
    padding: 10px 14px !important;
    font-weight: 600 !important;
}
    div.stButton > button[kind="secondary"]:hover {
    background-color: rgba(16, 163, 127, 0.55) !important;
    color: white !important;
    border: 1px solid #0E8F70 !important;
}

    div.stAlert {
    border: 1px solid #30377D !important;
    border-radius: 10px !important;
    font-weight: 600 !important;

}

            
    .main-header {
        text-align: center;
        color: #1e3a8a;
        padding: 1rem 0;
        font-size: 2.5rem;
        font-weight: 700;
    }
    .sub-header {
        text-align: center;
        color: #D8D0D0;
        font-size: 1.2rem;
        margin-bottom: 2rem;
        line-height: 1.6;
    }        
            
    
    .chat-wrapper {
        max-width: 800px;
        margin: 0 auto;
        background: #10A37F;
        padding: 10px;
}

    .message {
        padding: 12px 16px;
        margin: 10px 0;
        border-radius: 14px;
        font-size: 1.05rem;
        line-height: 1.5;
        max-width: 80%;
}

    .user {
        
        margin-left: auto;
        background: #10A37F;
        border: 1px solid #0E8F70;
        color: black;

}

    .assistant {
        
        margin-right: auto;
        background: #9D9D9D;
        border: 1px solid #565869;
        color: black;

}

    .avatar {
        width: 36px;
        height: 36px;
        border-radius: 50%;
        background: #e5e5e5;
        display: inline-block;
        margin-right: 8px;
}

    .message-row {
        display: flex;
        align-items: flex-start;
        margin-top: 18px;
}

    .message-text {
        flex: 1;
}
   

</style>

    """, unsafe_allow_html=True)



# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []

# Header
st.markdown("<h1 class='main-header'>⚖️ LawPilot: Legal Advice Bot</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-header'>Free AI-Powered Legal Guidance for Indian Citizens<br>Get instant answers on tenancy, consumer rights, workplace issues & traffic laws</p>", unsafe_allow_html=True)


# Sidebar
with st.sidebar:
    st.markdown("### 📋 Coverage Areas:")
    st.markdown("""
    <div class='sidebar-info'>
    <span class='category-badge'> Tenancy Disputes</span>
    <span class='category-badge'> Consumer Rights </span>
    <span class='category-badge'> Workplace Issues</span>
    <span class='category-badge'> Copyright Issues    </span>
    <span class='category-badge'> Cyber Crime     </span>
    <span class='category-badge'> Divorce Issues     </span>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("")
    
    st.markdown("### 📞 Emergency Helplines:")
    st.markdown("""
    - **Police:** 100
    - **Women Helpline:** 1091
    - **Consumer Helpline:** 1915
    - **Cyber Crime:** 1930
    """)
    
    

    

  
    # Clear conversation button
    if st.button("🗑️ Clear Conversation"):
        st.session_state.messages = []
        st.session_state.conversation_history = []
        st.rerun()


# Display chat messages
chat_container = st.container()
with chat_container:
    for message in st.session_state.messages:
        if message["role"] == "user":
            st.markdown(f"""
            <div class="message-row" style="justify-content: flex-end;">
                <div class="message user">
                    {message['content']}
                </div>
            </div>
            """, unsafe_allow_html=True)

        else:
            st.markdown(f"""
            <div class="message-row" style="justify-content: flex-start;">
                <div class="message assistant">
                    {message['content']}
                </div>
            </div>
            """, unsafe_allow_html=True)


# Chat input
st.markdown("---")

# Use chat_input which supports Enter key
user_input = st.chat_input("Type your legal question here and press Enter...")

# Process the message when user sends it
if user_input:
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    with st.spinner("🔍 Analyzing your legal query"):
        try:
            # Initialize the client
            client = InferenceClient(token=HFTOKEN)
            
            # Build conversation history for context
            conversation_context = ""
            if len(st.session_state.conversation_history) > 0:
                conversation_context = "\n\n**PREVIOUS CONVERSATION CONTEXT:**\n"
                for msg in st.session_state.conversation_history[-6:]:  # Last 3 exchanges
                    conversation_context += f"{msg['role'].upper()}: {msg['content']}\n"
            
            # Prepare the comprehensive legal prompt with conversation context
            system_prompt = f"""You are an expert Indian legal advisor AI assistant with comprehensive knowledge of Indian laws, acts, and legal procedures. Your role is to provide accurate, helpful, and accessible legal guidance to Indian citizens.

**CRITICAL INSTRUCTIONS:**
1. NEVER use LaTeX formatting or mathematical symbols
2. Write in clear, plain language that ordinary citizens can understand
3. Always cite relevant Indian laws, acts, and sections when applicable
4. Provide step-by-step actionable guidance
5. Include relevant helpline numbers and government portals
6. Be empathetic and professional in tone
7. If the query is not legal in nature, politely redirect the user
8. Maintain conversation context and refer to previous questions when relevant
9. If user asks follow-up questions, provide additional details or clarifications based on the conversation history

**SCOPE OF EXPERTISE:**
- Tenancy disputes and Rent Control Acts
- Consumer Protection Act, 2019
- Workplace rights and Labour Laws
- Motor Vehicles Act, 1988 and traffic violations
- Cyber crime and IT Act, 2000
- Family law matters (divorce, maintenance, custody)
- Property disputes and laws
- Civil and criminal procedure basics
- Government complaint mechanisms

{conversation_context}

**CURRENT USER QUERY:**
{user_input}

**RESPONSE FORMAT (Use this for NEW questions, adapt for follow-ups):**


[Summarize the user's problem in 2-3 lines and do not enter what you are responding to for eg
user wrote: "Hello"
just respond with the summary first and follow the rest dont specify what you are responding to]

**Applicable Laws:**
[List the relevant Indian laws, acts, and sections that apply to this situation]

**Your Legal Rights:**
[Clearly explain what rights the user has under Indian law]

**Step-by-Step Action Plan:**

**Step 1:** [First action to take]
- Explanation: [Why this step is important]
- Timeline: [Expected timeframe]

**Step 2:** [Second action to take]
- Explanation: [Why this step is important]
- Timeline: [Expected timeframe]

[Continue for all necessary steps]

**Required Documents:**
[List all documents the user needs to gather]

**Where to File/Approach:**
[Specify the exact authority, court, or portal where action should be taken]
- Portal/Office: [Name and link if applicable]
- Location: [Where to go physically if needed]

**Estimated Costs:**
[Provide approximate costs for court fees, stamp duties, etc. if applicable]

**Important Deadlines:**
[Mention any limitation periods or time-sensitive requirements]

**Helpline Numbers & Resources:**
[Provide relevant government helplines and official portals]

**Legal Precedents/Judgments (if relevant):**
[Mention any important Supreme Court or High Court judgments related to this issue]

**Sample Document Template (if applicable):**
[Provide a basic template for complaint letter, notice, or application if relevant]

**Important Warnings:**
[Any pitfalls to avoid or critical considerations]

**Next Steps if This Doesn't Work:**
[Alternative options or escalation paths]

**Recommendation:**
[Final advice including when to consult a lawyer]

---
**Note:** This is general legal information. For specific legal advice tailored to your exact circumstances, please consult a qualified lawyer.

**SPECIAL HANDLING:**
- If query is non-legal: Politely inform them this chatbot is specifically for legal matters under Indian law
- If query requires immediate legal action: Clearly mark as URGENT and recommend immediate lawyer consultation
- If query involves criminal matters: Advise consulting a criminal lawyer and provide police contact
- If information is insufficient: Ask specific clarifying questions
- For follow-up questions: Provide direct, concise answers that build on previous context

Provide your response now:"""

            messages = [{"role": "user", "content": system_prompt}]
            
            # List of models to try (in order of preference)
            models_to_try = [
                "deepseek-ai/DeepSeek-V3-0324",
                "Qwen/Qwen2.5-7B-Instruct",
                "meta-llama/Llama-3.2-3B-Instruct",
            ]
            
            success = False
            
            for model in models_to_try:
                try:
                    response = client.chat_completion(
                        messages=messages,
                        model=model,
                        max_tokens=2500,
                    )
                    
                    answer = response.choices[0].message.content
                    success = True
                    
                    # Add assistant response to chat
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                    
                    # Update conversation history
                    st.session_state.conversation_history.append({"role": "user", "content": user_input})
                    save_message("user", user_input)

                    st.session_state.conversation_history.append({"role": "assistant", "content": answer})
                    save_message("assistant", answer)

                    
                    # Rerun to display the new message
                    st.rerun()
                    
                    break
                    
                except Exception as e:
                    continue
            
            if not success:
                error_message = "❌ Unable to generate response at the moment. Please try again in a few moments or rephrase your question."
                st.session_state.messages.append({"role": "assistant", "content": error_message})
                st.rerun()
                
        except Exception as e:
            error_message = f"❌ An error occurred: {str(e)[:100]}"
            st.session_state.messages.append({"role": "assistant", "content": error_message})
            st.rerun()

# Show helpful tips if no conversation yet
if len(st.session_state.messages) == 0:
    st.info("""
    👋 **Welcome to the Legal Advice Chatbot!**
    
    Start by asking a legal question. You can:
    - Ask about your rights in any situation
    - Request step-by-step guidance for legal procedures
    - Ask follow-up questions to get more details
    - Request document templates or complaint formats
    
    Just type your question below and press **Enter** to begin!
    """)

# Footer
