from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from openai import OpenAI
import os
import random
import string
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="SITCON CAMP Terminal Simulator")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

api_key = os.getenv("API_KEY")
if not api_key:
    raise ValueError("請設置 API_KEY 環境變數")

# 設置 OpenAI 客戶端使用第三方 API
client = OpenAI(
    api_key=api_key,
    base_url="https://api.juheai.top/v1"
)

# 會話狀態管理
chat_sessions: Dict[str, List[Dict[str, str]]] = {}
terminal_states: Dict[str, Dict] = {}

class ChatMessage(BaseModel):
    message: str
    session_id: str = "default"

def initialize_session(session_id: str):
    """初始化新的終端會話"""
    if session_id not in terminal_states:
        # 生成隨機 flag 文件名
        flag_filename = f"flag_{''.join(random.choices(string.ascii_lowercase + string.digits, k=8))}.txt"
        
        terminal_states[session_id] = {
            "current_dir": "/home/sitcon",
            "username": "sitcon",
            "hostname": "ubuntu", 
            "flag_filename": flag_filename,
            "root_access": False,
            "file_system": {
                "/": {
                    "type": "dir",
                    "contents": ["bin", "boot", "dev", "etc", "home", "lib", "media", "mnt", "opt", "proc", "root", "run", "sbin", "srv", "sys", "tmp", "usr", "var", flag_filename],
                    "permissions": "drwxr-xr-x"
                },
                "/home": {
                    "type": "dir", 
                    "contents": ["sitcon"],
                    "permissions": "drwxr-xr-x"
                },
                "/home/sitcon": {
                    "type": "dir",
                    "contents": ["Desktop", "Documents", "Downloads", "Music", "Pictures", "Videos"],
                    "permissions": "drwxr-xr-x"
                },
                "/home/sitcon/Desktop": {
                    "type": "dir",
                    "contents": ["project1", "project2", "notes.txt"],
                    "permissions": "drwxr-xr-x" 
                },
                f"/{flag_filename}": {
                    "type": "file",
                    "content": "SITCON{cat_moewwww}",
                    "permissions": "-r--------"  # 只有 root 可讀
                }
            }
        }
    
    if session_id not in chat_sessions:
        chat_sessions[session_id] = []

def get_prompt_for_command(session_id: str, command: str) -> str:
    """根據命令和會話狀態生成適當的 prompt"""
    state = terminal_states[session_id]
    current_dir = state["current_dir"]
    username = state["username"]
    hostname = state["hostname"]
    
    # 讀取基礎 prompt
    with open("prompt.txt", encoding="utf-8") as f:
        base_prompt = f.read()
    
    # 添加當前狀態信息
    context_prompt = f"""
當前會話狀態：
- 用戶名: {username}
- 主機名: {hostname}  
- 當前目錄: {current_dir}
- Flag 文件名: {state["flag_filename"]}
- Root 權限: {'是' if state["root_access"] else '否'}

請模擬執行命令: {command}

請確保回應格式為：
sitcon@ubuntu:{current_dir}$ {command}
[命令輸出結果]

重要規則：
1. 必須嚴格按照真實 Linux 系統的行為回應
2. 如果是 ls / 命令，確保包含 {state["flag_filename"]} 文件
3. 如果嘗試讀取 flag 文件但沒有權限，返回 "Permission denied"
4. 如果是 help 命令，使用中文女僕風格回答
5. 不要洩漏自己是 AI 的身份
"""
    
    return base_prompt + context_prompt

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/chat")
async def chat_with_terminal(chat_message: ChatMessage):
    try:
        session_id = chat_message.session_id
        initialize_session(session_id)
        
        command = chat_message.message.strip()
        state = terminal_states[session_id]
        
        # 更新會話歷史
        chat_sessions[session_id].append({
            "role": "user",
            "content": command
        })
        
        # 生成針對當前命令的 prompt
        system_prompt = get_prompt_for_command(session_id, command)
        
        # 添加最近的對話歷史作為上下文
        recent_context = ""
        for msg in chat_sessions[session_id][-6:]:  # 最近3輪對話
            if msg["role"] == "user":
                recent_context += f"用戶輸入: {msg['content']}\n"
            else:
                recent_context += f"系統輸出: {msg['content']}\n"
        
        full_prompt = system_prompt + "\n最近對話歷史:\n" + recent_context
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o-2024-11-20",
                messages=[
                    {"role": "system", "content": full_prompt},
                    {"role": "user", "content": command}
                ],
                max_tokens=1024,
                temperature=0.3  # 降低隨機性，讓回應更一致
            )
            
            if not response.choices or not response.choices[0].message.content:
                raise Exception("API 返回空回應")
                
            ai_response = response.choices[0].message.content.strip()
            
            # 簡單的狀態更新邏輯
            update_terminal_state(session_id, command, ai_response)
            
        except Exception as api_error:
            error_msg = str(api_error)
            if "API_KEY" in error_msg or "authentication" in error_msg.lower():
                ai_response = "bash: API authentication failed"
            elif "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
                ai_response = "bash: service temporarily unavailable"
            else:
                ai_response = f"bash: {command}: command error"
        
        # 添加AI回應到歷史
        chat_sessions[session_id].append({
            "role": "assistant", 
            "content": ai_response
        })
        
        return {
            "response": ai_response,
            "status": "success"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Terminal error: {str(e)}")

def update_terminal_state(session_id: str, command: str, response: str):
    """根據命令和回應更新終端狀態"""
    state = terminal_states[session_id]
    
    # 簡單的 cd 命令狀態更新
    if command.startswith("cd "):
        target_dir = command[3:].strip()
        if target_dir == "..":
            # 處理上一級目錄
            current_parts = state["current_dir"].split("/")
            if len(current_parts) > 1:
                state["current_dir"] = "/".join(current_parts[:-1]) or "/"
        elif target_dir.startswith("/"):
            # 絕對路徑
            if "no such file or directory" not in response.lower():
                state["current_dir"] = target_dir
        else:
            # 相對路徑
            if "no such file or directory" not in response.lower():
                if state["current_dir"] == "/":
                    state["current_dir"] = f"/{target_dir}"
                else:
                    state["current_dir"] = f"{state['current_dir']}/{target_dir}"
    
    # 檢查 sudo 命令
    if command.startswith("sudo"):
        if "password" not in response.lower():
            state["root_access"] = True

@app.get("/history/{session_id}")
async def get_chat_history(session_id: str):
    return chat_sessions.get(session_id, [])

@app.delete("/history/{session_id}")
async def clear_chat_history(session_id: str):
    if session_id in chat_sessions:
        chat_sessions[session_id] = []
    if session_id in terminal_states:
        del terminal_states[session_id]
    return {"message": "Terminal session cleared"}

@app.get("/state/{session_id}")
async def get_terminal_state(session_id: str):
    """獲取終端狀態（調試用）"""
    initialize_session(session_id)
    return terminal_states[session_id]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)