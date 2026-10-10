from langchain_core.messages import AIMessage,HumanMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from agent.graph import build_graph
from agent.prompts import system_prompt

@tool
def get_banking_transactions(limit:int=5)->dict:
    """Read own transactions."""
    return {'transactions':[{'merchant':'Swiggy','amount':642}]}
class FakeModel:
    def __init__(self): self.histories=[]
    def bind_tools(self,tools): return self
    async def ainvoke(self,messages):
        self.histories.append(messages)
        if messages[-1].type=='human':
            return AIMessage(content='',tool_calls=[{'name':'get_banking_transactions','args':{'limit':5},'id':'call1','type':'tool_call'}])
        return AIMessage(content='Your Swiggy transaction is ₹642.00.')
async def test_graph_tool_and_memory():
    model=FakeModel();graph=build_graph([get_banking_transactions],model,MemorySaver())
    config={'configurable':{'thread_id':'1:test'},'recursion_limit':15}
    result=await graph.ainvoke({'messages':[HumanMessage(content='Show payments')]},config)
    assert result['messages'][-1].content=='Your Swiggy transaction is ₹642.00.'
    assert any(m.type=='tool' for m in result['messages'])
    result=await graph.ainvoke({'messages':[HumanMessage(content='And last month?')]},config)
    assert len([m for m in result['messages'] if m.type=='human'])==2
    other=await graph.ainvoke({'messages':[HumanMessage(content='Hi')]},{'configurable':{'thread_id':'2:test'}})
    assert len([m for m in other['messages'] if m.type=='human'])==1
    assert 'Politely decline transfers' in system_prompt()

async def test_service_uses_bearer_and_reports_current_tools(monkeypatch):
    import agent.service as service
    from common.auth import create_token
    observed={}
    model=FakeModel()
    class FakeClient:
        def __init__(self,config): observed.update(config)
        async def get_tools(self): return [get_banking_transactions]
    monkeypatch.setenv('OPENAI_API_KEY','fake-test-key')
    monkeypatch.setattr(service,'MultiServerMCPClient',FakeClient)
    monkeypatch.setattr(service,'ChatOpenAI',lambda **kwargs:model)
    monkeypatch.setattr(service,'memory',MemorySaver())
    token=create_token(1)
    first=await service.run_chat(token,'service-test','Show payments')
    assert first['tools_used']==[{'name':'get_banking_transactions','args':{'limit':5}}]
    second=await service.run_chat(token,'service-test','And last month?')
    assert len(second['tools_used'])==1
    assert observed['bank']['headers']['Authorization']=='Bearer '+token
    assert len([m for m in model.histories[-1] if m.type=='human'])==2
