from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

import sys
from pathlib import Path

load_dotenv()

# Setup Pathing internal to backend
BASE_DIR = Path(__file__).parent.resolve()
sys.path.append(str(BASE_DIR)) # Ensure backend is on path

from routers.librarian import router as librarian_router
from routers.curriculum import router as curriculum_router
from routers.data_manager import router as data_manager_router
from routers.training import router as training_router
from routers.admin import router as admin_router
from routers.conversation import router as conversation_router
from routers.qa import router as qa_router

app = FastAPI(title="Civic Lens API")
app.include_router(librarian_router, prefix="/api/v1")
app.include_router(curriculum_router, prefix="/api/v1")
app.include_router(data_manager_router, prefix="/api/v1")
app.include_router(training_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(conversation_router, prefix="/api/v1")
app.include_router(qa_router, prefix="/api/v1")

# Setup CORS for future frontend interaction
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Hugging Face Configuration
HF_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN")
client = InferenceClient(api_key=HF_TOKEN)

class LLMRequest(BaseModel):
    prompt: str
    model: str = "Qwen/Qwen2.5-7B-Instruct"
    max_tokens: int = 500

@app.get("/")
async def root():
    return {"message": "Welcome to the Civic Lens API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "0.1.0"}

@app.get("/api/v1/ping")
async def ping():
    return {"ping": "pong"}

@app.post("/api/v1/llm/generate")
async def generate_text(request: LLMRequest):
    try:
        if not HF_TOKEN:
            return {"warning": "HUGGINGFACE_API_TOKEN not set, this might fail unless it is a public model/endpoint.", "results": "Mock response: Please set HF_TOKEN"}
        
        response = ""
        for message in client.chat_completion(
            model=request.model,
            messages=[{"role": "user", "content": request.prompt}],
            max_tokens=request.max_tokens,
            stream=True,
        ):
            response += message.choices[0].delta.content
        
        return {"model": request.model, "generated_text": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
