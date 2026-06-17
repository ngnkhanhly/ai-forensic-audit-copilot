from typing import TypedDict, Annotated, Sequence, Dict, Any, List
import json
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from backend.app.config import settings
from backend.app.agents import tools as agent_tools

# Define State
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

# Define LangChain wrapper tools so that ChatOpenAI can bind them
@tool
def list_documents_tool() -> str:
    """List all documents currently registered in the database, including their IDs, filenames, status, and document types. Use this to find the ID of a document when the user specifies a filename or asks general questions."""
    return agent_tools.list_documents()

@tool
def search_documents_tool(query: str) -> str:
    """Search across all document chunks semantically. Use this to find specific clauses, terms, or amounts."""
    return agent_tools.search_documents(query)

@tool
def extract_fields_tool(document_id: int) -> str:
    """Retrieve structured data (vendor, total, date, effective_date, parties) for a specific document ID."""
    return agent_tools.extract_fields(document_id)

@tool
def validate_document_tool(document_id: int) -> str:
    """Get the validation log results, showing rules passed/failed for a document ID."""
    return agent_tools.validate_document(document_id)

@tool
def find_expiring_contracts_tool(days: int = 30) -> str:
    """Find contracts expiring in the next N days."""
    return agent_tools.find_expiring_contracts(days)

@tool
def generate_report_tool(results_json_str: str) -> str:
    """Generate a clean markdown report summary from lists or search results. Use this when the user asks to summarize or generate a report."""
    return agent_tools.generate_report(results_json_str)

# Map tools
tools_list = [
    list_documents_tool,
    search_documents_tool,
    extract_fields_tool,
    validate_document_tool,
    find_expiring_contracts_tool,
    generate_report_tool
]
tools_dict = {t.name: t for t in tools_list}

# Initialize model
def get_model():
    return ChatOpenAI(
        model=settings.DEFAULT_LLM_MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=0.0
    ).bind_tools(tools_list)

# Define nodes
def agent_node(state: AgentState) -> Dict[str, Any]:
    messages = state["messages"]
    
    # Define a clear system prompt for the agent to resolve document IDs and filenames automatically
    system_instruction = (
        "You are the Enterprise Document Intelligence Agent.\n"
        "You help users analyze business documents (invoices, contracts, receipts) in the repository.\n"
        "Guidelines:\n"
        "1. NEVER ask the user for a document ID if they mention a filename or if you can find it yourself. "
        "First call the `list_documents_tool` to find the correct document ID and filename, or search the vector DB.\n"
        "2. If the user asks a general question about a document (e.g. \"Who signed the contract sample_contract.pdf?\"), "
        "first call `list_documents_tool`, find the matching document ID, and then call `extract_fields_tool` with that ID.\n"
        "3. If the requested information (like specific line items, list of services, or detailed text clauses) is not found in the structured fields returned by `extract_fields_tool`, you MUST call `search_documents_tool` to find it in the raw text chunks of the document.\n"
        "4. When asked to summarize or generate a report, use the `generate_report_tool` to format the final output as a clean markdown report.\n"
        "5. Answer in the same language as the user's prompt (e.g., Vietnamese if the user asks in Vietnamese).\n"
        "6. If there is an active document context in the conversation history (e.g., \"[Context] The active document is ID: X, Filename: Y, Type: Z\"), you MUST use this ID directly for any document-specific queries (like calling extract_fields_tool or validate_document_tool) without listing all documents or searching first. This prevents search confusion and loops."
    )
    
    full_messages = [SystemMessage(content=system_instruction)] + list(messages)
    model = get_model()
    response = model.invoke(full_messages)
    return {"messages": [response]}

def tool_node(state: AgentState) -> Dict[str, Any]:
    messages = state["messages"]
    last_message = messages[-1]
    
    tool_messages = []
    for tool_call in last_message.tool_calls:
        tool_fn = tools_dict[tool_call["name"]]
        # Call tool with arguments
        result = tool_fn.invoke(tool_call["args"])
        tool_messages.append(
            ToolMessage(
                content=str(result),
                tool_call_id=tool_call["id"],
                name=tool_call["name"]
            )
        )
    return {"messages": tool_messages}

# Routing logic
def should_continue(state: AgentState) -> str:
    messages = state["messages"]
    last_message = messages[-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END

# Build Graph
workflow = StateGraph(AgentState)
workflow.add_node("agent", agent_node)
workflow.add_node("tools", tool_node)

workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue, ["tools", END])
workflow.add_edge("tools", "agent")

app_graph = workflow.compile()

def run_document_agent(chat_history: List[Dict[str, str]]) -> str:
    """
    Executes the agent flow using the provided chat history.
    """
    messages = []
    for msg in chat_history:
        role = msg["role"]
        content = msg["content"]
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role in ["assistant", "model"]:
            messages.append(AIMessage(content=content))
            
    try:
        final_state = app_graph.invoke({"messages": messages})
        return final_state["messages"][-1].content
    except Exception as e:
        return f"Agent error occurred: {str(e)}"
