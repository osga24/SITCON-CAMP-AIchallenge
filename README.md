# SITCON CAMP AI Challenge Platform

This project is a multi-component platform for running and managing an AI-powered CTF/terminal challenge event, including a challenge server, a participant panel, and a history viewer.

## Project Structure

- **chall/**: Main challenge server (FastAPI + OpenAI + MongoDB)
  - Provides a terminal-like chat interface for teams to interact with AI-powered challenges.
  - Supports multiple challenge schemas and prompt files.
  - Stores chat history and results in MongoDB.
- **panel/**: Participant panel (FastAPI + SQLite)
  - For teams/participants to select their team, view and attempt challenges, and submit flags.
  - Each team can only see their own progress and submit flags for each challenge.
  - There is **no web UI for viewing submission history**; all write records (progress, submissions) are only accessible via direct SQLite access.
- **history/**: Web frontend for viewing challenge history (Next.js/React)
  - Allows browsing of team and challenge histories.
  - Modern web UI.

---

## 1. Challenge Server (`chall/`)

### Features

- FastAPI backend serving a chat-based terminal challenge.
- Uses OpenAI API for AI responses (configurable prompt).
- MongoDB for storing chat and challenge history.
- Supports command-line flags for schema, prompt file, and port.

### Requirements

- Python 3.8+
- MongoDB instance
- OpenAI API key (or compatible endpoint)
- Install dependencies:
  ```bash
  uv pip install -r requirements.txt
  ```

### Environment Variables

- `API_KEY`: Your OpenAI API key.
- `MONGODB`: MongoDB connection string (e.g., `mongodb://localhost:27017`).

### Running the Server

Example:
```bash
uv run main.py --schema chall1 --promptfile prompts/basic_prompt_1.txt --port 30007
```

- `--schema`: MongoDB collection name (must be `chall1`, `chall2`, or `chall3` for the history panel to show)
- `--promptfile`: Prompt file location (default: prompts/basic_prompt_1.txt)
- `--port`: Port to run the server on (default: 30009)

---

## 2. Participant Panel (`panel/`)

### Features

- FastAPI backend with Jinja2 templates.
- **For participants/teams**: select team, view challenges, submit flags, and progress through levels.
- SQLite database for team progress and submissions.
- Discord webhook support for notifications.
- **No web UI for viewing submission history**; all write records are only accessible via direct SQLite access.

### Requirements

- Python 3.8+
- Install dependencies:
  ```bash
  uv pip install -r requirements.txt
  ```

### Environment Variables

- `SECRET_KEY`: Secret for session management.
- `ADMIN_PASSWORD`: Admin login password (for admin-only endpoints).
- `DB_PATH`: Path to SQLite database (default: database.db).
- `DISCORD_WEBHOOK_URL`: (Optional) Discord webhook for notifications.

### Running the Panel

```bash
uv run main.py
```

---

## 3. History Viewer (`history/`)

### Features

- Next.js/React frontend for browsing challenge and team histories.
- Modern, responsive UI.

### Requirements

- Node.js 18+
- Install dependencies:
  ```bash
  npm install
  # or
  pnpm install
  ```

### Running the Viewer

```bash
npm run dev
# or
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## Example Deployment

1. Set up MongoDB and create a `.env` file in `chall/` and `history/` with your `MONGODB` and `API_KEY` connection string. (See `.env.example`)
2. Start the challenge server:
   ```bash
   uv run main.py --schema chall1 --promptfile prompts/basic_prompt_1.txt --port 30007
   ```
3. Start the participant panel (set up `.env` as needed):
   ```bash
   uv run main.py
   ```
4. Start the history viewer:
   ```bash
   pnpm run dev
   ```

---

## Notes

- You can customize the challenge prompt by editing or providing a different prompt file in `chall/prompts/`.
- The challenge server and panel are independent FastAPI apps; the history viewer is a separate Next.js app.
- For production, use a process manager (e.g., systemd, pm2) and a reverse proxy (e.g., nginx).
