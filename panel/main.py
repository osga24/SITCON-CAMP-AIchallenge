from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import sqlite3
import os
import httpx
from datetime import datetime

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="s3cr3tk3y")
templates = Jinja2Templates(directory="templates")

DB_PATH = "database.db"

# Flag設定
FLAGS = {
    1: "SITCON{c47_m03wwww}",
    2: "SITCON{5p4n15hhh}",
    3: "SITCON{pr0mp7_1nj3c710n}"
}

# 題目資訊
CHALLENGE_INFO = {
    1: {
        "title": "第一關：可愛的貓咪",
        "description": "請找出隱藏在網站中的旗子 (flag)。"
    },
    2: {
        "title": "第二關：西班牙挑戰",
        "description": "這是一個多語言挑戰，請正確輸入旗子。"
    },
    3: {
        "title": "第三關：Prompt Injection",
        "description": "破解 AI 防禦，獲取最後一個旗子。"
    }
}

WEBHOOK_URL = "https://discord.com/api/webhooks/1391456740549197845/VtSk-vh0TS4TVky1xYeKwbFEj5FdjgQCw87Gfl8AsssM_hu19TY19ySM0PcRS7wlIhIY"

def init_db():
    if not os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE progress (
                team INTEGER PRIMARY KEY,
                level INTEGER DEFAULT 0
            )
        ''')
        for team in range(1, 10):
            c.execute('INSERT INTO progress (team, level) VALUES (?, ?)', (team, 0))
        conn.commit()
        conn.close()

def get_team_level(team: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT level FROM progress WHERE team = ?', (team,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

def update_team_level(team: int, level: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE progress SET level = ? WHERE team = ?', (level, team))
    conn.commit()
    conn.close()

init_db()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/set_team")
async def set_team(request: Request, team: int = Form(...)):
    if team < 1 or team > 9:
        return HTMLResponse("Invalid team number.", status_code=400)
    request.session["team"] = team
    return RedirectResponse("/challenge/1", status_code=303)

@app.get("/challenge/{level}", response_class=HTMLResponse)
async def challenge(request: Request, level: int):
    team = request.session.get("team")
    if not team:
        return RedirectResponse("/", status_code=303)
    current_level = get_team_level(team)
    if level > current_level + 1:
        return HTMLResponse("You have not unlocked this challenge yet.", status_code=403)
    if level > 3:
        return HTMLResponse("No such challenge.", status_code=404)
    info = CHALLENGE_INFO.get(level, {"title": "未知挑戰", "description": ""})
    return templates.TemplateResponse("challenge.html", {
        "request": request,
        "level": level,
        "info": info
    })

@app.post("/submit/{level}", response_class=HTMLResponse)
async def submit_flag(request: Request, level: int, flag: str = Form(...)):
    team = request.session.get("team")
    if not team:
        return RedirectResponse("/", status_code=303)
    current_level = get_team_level(team)
    if level > current_level + 1:
        return HTMLResponse("You have not unlocked this challenge yet.", status_code=403)

    is_correct = FLAGS.get(level) == flag.strip()

    # 發送 Discord Webhook
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    status_text = "✅ 正確" if is_correct else "❌ 錯誤"
    content = (
        f"**Flag 提交記錄**\n"
        f"- 小隊: {team}\n"
        f"- 關卡: {level}\n"
        f"- 狀態: {status_text}\n"
        f"- 提交時間: {now}\n"
        f"- Flag: `{flag.strip()}`"
    )
    async with httpx.AsyncClient() as client:
        await client.post(WEBHOOK_URL, json={"content": content})

    if is_correct:
        update_team_level(team, level)
        if level == 3:
            return templates.TemplateResponse("success.html", {"request": request, "team": team})
        return RedirectResponse(f"/challenge/{level + 1}", status_code=303)

    # 答錯，回到同一頁
    info = CHALLENGE_INFO.get(level, {"title": "未知挑戰", "description": ""})
    return templates.TemplateResponse("challenge.html", {
        "request": request,
        "level": level,
        "info": info,
        "error": "旗子錯誤，請再試一次！"
    })
