import os
import pathlib
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from core.agent import Agent
from scheduler.scheduler import Scheduler
from config.config_manager import load_config, save_config

# Inisialisasi agent secara global
agent = None
scheduler = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent, scheduler
    agent = Agent()
    scheduler = Scheduler()
    yield
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan, title="Madura AI Agent API")

# Setup folder static untuk file web
web_dir = pathlib.Path(__file__).parent / "web"
app.mount("/static", StaticFiles(directory=web_dir), name="static")

class ChatRequest(BaseModel):
    message: str

@app.get("/", response_class=HTMLResponse)
async def index():
    with open(web_dir / "index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/chat")
def chat_endpoint(req: ChatRequest):
    try:
        # Jalankan chat secara sinkron di thread terpisah (ditangani oleh FastAPI)
        response = agent.chat(req.message)
        return {"reply": response}
    except Exception as e:
        return {"reply": f"❌ Maaf, terjadi kesalahan internal: {str(e)}"}

class ConfigRequest(BaseModel):
    ai_name: str
    user_name: str
    personality: str

@app.get("/api/config")
def get_config_endpoint():
    return load_config()

@app.post("/api/config")
def update_config_endpoint(req: ConfigRequest):
    try:
        cfg = load_config()
        cfg["ai_name"] = req.ai_name
        cfg["user_name"] = req.user_name
        cfg["personality"] = req.personality
        save_config(cfg)
        
        # Reload konfigurasi pada agent global jika diperlukan
        if agent is not None:
            agent.config = load_config()
            
        return {"status": "success", "message": "Konfigurasi berhasil disimpan!"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
