# PrashanthGPT

A beginner-friendly Streamlit chatbot that uses OpenRouter's Chat Completions
API with `openai/gpt-4o-mini`.

## Features

- Keeps active conversations in Streamlit session state and saves them as JSON
  files in `chats/` so they can be restored after a page refresh.
- Lets you create, switch between, and delete conversations from the sidebar.
- Includes controls for temperature, maximum output tokens, recent context
  length, and response streaming.
- Applies system prompt edits only after you click **Save**.
- Reads `OPENROUTER_API_KEY` from Streamlit secrets; the key is not stored in
  the app code.

There is no database, account system, or file upload feature. Everyone using
the same deployed app can see and delete its saved chats. Streamlit Community
Cloud may clear local files after a restart. Visitors may also use your
configured API key and consume its credits, so only share the demo with people
you trust.

## Run locally

1. Install Python 3.11 or newer.
2. From this folder, install the dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

3. Open `.streamlit/secrets.toml` and replace `paste-your-key-here` with your
   own OpenRouter API key. Never commit or share this file.
4. Start the app:

   ```bash
   python -m streamlit run app.py
   ```

The `.gitignore` excludes secrets, environment files, virtual environments,
Python cache files, and saved chat JSON files.

## Deploy on Streamlit Community Cloud

Deploy `app.py` from this folder, then add
`OPENROUTER_API_KEY = "your-own-openrouter-key"` in the app's Streamlit
**Settings > Secrets**. Do not upload `.streamlit/secrets.toml` or saved chat
files.
