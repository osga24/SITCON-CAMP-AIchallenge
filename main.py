from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import google.generativeai as genai
import os
from typing import List, Dict
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

app = FastAPI(title="SITCON CAMP Gemini Chat")

# 配置靜態文件和模板
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 配置Gemini API
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("請設置 GEMINI_API_KEY 環境變數")

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.0-flash')

# 存儲對話歷史和系統配置
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
        # 獲取或創建會話
        session_id = chat_message.session_id
        if session_id not in chat_sessions:
            chat_sessions[session_id] = []
            
        # 獲取系統配置
        config = system_configs.get(session_id, {
            "hostname": "ubuntu",
            "username": "sitcon", 
            "working_directory": "/home/sitcon",
            "root_password": "",
            "sudo_enabled": True
        })
        
        # 添加用戶消息到歷史
        chat_sessions[session_id].append({
            "role": "user",
            "content": chat_message.message
        })
        
        # 構建對話上下文
        context = ""
        for msg in chat_sessions[session_id][-10:]:  # 只保留最近10條消息
            if msg["role"] == "user":
                context += f"用戶輸入: {msg['content']}\n"
            else:
                context += f"終端輸出: {msg['content']}\n"
          # 構建系統提示
        system_prompt = f"""你是一個 Ubuntu Linux 終端模擬器。你需要：

1. 完全模擬真實的 Ubuntu 終端行為
2. 當前用戶配置：
   - 主機名: {config['hostname']}
   - 用戶名: {config['username']}
   - 當前目錄: {config['working_directory']}
   - sudo 權限: {'已啟用' if config['sudo_enabled'] else '已禁用'}
   - root 密碼: {'已設置' if config['root_password'] else '未設置'}

3. 模擬規則：
   - 首先顯示命令提示符和用戶輸入的命令
   - 然後顯示命令的執行結果
   - 最後顯示新的命令提示符等待下一個命令
   - 正確回應 Linux 命令（ls, cd, pwd, cat, sudo 等）
   - 如果用戶使用 sudo 命令：
     * 如果已設置root密碼，顯示 "[sudo] password for {config['username']}:" 並等待用戶輸入密碼
     * 如果用戶輸入的密碼與設置的root密碼匹配，執行sudo命令
     * 如果密碼錯誤，顯示 "Sorry, try again." 
     * 如果未設置密碼但sudo_enabled為True，直接執行命令
   - 模擬文件系統結構和權限
   - 對無效命令返回適當的錯誤信息
   - 保持會話狀態（如當前目錄）

4. 重要格式要求：
   - 直接輸出純文本，不要使用任何markdown語法
   - 不要使用```text```或```bash```等代碼塊標記
   - 不要使用**粗體**或*斜體*等markdown格式
   - 輸出格式應該像這樣：
     {config['username']}@{config['hostname']}:{config['working_directory']}$ [用戶命令]
     [命令執行結果]
     {config['username']}@{config['hostname']}:{config['working_directory']}$

5. 特殊處理：
   - 如果用戶輸入包含 "config:" 開頭，這是系統配置命令，不要作為終端命令處理
   - 始終以終端輸出的格式回應，不要額外說明

對話歷史：
{context}

請處理最新的命令並返回終端輸出："""# 發送消息給Gemini
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
    print("🚀 啟動 SITCON CAMP Gemini Chat Terminal")
    print("📝 確保已設置 GEMINI_API_KEY 環境變數")
    print("🌐 瀏覽器打開: http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)