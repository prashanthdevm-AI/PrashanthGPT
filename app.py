import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import streamlit as st
from openai import OpenAI, OpenAIError
from streamlit.errors import StreamlitSecretNotFoundError


MODEL = "openai/gpt-4o-mini"
CHATS_DIR = Path(__file__).parent / "chats"
SYSTEM_PROMPT = "You are a helpful assistant. Give clear, friendly answers."


def load_chats():
    """Load valid conversation files from the local chats folder."""
    try:
        CHATS_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        st.error(f"Could not open the chats folder: {error}")
        st.stop()

    chats = {}

    for chat_file in CHATS_DIR.glob("*.json"):
        try:
            chat = json.loads(chat_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            st.warning(f"Could not read {chat_file.name}: {error}")
            continue

        chat_id = chat.get("id") if isinstance(chat, dict) else None
        valid_id = (
            isinstance(chat_id, str)
            and len(chat_id) == 32
            and all(character in "0123456789abcdef" for character in chat_id)
            and chat_file.stem == chat_id
        )
        valid_messages = (
            isinstance(chat, dict)
            and isinstance(chat.get("messages"), list)
            and all(
                isinstance(message, dict)
                and message.get("role") in ("user", "assistant")
                and isinstance(message.get("content"), str)
                for message in chat["messages"]
            )
        )

        if not valid_id or not valid_messages:
            st.warning(f"Skipping invalid conversation file: {chat_file.name}")
            continue

        chats[chat_id] = {
            "id": chat_id,
            "title": chat.get("title", "New chat")
            if isinstance(chat.get("title"), str)
            else "New chat",
            "messages": chat["messages"],
            "updated_at": chat.get("updated_at", "")
            if isinstance(chat.get("updated_at", ""), str)
            else "",
        }

    return chats


def save_chat(chat):
    """Save one conversation as a JSON file."""
    try:
        CHATS_DIR.mkdir(parents=True, exist_ok=True)
        chat_file = CHATS_DIR / f"{chat['id']}.json"
        chat_file.write_text(
            json.dumps(chat, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as error:
        st.error(f"Could not save this conversation: {error}")


def create_chat():
    chat_id = uuid4().hex
    chat = {
        "id": chat_id,
        "title": "New chat",
        "messages": [],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    st.session_state.chats[chat_id] = chat
    st.session_state.active_chat_id = chat_id
    save_chat(chat)


def get_api_key():
    try:
        return st.secrets["OPENROUTER_API_KEY"]
    except (KeyError, StreamlitSecretNotFoundError):
        return None


def stream_text(response_stream):
    for chunk in response_stream:
        if chunk.choices:
            text = chunk.choices[0].delta.content
            if text:
                yield text


def render_sidebar():
    with st.sidebar:
        st.header("Conversations")
        if st.button("＋ New chat", use_container_width=True):
            create_chat()
            st.rerun()

        for chat in sorted(
            st.session_state.chats.values(),
            key=lambda item: item.get("updated_at", ""),
            reverse=True,
        ):
            select_column, delete_column = st.columns([5, 1])
            with select_column:
                label = chat["title"] or "New chat"
                if chat["id"] == st.session_state.active_chat_id:
                    label = f"● {label}"
                if st.button(
                    label,
                    key=f"select_{chat['id']}",
                    use_container_width=True,
                ):
                    st.session_state.active_chat_id = chat["id"]
                    st.rerun()
            with delete_column:
                if st.button("×", key=f"delete_{chat['id']}", help="Delete chat"):
                    chat_file = CHATS_DIR / f"{chat['id']}.json"
                    try:
                        chat_file.unlink(missing_ok=True)
                    except OSError as error:
                        st.error(f"Could not delete this conversation: {error}")
                    else:
                        del st.session_state.chats[chat["id"]]
                        if chat["id"] == st.session_state.active_chat_id:
                            if st.session_state.chats:
                                st.session_state.active_chat_id = next(
                                    iter(st.session_state.chats)
                                )
                            else:
                                create_chat()
                        st.rerun()

        st.divider()
        st.caption(
            "Chats are shared by everyone using this deployment. Visitors can "
            "see and delete them. Streamlit Cloud may clear local files after a restart."
        )


def main():
    st.set_page_config(page_title="PrashanthGPT", page_icon="💬")
    st.title("PrashanthGPT")
    st.caption(f"Chatting with {MODEL} through OpenRouter")

    if "chats" not in st.session_state:
        st.session_state.chats = load_chats()
    if not st.session_state.chats:
        create_chat()
    elif st.session_state.get("active_chat_id") not in st.session_state.chats:
        st.session_state.active_chat_id = next(iter(st.session_state.chats))

    render_sidebar()
    active_chat = st.session_state.chats[st.session_state.active_chat_id]

    for message in active_chat["messages"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    st.caption("This chatbot was built by Prashanth Dev M.")

    user_text = st.chat_input("Send a message")
    if not user_text:
        return

    with st.chat_message("user"):
        st.markdown(user_text)
    active_chat["messages"].append({"role": "user", "content": user_text})
    if active_chat["title"] == "New chat":
        active_chat["title"] = user_text.strip().replace("\n", " ")[:40] or "New chat"
    active_chat["updated_at"] = datetime.now(timezone.utc).isoformat()
    save_chat(active_chat)

    api_key = get_api_key()
    if not isinstance(api_key, str) or not api_key.strip():
        st.error(
            "The OpenRouter API key is missing. Add OPENROUTER_API_KEY to "
            ".streamlit/secrets.toml, then restart the app."
        )
        st.stop()

    request_messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *active_chat["messages"][-10:],
    ]
    client = OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
    )

    try:
        with st.chat_message("assistant"):
            response = client.chat.completions.create(
                model=MODEL,
                messages=request_messages,
                temperature=0.7,
                max_tokens=512,
                stream=True,
            )
            assistant_text = st.write_stream(stream_text(response))
    except OpenAIError as error:
        st.error(f"The OpenRouter request failed: {error}")
        return

    if assistant_text:
        active_chat["messages"].append(
            {"role": "assistant", "content": assistant_text}
        )
        active_chat["updated_at"] = datetime.now(timezone.utc).isoformat()
        save_chat(active_chat)


if __name__ == "__main__":
    main()
