import os, asyncio
from uuid import uuid4
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from common.auth import verify_token
from common.config import serverless
from agent.graph import build_graph
from agent.context import decode_context,encode_context
from agent.transport import bank_connection
memory=MemorySaver()
locks={}
async def run_chat(token, session_id, message, context_token=None):
    customer_id=verify_token(token)
    if not os.getenv('OPENAI_API_KEY'): raise RuntimeError('Set OPENAI_API_KEY in .env to enable the assistant.')
    thread=f'{customer_id}:{session_id}'
    stateless=serverless()
    history=decode_context(context_token,customer_id,session_id) if stateless else []
    # Stateless invocations own their context; local invocations share a checkpoint.
    lock=asyncio.Lock() if stateless else locks.setdefault(thread,asyncio.Lock())
    async with lock, bank_connection(token) as connection:
        client=MultiServerMCPClient({'bank':connection})
        tools=await client.get_tools()
        llm=ChatOpenAI(model=os.getenv('OPENAI_MODEL','gpt-4o-mini'),temperature=0,timeout=45,max_retries=1)
        graph=build_graph(tools,llm,None if stateless else memory)
        human=HumanMessage(content=message,id=str(uuid4()))
        result=await graph.ainvoke({'messages':[*history,human]},config={'configurable':{'thread_id':thread},'recursion_limit':15})
        used=[]
        for msg in reversed(result['messages']):
            if msg.id==human.id: break
            if isinstance(msg,AIMessage): used[0:0]=[{'name':c['name'],'args':c['args']} for c in msg.tool_calls]
        content=result['messages'][-1].content
        if not isinstance(content,str): content='\n'.join(b.get('text','') for b in content if isinstance(b,dict))
        response={'answer':content,'tools_used':used}
        if stateless: response['context_token']=encode_context(result['messages'],customer_id,session_id)
        return response
