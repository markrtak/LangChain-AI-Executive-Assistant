import os
from dotenv import load_dotenv
from dataclasses import dataclass
from langchain.agents import AgentState, create_agent
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver
from langchain.tools import tool, ToolRuntime
from langgraph.types import Command
from langchain.messages import ToolMessage
from langchain.agents.middleware import wrap_model_call, dynamic_prompt, HumanInTheLoopMiddleware
from langchain.agents.middleware import ModelRequest, ModelResponse
from typing import Callable

load_dotenv()


@dataclass
class EmailContext:
    email_address: str = "takla@example.com"
    password: str = "password123"


class AuthenticatedState(AgentState):
    authenticated: bool


@tool
def check_inbox() -> str:
    """Check the inbox for recent emails"""
    return """
    Hi Mark, 
    I'm going to be near your gym tomorrow and was wondering if we could workout together?
    - best, Omar (omar@example.com)
    """


@tool
def send_email(to: str, subject: str, body: str) -> str:
    """Send an response email"""
    return f"Email sent to {to} with subject {subject} and body {body}"


@tool
def authenticate(email: str, password: str, runtime: ToolRuntime) -> Command:
    """Authenticate the user with the given email and password"""
    if email == runtime.context.email_address and password == runtime.context.password:
        return Command(
            update={
                "authenticated": True,
                "messages": [
                    ToolMessage("Successfully authenticated", tool_call_id=runtime.tool_call_id)
                ],
            }
        )
    else:
        return Command(
            update={
                "authenticated": False,
                "messages": [
                    ToolMessage("Authentication failed", tool_call_id=runtime.tool_call_id)
                ],
            }
        )


@wrap_model_call
async def dynamic_tool_call(
    request: ModelRequest, handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    """Allow read inbox and send email tools only if user provides correct email and password"""

    authenticated = request.state.get("authenticated")

    if authenticated:
        tools = [check_inbox, send_email]
    else:
        tools = [authenticate]

    request = request.override(tools=tools)
    return await handler(request)


authenticated_prompt = """You are a helpful assistant that can check the inbox and send emails.
Your first step after authentication is to check the inbox."""
unauthenticated_prompt = (
    "You are a helpful assistant that can authenticate users. "
    "Ask the user for their email and password, then call the authenticate tool."
)


@dynamic_prompt
def dynamic_prompt_func(request: ModelRequest) -> str:
    """Generate system prompt based on authentication status"""
    authenticated = request.state.get("authenticated")

    if authenticated:
        return authenticated_prompt
    else:
        return unauthenticated_prompt


unauthenticated_prompt = """You are an intelligent, secure Email Assistant Agent. 
YOUR MISSION:
You help users manage their inbox and draft responses, but you operate under a strict zero-trust security policy. You cannot access any emails until the user is fully authenticated.
YOUR CAPABILITIES & WORKFLOW:
1. State Awareness: You know whether the user is logged in or not based on their session state.
2. Authentication: If a user asks who you are, what you do, or tries to read/send emails, politely inform them that you are their Personal Email Assistant, but you must first verify their identity. 
3. Tool Execution: Ask the user for their email address and password, then execute the `authenticate` tool. Do not guess credentials.
CURRENT STATUS: Unauthenticated. You only have access to the `authenticate` tool right now."""

authenticated_prompt = """You are an intelligent, secure Email Assistant Agent.
YOUR MISSION:
You act as a human-centric co-pilot for managing email workflows, reading incoming messages, and drafting responses.
YOUR CAPABILITIES & WORKFLOW:
1. Identity & Purpose: When asked what you do or who you are, proudly state that you are an automated Email Assistant designed to securely check inboxes and handle correspondence.
2. Inbox Processing: Your first priority upon a fresh authentication is to check the user's inbox using the `check_inbox` tool to summarize recent messages.
3. Email Despatch: You can draft and reply to messages using the `send_email` tool.
4. Human-in-the-Loop Safeguard: You are fully aware that you have a safety middleware constraint. While you can check the inbox autonomously, you CANNOT finalize or send an email without explicit human review and approval. 
CURRENT STATUS: Successfully Authenticated. You now have full access to your `check_inbox` and `send_email` tools."""

llm = init_chat_model(
    model="llama-3.3-70b-versatile",
    model_provider="groq",
    api_key=os.getenv("GROQ_API_KEY"),
).bind(parallel_tool_calls=False)

agent = create_agent(
    model=llm,
    tools=[authenticate, check_inbox, send_email],
    state_schema=AuthenticatedState,
    context_schema=EmailContext,
    middleware=[
        dynamic_tool_call,
        dynamic_prompt_func,
        HumanInTheLoopMiddleware(
            interrupt_on={
                "authenticate": False,
                "check_inbox": False,
                "send_email": True,
            }
        ),
    ],
)

# Export the graph variable so langgraph.json can read it.
# If the agent has an underlying compiled graph structure, expose it safely:
if hasattr(agent, "graph"):
    graph = agent.graph
else:
    # If create_agent compiles directly to a runnable graph structure, export it as-is
    graph = agent
