from __future__ import annotations

from typing import List, Dict


from fastapi import APIRouter, HTTPException, Request, Depends
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlmodel import Session, select
from data.models import Conversation, Message
from tomato.client import FinancialDataChat
from typing import List, Optional
import asyncio
from db import get_session



router = APIRouter()



@router.get("/health")
def health(request: Request):
    try:
        eng: Engine = request.app.state.engine
        with eng.connect() as c:
            c.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


# --- Conversation Endpoints ---
@router.post("/conversations", response_model=Conversation)
def create_conversation(topic: Optional[str] = None, session: Session = Depends(get_session)):
    conv = Conversation(topic=topic)
    session.add(conv)
    session.commit()
    session.refresh(conv)
    return conv

@router.get("/conversations", response_model=List[Conversation])
def list_conversations(session: Session = Depends(get_session)):
    return session.exec(select(Conversation)).all()

@router.get("/conversations/{conv_id}", response_model=Conversation)
def get_conversation(conv_id: int, session: Session = Depends(get_session)):
    conv = session.get(Conversation, conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


# --- Message Endpoints ---
@router.get("/conversations/{conv_id}/messages", response_model=List[Message])
def list_messages(conv_id: int, session: Session = Depends(get_session)):
    conv = session.get(Conversation, conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv.messages

@router.post("/conversations/{conv_id}/messages", response_model=Message)
def create_message(conv_id: int, content: str, sender_type: str = "user", sender: Optional[str] = None, session: Session = Depends(get_session)):
    conv = session.get(Conversation, conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    msg = Message(conversation_id=conv_id, sender_type=sender_type, sender=sender, content=content)
    session.add(msg)
    session.commit()
    session.refresh(msg)
    return msg


# --- Ask Endpoint ---
@router.post("/ask")
async def ask(conv_id: int, prompt: str, sender: Optional[str] = None, session: Session = Depends(get_session)):
    conv = session.get(Conversation, conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # 1. Create user message
    user_msg = Message(
        conversation_id=conv_id,
        sender_type="user",
        sender=sender,
        content=prompt
    )
    session.add(user_msg)
    session.commit()
    session.refresh(user_msg)

    # 2. Call LLM via FinancialDataChat
    chat = FinancialDataChat()
    # Use previous messages for context
    history = session.exec(select(Message).where(Message.conversation_id == conv_id)).all()
    # Convert to list of dicts for LLM (if needed)
    # If FinancialDataChat expects ModelMessage, adapt accordingly
    chat.message_history = []  # You may need to convert Message to ModelMessage
    # For now, just send the prompt
    result = await chat.run_interaction(prompt)

    # 3. Extract usage information from the result
    usage_info = None
    new_messages = result.new_messages()
    
    # Find the ModelResponse in the new messages to get usage info
    for message in new_messages:
        if hasattr(message, 'usage') and message.usage:
            usage_info = {
                "requests": getattr(message.usage, 'requests', None),
                "request_tokens": getattr(message.usage, 'request_tokens', None),
                "response_tokens": getattr(message.usage, 'response_tokens', None),
                "total_tokens": getattr(message.usage, 'total_tokens', None),
                "model_name": getattr(message, 'model_name', None),
                "details": getattr(message.usage, 'details', None),
            }
            break  # We found the usage info, no need to continue

    # 4. Log system message and usage
    system_msg = Message(
        conversation_id=conv_id,
        sender_type="system",
        sender="llm",
        content=result.output,
        usage=usage_info
    )
    session.add(system_msg)
    session.commit()
    session.refresh(system_msg)

    return {"user_message": user_msg, "system_message": system_msg}


## Removed old stub ask endpoint (replaced by async /ask above)
