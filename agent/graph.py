from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import SystemMessage, AIMessage
from agent.prompts import system_prompt

def build_graph(tools, llm, checkpointer=None):
    model=llm.bind_tools(tools)
    async def respond(state):
        messages=state['messages']
        rounds=0
        for msg in reversed(messages):
            if msg.type=='human': break
            if isinstance(msg,AIMessage) and msg.tool_calls: rounds+=1
        if rounds>=6:
            return {'messages':[AIMessage(content='I reached the lookup limit. Please narrow your date range or ask a more specific question.')]}
        return {'messages':[await model.ainvoke([SystemMessage(content=system_prompt()),*messages])]}
    def route(state): return 'tools' if state['messages'][-1].tool_calls else END
    graph=StateGraph(MessagesState)
    graph.add_node('agent',respond); graph.add_node('tools',ToolNode(tools))
    graph.add_edge(START,'agent'); graph.add_conditional_edges('agent',route); graph.add_edge('tools','agent')
    return graph.compile(checkpointer=checkpointer)
