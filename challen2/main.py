from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import openai
import os
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

session_histories: Dict[str, List[Dict[str, str]]] = {}

class ChatMessage(BaseModel):
    message: str
    session_id: str

def get_prompt_for_command() -> str:
    # 讀取基礎 prompt
    with open("prompts/basic_prompt.txt", encoding="utf-8") as f:
        base_prompt = f.read()
    
    return base_prompt 

def get_session_history(session_id: str) -> List[Dict[str, str]]:
    """獲取指定 session 的對話歷史，如果不存在則創建新的"""
    if session_id not in session_histories:
        session_histories[session_id] = []
    
    return session_histories[session_id]



@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/chat")
async def chat_with_terminal(chat_message: ChatMessage):
    try:
        command = chat_message.message.strip()
        session_id = chat_message.session_id.strip()
        
        if not session_id:
            raise HTTPException(status_code=400, detail="Session ID 不能為空")
        
        # 獲取該 session 的對話歷史
        chat_history = get_session_history(session_id)
        
        # 生成針對當前命令的 prompt
        system_prompt = get_prompt_for_command()
        
        # 建構對話歷史
        messages = [{"role": "system", "content": system_prompt}]
        
        # 添加歷史對話
        messages.extend(chat_history)
        
        # 添加當前指令
        messages.append({"role": "user", "content": command})
        
        try:
            response = openai.ChatCompletion.create(
                model="basic/gpt-4o-mini",
                messages=messages,
                max_tokens=1024,
                temperature=0.3
            )
            
            if not response.choices or not response.choices[0].message.content:
                raise Exception("API 返回空回應")
                
            ai_response = response.choices[0].message.content.strip()
            
            # 儲存對話到該 session 的歷史
            chat_history.append({"role": "user", "content": command})
            chat_history.append({"role": "assistant", "content": ai_response})
            
            # 限制歷史長度避免 token 過多
            if len(chat_history) > 40:  # 保持最近 40 條訊息 (20 組對話)
                chat_history[:] = chat_history[-40:]
            
        except Exception as api_error:
            error_msg = str(api_error)
            ai_response = error_msg
                
        return {
            "response": ai_response,
            "status": "success",
            "session_id": session_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Terminal error: {str(e)}")

@app.get("/debug/state")
async def debug_state():
    """調試用：查看當前狀態"""
    return {
        "total_sessions": len(session_histories)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
