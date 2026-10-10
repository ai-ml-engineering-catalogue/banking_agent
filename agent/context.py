"""Encrypted client-carried conversation context for stateless deployments."""
import base64
import hashlib
import json
from cryptography.fernet import Fernet, InvalidToken
from common.config import secret
from langchain_core.messages import HumanMessage, AIMessage

class ContextError(ValueError):
    pass

def cipher():
    key=hashlib.sha256(('ibank-conversation-v1:'+secret()).encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))

def decode_context(token, customer_id, session_id):
    if not token: return []
    try:
        data=json.loads(cipher().decrypt(token.encode(),ttl=3600))
        if data['customer_id']!=customer_id or data['session_id']!=session_id:
            raise ContextError('Conversation belongs to another customer or session')
        return [(HumanMessage if m['role']=='user' else AIMessage)(content=m['content']) for m in data['messages']]
    except (InvalidToken,KeyError,TypeError,json.JSONDecodeError) as exc:
        raise ContextError('Conversation expired or invalid. Start a new chat.') from exc

def encode_context(messages, customer_id, session_id):
    # Keep only complete user/answer turns, never JWTs or tool-call envelopes.
    history=[{'role':'user' if m.type=='human' else 'assistant','content':m.content[:8000]} for m in messages if m.type=='human' or (m.type=='ai' and not m.tool_calls and isinstance(m.content,str))][-12:]
    if history and history[0]['role']!='user': history=history[1:]
    while len(json.dumps(history).encode())>40000 and len(history)>2: history=history[2:]
    data={'customer_id':customer_id,'session_id':session_id,'messages':history}
    return cipher().encrypt(json.dumps(data).encode()).decode()
