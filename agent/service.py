import os, asyncio
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from common.auth import verify_token
from agent.graph import build_graph
memory=MemorySaver()
locks={}
async def run_chat(token, session_id, message):
    customer_id=verify_token(token)
    if not os.getenv('OPENAI_API_KEY'): raise RuntimeError('Set OPENAI_API_KEY in .env to enable the assistant.')
    thread=f'{customer_id}:{session_id}'
    async with locks.setdefault(thread,asyncio.Lock()):
        client=MultiServerMCPClient({'bank':{'url':os.getenv('MCP_URL','http://127.0.0.1:8001/mcp'),'transport':'streamable_http','headers':{'Authorization':f'Bearer {token}'}}})
        tools=await client.get_tools()
        llm=ChatOpenAI(model=os.getenv('OPENAI_MODEL','gpt-4o-mini'),temperature=0,timeout=45,max_retries=1)
        graph=build_graph(tools,llm,memory)
        human=HumanMessage(content=message)
        result=await graph.ainvoke({'messages':[human]},config={'configurable':{'thread_id':thread},'recursion_limit':15})
        used=[]
        for msg in reversed(result['messages']):
            if msg.id==human.id or msg is human: break
            if isinstance(msg,AIMessage): used[0:0]=[{'name':c['name'],'args':c['args']} for c in msg.tool_calls]
        content=result['messages'][-1].content
        if not isinstance(content,str): content='\n'.join(b.get('text','') for b in content if isinstance(b,dict))
        return {'answer':content,'tools_used':used}
