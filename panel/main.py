from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
import sqlite3
import os
import httpx
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import secrets
from functools import lru_cache
from dotenv import load_dotenv

# 載入 .env 文件
load_dotenv()

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ctf.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 配置類
class Config:
    # 基本配置
    DB_PATH = os.getenv("DB_PATH", "database.db")
    SECRET_KEY = os.getenv("SECRET_KEY")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
    WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
    
    # 系統限制
    MAX_TEAMS = int(os.getenv("MAX_TEAMS", "9"))
    MAX_LEVELS = int(os.getenv("MAX_LEVELS", "3"))
    RATE_LIMIT_ATTEMPTS = int(os.getenv("RATE_LIMIT_ATTEMPTS", "5"))
    
    @classmethod
    def validate_config(cls):
        """驗證配置"""
        if not cls.SECRET_KEY:
            cls.SECRET_KEY = secrets.token_urlsafe(32)
            logger.warning("SECRET_KEY not set in environment. Generated temporary key. Please set SECRET_KEY in .env file!")
        
        if len(cls.SECRET_KEY) < 32:
            logger.warning("SECRET_KEY should be at least 32 characters long for better security!")
        
        if cls.ADMIN_PASSWORD == "admin123":
            logger.warning("Using default admin password! Please change ADMIN_PASSWORD in .env file!")
        
        if not cls.WEBHOOK_URL:
            logger.warning("DISCORD_WEBHOOK_URL not set. Discord notifications will be disabled.")
        
        return True

# 輸入驗證函數
def validate_team(team: int) -> int:
    """驗證團隊編號"""
    if not isinstance(team, int) or not 1 <= team <= Config.MAX_TEAMS:
        raise ValueError(f'Team number must be between 1 and {Config.MAX_TEAMS}')
    return team

def validate_flag(flag: str) -> str:
    """驗證 flag 格式"""
    if not flag or not isinstance(flag, str):
        raise ValueError('Flag cannot be empty')
    
    flag = flag.strip()
    if len(flag) == 0:
        raise ValueError('Flag cannot be empty')
    if len(flag) > 100:
        raise ValueError('Flag too long')
    return flag

# 數據庫管理類
class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """初始化數據庫"""
        try:
            if not os.path.exists(self.db_path):
                conn = sqlite3.connect(self.db_path)
                c = conn.cursor()
                
                # 創建進度表
                c.execute('''
                    CREATE TABLE progress (
                        team INTEGER PRIMARY KEY,
                        level INTEGER DEFAULT 0,
                        last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 創建提交記錄表
                c.execute('''
                    CREATE TABLE submissions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        team INTEGER,
                        level INTEGER,
                        flag TEXT,
                        is_correct BOOLEAN,
                        submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 創建速率限制表
                c.execute('''
                    CREATE TABLE rate_limits (
                        team_level TEXT PRIMARY KEY,
                        attempts INTEGER DEFAULT 0,
                        last_attempt DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 初始化團隊數據
                for team in range(1, Config.MAX_TEAMS + 1):
                    c.execute('INSERT INTO progress (team, level) VALUES (?, ?)', (team, 0))
                
                conn.commit()
                conn.close()
                logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    def get_connection(self):
        """獲取數據庫連接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_team_level(self, team: int) -> int:
        """獲取團隊當前等級"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute('SELECT level FROM progress WHERE team = ?', (team,))
                row = c.fetchone()
                return row['level'] if row else 0
        except Exception as e:
            logger.error(f"Failed to get team level for team {team}: {e}")
            return 0
    
    def update_team_level(self, team: int, level: int) -> bool:
        """更新團隊等級"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute(
                    'UPDATE progress SET level = ?, last_updated = CURRENT_TIMESTAMP WHERE team = ?',
                    (level, team)
                )
                conn.commit()
                return c.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to update team level for team {team}: {e}")
            return False
    
    def record_submission(self, team: int, level: int, flag: str, is_correct: bool):
        """記錄提交歷史"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute('''
                    INSERT INTO submissions (team, level, flag, is_correct)
                    VALUES (?, ?, ?, ?)
                ''', (team, level, flag, is_correct))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to record submission: {e}")
    
    def check_rate_limit(self, team: int, level: int) -> bool:
        """檢查速率限制"""
        try:
            key = f"{team}_{level}"
            now = datetime.now(timezone.utc)
            
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute('''
                    SELECT attempts, last_attempt FROM rate_limits WHERE team_level = ?
                ''', (key,))
                row = c.fetchone()
                
                if not row:
                    c.execute('''
                        INSERT INTO rate_limits (team_level, attempts, last_attempt)
                        VALUES (?, 1, ?)
                    ''', (key, now))
                    conn.commit()
                    return True
                
                last_attempt = datetime.fromisoformat(row['last_attempt'].replace('Z', '+00:00'))
                attempts = row['attempts']
                
                if (now - last_attempt).total_seconds() > 60:
                    c.execute('''
                        UPDATE rate_limits SET attempts = 1, last_attempt = ?
                        WHERE team_level = ?
                    ''', (now, key))
                    conn.commit()
                    return True
                
                if attempts >= Config.RATE_LIMIT_ATTEMPTS:
                    return False
                
                c.execute('''
                    UPDATE rate_limits SET attempts = attempts + 1, last_attempt = ?
                    WHERE team_level = ?
                ''', (now, key))
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            return True

# 挑戰管理類
class ChallengeManager:
    def __init__(self):
        self.flags = {
            1: "SITCON{c47_m03wwww}",
            2: "SITCON{5p4n15hhh}",
            3: "SITCON{pr0mp7_1nj3c710n}"
        }
        
        self.challenge_info = {
            1: {
                "title": "第一關：可愛的貓咪",
                "description": "請找出隱藏在網站中的旗子 (flag)。",
                "difficulty": "Easy",
                "points": 100
            },
            2: {
                "title": "第二關：西班牙挑戰",
                "description": "這是一個多語言挑戰，請正確輸入旗子。",
                "difficulty": "Medium",
                "points": 200
            },
            3: {
                "title": "第三關：Prompt Injection",
                "description": "破解 AI 防禦，獲取最後一個旗子。",
                "difficulty": "Hard",
                "points": 300
            }
        }
    
    @lru_cache(maxsize=128)
    def get_challenge_info(self, level: int) -> Dict[str, Any]:
        """獲取挑戰信息"""
        return self.challenge_info.get(level, {
            "title": "未知挑戰",
            "description": "",
            "difficulty": "Unknown",
            "points": 0
        })
    
    def validate_flag(self, level: int, flag: str) -> bool:
        """驗證 flag"""
        if level not in self.flags:
            return False
        
        expected_flag = self.flags[level]
        submitted_flag = flag.strip()
        
        return secrets.compare_digest(expected_flag, submitted_flag)

# Discord 通知管理類
class NotificationManager:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self.client = httpx.AsyncClient(timeout=10.0)
    
    async def send_submission_notification(self, team: int, level: int, flag: str, is_correct: bool):
        """發送提交通知"""
        try:
            now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            status_text = "✅ 正確" if is_correct else "❌ 錯誤"
            
            embed = {
                "title": "Flag 提交記錄",
                "color": 0x00ff00 if is_correct else 0xff0000,
                "fields": [
                    {"name": "小隊", "value": str(team), "inline": True},
                    {"name": "關卡", "value": str(level), "inline": True},
                    {"name": "狀態", "value": status_text, "inline": True},
                    {"name": "提交時間", "value": now, "inline": False},
                    {"name": "Flag", "value": f"`{flag}`", "inline": False}
                ]
            }
            
            payload = {"embeds": [embed]}
            
            response = await self.client.post(self.webhook_url, json=payload)
            response.raise_for_status()
            
        except Exception as e:
            logger.error(f"Failed to send Discord notification: {e}")
    
    async def close(self):
        """關閉HTTP客戶端"""
        await self.client.aclose()

# 全局實例
Config.validate_config()
db_manager = DatabaseManager(Config.DB_PATH)
challenge_manager = ChallengeManager()
notification_manager = NotificationManager(Config.WEBHOOK_URL) if Config.WEBHOOK_URL else None

# FastAPI 應用（不使用 lifespan）
app = FastAPI(
    title="CTF Challenge System",
    description="A secure and optimized CTF platform",
    version="2.0.0"
)

# 中間件
app.add_middleware(
    SessionMiddleware,
    secret_key=Config.SECRET_KEY,
    max_age=3600,  # 1小時過期
    https_only=False  # 在生產環境中設為 True
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# 靜態文件
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# 模板
templates = Jinja2Templates(directory="templates")

# 啟動和關閉事件
@app.on_event("startup")
async def startup_event():
    logger.info("CTF Server starting up...")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("CTF Server shutting down...")
    if notification_manager:
        await notification_manager.close()

# 依賴項
def get_current_team(request: Request) -> Optional[int]:
    """獲取當前團隊"""
    return request.session.get("team")

def require_team(team: int = Depends(get_current_team)) -> int:
    """要求已選擇團隊"""
    if not team:
        raise HTTPException(status_code=403, detail="請先選擇團隊")
    return team

def check_admin_auth(request: Request) -> bool:
    """檢查管理員權限"""
    return request.session.get("is_admin", False)

def require_admin(request: Request) -> bool:
    """要求管理員權限"""
    if not check_admin_auth(request):
        raise HTTPException(status_code=403, detail="需要管理員權限")
    return True

# 路由
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """首頁"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/set_team")
async def set_team(request: Request, team: int = Form(...)):
    """設置團隊"""
    try:
        validated_team = validate_team(team)
        request.session["team"] = validated_team
        logger.info(f"Team {team} logged in")
        return RedirectResponse("/challenge/1", status_code=303)
    except ValueError as e:
        logger.warning(f"Invalid team selection: {e}")
        raise HTTPException(status_code=400, detail="無效的團隊編號")

@app.get("/challenge/{level}", response_class=HTMLResponse)
async def challenge(
    request: Request,
    level: int,
    team: int = Depends(require_team)
):
    """挑戰頁面"""
    if not 1 <= level <= Config.MAX_LEVELS:
        raise HTTPException(status_code=404, detail="挑戰不存在")
    
    current_level = db_manager.get_team_level(team)
    
    if level > current_level + 1:
        raise HTTPException(status_code=403, detail="您尚未解鎖此挑戰")
    
    info = challenge_manager.get_challenge_info(level)
    
    return templates.TemplateResponse("challenge.html", {
        "request": request,
        "level": level,
        "info": info,
        "team": team,
        "current_level": current_level
    })

@app.post("/submit/{level}", response_class=HTMLResponse)
async def submit_flag(
    request: Request,
    level: int,
    flag: str = Form(...),
    team: int = Depends(require_team)
):
    """提交 flag"""
    try:
        # 驗證輸入
        validated_flag = validate_flag(flag)
        
        # 檢查關卡有效性
        if not 1 <= level <= Config.MAX_LEVELS:
            raise HTTPException(status_code=404, detail="挑戰不存在")
        
        # 檢查權限
        current_level = db_manager.get_team_level(team)
        if level > current_level + 1:
            raise HTTPException(status_code=403, detail="您尚未解鎖此挑戰")
        
        # 檢查速率限制
        if not db_manager.check_rate_limit(team, level):
            logger.warning(f"Rate limit exceeded for team {team}, level {level}")
            raise HTTPException(status_code=429, detail="提交太頻繁，請稍後再試")
        
        # 驗證 flag
        is_correct = challenge_manager.validate_flag(level, validated_flag)
        
        # 記錄提交
        db_manager.record_submission(team, level, validated_flag, is_correct)
        
        # 發送通知（異步，如果有配置 Webhook）
        if notification_manager:
            asyncio.create_task(
                notification_manager.send_submission_notification(
                    team, level, validated_flag, is_correct
                )
            )
        
        if is_correct:
            # 更新進度
            db_manager.update_team_level(team, level)
            logger.info(f"Team {team} completed level {level}")
            
            # 檢查是否完成所有挑戰
            if level == Config.MAX_LEVELS:
                return templates.TemplateResponse("success.html", {
                    "request": request,
                    "team": team
                })
            
            # 重定向到下一關
            return RedirectResponse(f"/challenge/{level + 1}", status_code=303)
        
        # 答錯，返回錯誤信息
        info = challenge_manager.get_challenge_info(level)
        return templates.TemplateResponse("challenge.html", {
            "request": request,
            "level": level,
            "info": info,
            "team": team,
            "current_level": current_level,
            "error": "旗子錯誤，請再試一次！"
        })
        
    except ValueError as e:
        # 輸入驗證錯誤
        info = challenge_manager.get_challenge_info(level)
        return templates.TemplateResponse("challenge.html", {
            "request": request,
            "level": level,
            "info": info,
            "team": team,
            "current_level": db_manager.get_team_level(team),
            "error": f"輸入錯誤：{e}"
        })
    except Exception as e:
        logger.error(f"Unexpected error in submit_flag: {e}")
        raise HTTPException(status_code=500, detail="服務器內部錯誤")

@app.get("/admin", response_class=HTMLResponse)
async def admin_login(request: Request):
    """管理員登入頁面"""
    if check_admin_auth(request):
        return RedirectResponse("/leaderboard", status_code=303)
    
    return templates.TemplateResponse("admin_login.html", {
        "request": request
    })

@app.post("/admin/login")
async def admin_login_post(request: Request, password: str = Form(...)):
    """管理員登入處理"""
    if secrets.compare_digest(password, Config.ADMIN_PASSWORD):
        request.session["is_admin"] = True
        logger.info("Admin logged in successfully")
        return RedirectResponse("/leaderboard", status_code=303)
    else:
        logger.warning("Failed admin login attempt")
        return templates.TemplateResponse("admin_login.html", {
            "request": request,
            "error": "密碼錯誤"
        })

@app.post("/admin/logout")
async def admin_logout(request: Request):
    """管理員登出"""
    request.session.pop("is_admin", None)
    return RedirectResponse("/", status_code=303)

@app.get("/leaderboard", response_class=HTMLResponse)
async def leaderboard(request: Request, _: bool = Depends(require_admin)):
    """排行榜（僅管理員可見）"""
    try:
        with db_manager.get_connection() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT team, level, last_updated
                FROM progress
                WHERE level > 0
                ORDER BY level DESC, last_updated ASC
            ''')
            teams = c.fetchall()
            
            # 獲取總提交統計
            c.execute('''
                SELECT 
                    team,
                    COUNT(*) as total_attempts,
                    SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) as correct_attempts
                FROM submissions
                GROUP BY team
                ORDER BY team
            ''')
            stats = {row['team']: {
                'total_attempts': row['total_attempts'],
                'correct_attempts': row['correct_attempts']
            } for row in c.fetchall()}
        
        return templates.TemplateResponse("leaderboard.html", {
            "request": request,
            "teams": teams,
            "stats": stats
        })
    except Exception as e:
        logger.error(f"Failed to load leaderboard: {e}")
        raise HTTPException(status_code=500, detail="無法載入排行榜")

# 錯誤處理
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return HTMLResponse("<h1>404 - Page Not Found</h1>", status_code=404)

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    logger.error(f"Internal server error: {exc}")
    return HTMLResponse("<h1>500 - Internal Server Error</h1>", status_code=500)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
