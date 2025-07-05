from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import openai
import os
import json
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="SITCON CAMP Terminal Simulator")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

api_key = os.getenv("API_KEY")
if not api_key:
    raise ValueError("請設置 API_KEY 環境變數")

openai.api_key = api_key
openai.api_base = "https://api.juheai.top/v1"

# 會話狀態管理
chat_sessions: Dict[str, List[Dict[str, str]]] = {}
terminal_states: Dict[str, Dict] = {}

class ChatMessage(BaseModel):
    message: str
    history: str

def get_prompt_for_command() -> str:
    
    # 讀取基礎 prompt
    with open("prompt.txt", encoding="utf-8") as f:
        base_prompt = f.read()
    
    return base_prompt 

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/chat")
async def chat_with_terminal(chat_message: ChatMessage):
    try:
        
        command = chat_message.message.strip()
        history = chat_message.history.strip()
        
        # 生成針對當前命令的 prompt
        system_prompt = get_prompt_for_command()
        
        full_prompt = [{"role": "system", "content": system_prompt + "\n\n用戶歷史指令紀錄：" + history},{"role": "user", "content": command}]
        
        try:
            response = openai.ChatCompletion.create(
                model="basic/gpt-4o-mini",
                messages=full_prompt,
                max_tokens=1024,
                temperature=0.3  # 降低隨機性，讓回應更一致
            )
            
            if not response.choices or not response.choices[0].message.content:
                raise Exception("API 返回空回應")
                
            ai_response = response.choices[0].message.content.strip()
            
        except Exception as api_error:
            error_msg = str(api_error)
            ai_response = error_msg
            # if "API_KEY" in error_msg or "authentication" in error_msg.lower():
            #     ai_response = "bash: API authentication failed"
            # elif "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
            #     ai_response = "bash: service temporarily unavailable"
            # else:
            #     ai_response = f"bash: {command}: command error"
                
            
        return {
            "response": ai_response,
            "status": "success"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Terminal error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
