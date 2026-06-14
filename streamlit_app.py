import os
from hashlib import sha256

import requests
import streamlit as st

st.set_page_config(page_title="Smart Shopping Assistant", page_icon="cart", layout="wide")

DEFAULT_API_URL = os.getenv("SMARTSHOP_API_URL", "http://localhost:8000")
API_URL = DEFAULT_API_URL

st.markdown(
    """
    <style>
    [data-testid="stToolbar"],
    [data-testid="stHeaderActionElements"],
    [data-testid="stDecoration"],
    [data-testid="stSidebar"],
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="stSidebarHeader"],
    [data-testid="collapsedControl"],
    #MainMenu,
    header,
    footer {
        display: none !important;
    }
    [data-testid="stAudioInput"] {
        position: fixed;
        right: 5.25rem;
        bottom: 7.7rem;
        z-index: 1001;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 2.25rem !important;
        min-width: 2.25rem !important;
        height: 2.25rem !important;
        min-height: 2.25rem !important;
        overflow: visible !important;
    }
    [data-testid="stAudioInput"] label,
    [data-testid="stAudioInput"] [data-testid="stElementToolbar"],
    [data-testid="stAudioInput"] [data-testid="stAudioInputWaveSurfer"],
    [data-testid="stAudioInput"] [data-testid="stAudioInputWaveformTimeCode"] {
        display: none !important;
    }
    [data-testid="stAudioInput"] > div {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 2.25rem !important;
        min-width: 2.25rem !important;
        height: 2.25rem !important;
        min-height: 2.25rem !important;
        padding: 0 !important;
        margin: 0 !important;
        overflow: visible !important;
    }
    [data-testid="stAudioInput"] button {
        background: #16a34a !important;
        border: 1px solid #86efac !important;
        border-radius: 999px !important;
        box-shadow: 0 0 0 2px rgba(22, 163, 74, 0.2), 0 8px 20px rgba(0, 0, 0, 0.35) !important;
        color: #ffffff !important;
        height: 2.25rem !important;
        width: 2.25rem !important;
        min-width: 2.25rem !important;
        opacity: 1 !important;
        padding: 0 !important;
    }
    [data-testid="stAudioInput"] button:disabled,
    [data-testid="stAudioInput"] button[disabled] {
        background: #15803d !important;
        border-color: #bbf7d0 !important;
        color: #ffffff !important;
        opacity: 1 !important;
        filter: none !important;
        cursor: not-allowed !important;
    }
    [data-testid="stAudioInput"] button svg {
        color: #ffffff !important;
        height: 1.35rem !important;
        width: 1.35rem !important;
        opacity: 1 !important;
    }
    [data-testid="stAudioInput"] audio {
        position: absolute !important;
        width: 1px !important;
        height: 1px !important;
        opacity: 0 !important;
        pointer-events: none !important;
    }
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 10rem;
    }
    [data-testid="stChatInput"] {
        bottom: 3.5rem !important;
    }
    .sample-prompts {
        position: fixed;
        left: 1rem;
        right: 1rem;
        bottom: 0.65rem;
        z-index: 1000;
        display: flex;
        flex-wrap: wrap;
        gap: 0.35rem 0.5rem;
        align-items: center;
        color: rgba(250, 250, 250, 0.62);
        font-size: 0.7rem;
        line-height: 1.25;
        pointer-events: none;
    }
    .sample-prompts span {
        border: 1px solid rgba(250, 250, 250, 0.12);
        border-radius: 999px;
        background: rgba(250, 250, 250, 0.045);
        padding: 0.18rem 0.45rem;
        white-space: nowrap;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Smart Shopping Assistant")

if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "ui_initialized" not in st.session_state:
    stale_session_id = st.query_params.get("session_id")
    if stale_session_id:
        try:
            requests.delete(f"{API_URL}/memory/{stale_session_id}", timeout=10)
        except requests.RequestException:
            pass
        st.query_params.clear()
    st.session_state.ui_initialized = True


def render_text(text: str) -> str:
    return text.replace("$", r"\$")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(render_text(message["content"]))

audio_recording = st.audio_input(
    "Voice question",
    key="voice_question",
    label_visibility="collapsed",
    width="stretch",
)
if audio_recording:
    audio_bytes = audio_recording.getvalue()
    recording_id = sha256(audio_bytes).hexdigest()
    if st.session_state.get("last_recording_id") == recording_id:
        audio_recording = None
    else:
        st.session_state.last_recording_id = recording_id

if audio_recording:
    files = {
        "audio": (
            audio_recording.name or "voice-question.wav",
            audio_bytes,
            audio_recording.type or "audio/wav",
        )
    }
    response = requests.post(f"{API_URL}/transcribe", files=files, timeout=60)
    if response.ok:
        st.session_state.voice_text = response.json()["text"]
    else:
        st.error(response.text)

default_prompt = st.session_state.pop("voice_text", "")
prompt = st.chat_input("Ask for recommendations, reviews, prices, or policies")
st.markdown(
    """
    <div class="sample-prompts">
        <span>Find budget smartphones under $500.</span>
        <span>Summarize customer reviews for iPhone 15.</span>
        <span>Compare Samsung S24 and Google Pixel 8.</span>
        <span>Where can I get the best deal on wireless headphones?</span>
    </div>
    """,
    unsafe_allow_html=True,
)
if default_prompt:
    prompt = default_prompt

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(render_text(prompt))

    payload = {
        "query": prompt,
        "session_id": st.session_state.session_id,
        "customer_preferences": {},
    }
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = requests.post(f"{API_URL}/chat", json=payload, timeout=90)
        if response.ok:
            data = response.json()
            st.session_state.session_id = data["session_id"]
            st.query_params["session_id"] = data["session_id"]
            st.markdown(render_text(data["answer"]))
            with st.expander(f"Routed to {data['agent']}"):
                st.json(data["sources"])
                if data["pii_redacted"]:
                    st.info("PII was redacted before processing or display.")
            st.session_state.messages.append({"role": "assistant", "content": data["answer"]})
        else:
            st.error(response.text)
