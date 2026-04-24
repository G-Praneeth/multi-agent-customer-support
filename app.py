import os
import streamlit as st
from groq import Groq
from dotenv import load_dotenv

# Load API key from .env file
load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ─────────────────────────────────────────
# KNOWLEDGE BASE (FAQ Agent's brain)
# ─────────────────────────────────────────
FAQ = {
    "refund": "You can request a refund within 30 days of purchase. Please visit our returns page or contact support.",
    "shipping": "Standard shipping takes 5-7 business days. Express shipping takes 1-2 business days.",
    "password": "To reset your password, click 'Forgot Password' on the login page and follow the instructions.",
    "cancel": "You can cancel your order within 24 hours of placing it by visiting your order history.",
    "payment": "We accept Visa, MasterCard, PayPal, and Apple Pay.",
    "track": "You can track your order using the tracking number sent to your email after shipment.",
}

# ─────────────────────────────────────────
# AGENT 1: Orchestrator Agent
# ─────────────────────────────────────────
def orchestrator_agent(user_input):
    prompt = f"""
You are an Orchestrator Agent in a customer support system.
Classify the user's message into one of these categories:
- "faq" → if the question is about refund, shipping, password, cancel, payment, or tracking
- "escalate" → if the user is angry, frustrated, or has a complex/unusual issue

Respond with ONLY one word: either "faq" or "escalate".

User message: {user_input}
"""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=10,
        temperature=0
    )
    decision = response.choices[0].message.content.strip().lower()
    return decision

# ─────────────────────────────────────────
# AGENT 2: FAQ Agent
# ─────────────────────────────────────────
def faq_agent(user_input):
    for keyword, answer in FAQ.items():
        if keyword in user_input.lower():
            return f"📚 **FAQ Agent:** {answer}", "Knowledge Base Lookup (no AI needed)"

    prompt = f"""
You are a helpful customer support FAQ agent.
Answer the following customer question politely and concisely.
If you don't know the answer, say you'll connect them to a specialist.

Question: {user_input}
"""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200,
        temperature=0.5
    )
    return f"📚 **FAQ Agent:** {response.choices[0].message.content.strip()}", "AI Generated Answer"

# ─────────────────────────────────────────
# AGENT 3: Escalation Agent
# ─────────────────────────────────────────
def escalation_agent(user_input):
    prompt = f"""
You are a senior customer support escalation agent.
The customer has a complex issue or seems frustrated.
Respond with empathy, acknowledge their issue, apologize if needed,
and let them know a human specialist will follow up within 24 hours.

Customer message: {user_input}
"""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200,
        temperature=0.7
    )
    return f"🚨 **Escalation Agent:** {response.choices[0].message.content.strip()}\n\n⚠️ *This issue has been flagged for human review.*", "Escalated to Human Review"

# ─────────────────────────────────────────
# SENTIMENT ANALYZER
# ─────────────────────────────────────────
def analyze_sentiment(user_input):
    prompt = f"""
Analyze the sentiment of this message and respond with ONLY one of these words:
"positive", "neutral", or "negative"

Message: {user_input}
"""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=10,
        temperature=0
    )
    return response.choices[0].message.content.strip().lower()

# ─────────────────────────────────────────
# INPUT GUARDRAIL
# ─────────────────────────────────────────
def is_safe_input(user_input):
    dangerous_phrases = [
        "ignore previous instructions",
        "forget your instructions",
        "you are now",
        "act as",
        "disregard",
        "jailbreak"
    ]
    for phrase in dangerous_phrases:
        if phrase in user_input.lower():
            return False
    return True

# ─────────────────────────────────────────
# STREAMLIT UI
# ─────────────────────────────────────────
st.set_page_config(page_title="AI Customer Support", page_icon="🤖", layout="wide")

# Split into two columns: chat + transparency panel
chat_col, panel_col = st.columns([2, 1])

with chat_col:
    st.title("🤖 Multi-Agent Customer Support System")
    st.markdown("Ask me anything about your order, refunds, shipping, or account!")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_input = st.chat_input("Type your message here...")

with panel_col:
    st.title("🔍 Agent Transparency Panel")
    st.markdown("*See how agents make decisions in real time*")

    if "log" not in st.session_state:
        st.session_state.log = []

    for entry in st.session_state.log:
        with st.expander(f"Message: \"{entry['message'][:40]}...\"" if len(entry['message']) > 40 else f"Message: \"{entry['message']}\""):
            st.markdown(f"**🛡️ Safety Check:** {entry['safety']}")
            st.markdown(f"**😊 Sentiment:** {entry['sentiment']}")
            st.markdown(f"**🧭 Orchestrator Decision:** {entry['decision']}")
            st.markdown(f"**🤖 Agent Used:** {entry['agent']}")
            st.markdown(f"**📋 Reason:** {entry['reason']}")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with chat_col:
        with st.chat_message("user"):
            st.markdown(user_input)

    # Safety check
    if not is_safe_input(user_input):
        response = "⛔ **Security Alert:** Your message contains disallowed content and has been blocked."
        log_entry = {
            "message": user_input,
            "safety": "❌ BLOCKED — Prompt injection detected",
            "sentiment": "N/A",
            "decision": "N/A",
            "agent": "Guardrail",
            "reason": "Dangerous phrase detected in input"
        }
    else:
        sentiment = analyze_sentiment(user_input)
        sentiment_emoji = "😊 Positive" if sentiment == "positive" else "😐 Neutral" if sentiment == "neutral" else "😠 Negative"

        decision = orchestrator_agent(user_input)

        if "escalate" in decision:
            response, reason = escalation_agent(user_input)
            agent_used = "🚨 Escalation Agent"
        else:
            response, reason = faq_agent(user_input)
            agent_used = "📚 FAQ Agent"

        log_entry = {
            "message": user_input,
            "safety": "✅ PASSED",
            "sentiment": sentiment_emoji,
            "decision": "Escalate" if "escalate" in decision else "FAQ",
            "agent": agent_used,
            "reason": reason
        }

    st.session_state.log.append(log_entry)

    st.session_state.messages.append({"role": "assistant", "content": response})
    with chat_col:
        with st.chat_message("assistant"):
            st.markdown(response)

    st.rerun()