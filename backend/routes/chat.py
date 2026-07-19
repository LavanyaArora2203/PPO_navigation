# chat.py

from fastapi import APIRouter
from pydantic import BaseModel
from backend.langraph_agents.graph import graph

router = APIRouter()

class Chat(BaseModel):
    message: str


@router.post("/chat")
def chat(req: Chat):

    result = graph.invoke(
        {
            "user_input": req.message
        }
    )

    return {
        "reply": result["response"]
    }