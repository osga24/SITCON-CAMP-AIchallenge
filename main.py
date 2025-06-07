from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import google.generativeai as genai
import os
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="SITCON CAMP Gemini Chat")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("請設置 GEMINI_API_KEY 環境變數")

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.0-flash')


chat_sessions: Dict[str, List[Dict[str, str]]] = {}
system_configs: Dict[str, Dict] = {}

class ChatMessage(BaseModel):
    message: str
    session_id: str = "default"

class SystemConfig(BaseModel):
    session_id: str = "default"
    root_password: str = ""
    hostname: str = "ubuntu"
    username: str = "sitcon"
    working_directory: str = "/home/sitcon"
    sudo_enabled: bool = True
    os_version: str = "Ubuntu 22.04.3 LTS"
    shell: str = "/bin/bash"
    timezone: str = "Asia/Taipei"
    locale: str = "zh_TW.UTF-8"
    packages_installed: List[str] = []
    services_running: List[str] = ["ssh", "systemd", "networkd"]
    network_interface: str = "eth0"
    ip_address: str = "192.168.1.100"
    memory_total: str = "4096MB"
    disk_space: str = "50GB"

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/chat")
async def chat_with_gemini(chat_message: ChatMessage):
    try:
        session_id = chat_message.session_id
        if session_id not in chat_sessions:
            chat_sessions[session_id] = []
            
        config = system_configs.get(session_id, {
            "hostname": "ubuntu",
            "username": "sitcon", 
            "working_directory": "/home/sitcon",
            "root_password": "",
            "sudo_enabled": True
        })
        
        chat_sessions[session_id].append({
            "role": "user",
            "content": chat_message.message
        })
        
        context = ""
        for msg in chat_sessions[session_id][-10:]:
            if msg["role"] == "user":
                context += f"用戶輸入: {msg['content']}\n"
            else:
                context += f"終端輸出: {msg['content']}\n"
        with open("prompt.txt",encoding="utf-8")as f:
            system_prompt = f.read() + context
            
        try:
            response = model.generate_content(
                f"{system_prompt}\n\n用戶命令: {chat_message.message}"
            )
            
            if not response.text:
                raise Exception("Gemini API 返回空回應")
                
        except Exception as gemini_error:
            # 處理Gemini API特定錯誤
            error_msg = str(gemini_error)
            if "API_KEY" in error_msg:
                raise Exception("API Key 無效或未設置")
            elif "quota" in error_msg.lower():
                raise Exception("API 配額已用完")
            else:
                raise Exception(f"Gemini API 錯誤: {error_msg}")
        
        # 添加AI回應到歷史
        ai_response = response.text
        chat_sessions[session_id].append({
            "role": "assistant", 
            "content": ai_response
        })
        
        return {
            "response": ai_response,
            "status": "success"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"錯誤: {str(e)}")

@app.get("/history/{session_id}")
async def get_chat_history(session_id: str):
    return chat_sessions.get(session_id, [])

@app.delete("/history/{session_id}")
async def clear_chat_history(session_id: str):
    if session_id in chat_sessions:
        chat_sessions[session_id] = []
    return {"message": "對話歷史已清除"}

@app.post("/config")
async def set_system_config(config: SystemConfig):
    """設置系統配置"""
    system_configs[config.session_id] = {
        "hostname": config.hostname,
        "username": config.username,
        "working_directory": config.working_directory,
        "root_password": config.root_password,
        "sudo_enabled": config.sudo_enabled
    }
    return {"message": "系統配置已更新"}

@app.get("/config/{session_id}")
async def get_system_config(session_id: str):
    """獲取系統配置"""
    config = system_configs.get(session_id, {
        "hostname": "ubuntu",
        "username": "sitcon",
        "working_directory": "/home/sitcon",
        "root_password": "",
        "sudo_enabled": True
    })
    return config

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, port=8000)