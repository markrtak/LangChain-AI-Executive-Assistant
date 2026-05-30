# LangChain Email Assistant + Agent Chat UI

This project combines a LangChain-based email assistant agent with a React/Next.js chat UI for LangGraph. The agent uses dynamic middleware, prompt switching, tool gating, and human-in-the-loop controls to safely manage email workflows and support long-running conversations.

## What this project includes

- `email_agent.py`
  - Defines an authenticated email assistant agent.
  - Uses dynamic tool selection based on authentication state.
  - Implements middleware for prompt switching and tool gating.
  - Exports a Graph-compatible `agent` object.

- `agent-chat-ui/`
  - Next.js frontend chat app for talking to a LangGraph assistant.
  - Connects to a LangGraph server using `apiUrl`, `assistantId`, and optional API key.
  - Supports thread history, long conversations, and artifact rendering.

## Demo Video

Watch a short demo of the Agent Chat UI and Email Assistant in action:

- Demo Video: https://drive.google.com/file/d/1_eeQoEk9V2hnQe8o-uzkdmwWnXGk1zCk/view?usp=drive_link

## Architecture overview

### Agent logic

The core Python agent is defined in `3.5_email_agent.py`:

- `EmailContext` stores runtime context values such as email and password.
- `AuthenticatedState` is an `AgentState` schema with an `authenticated` boolean.
- `authenticate`, `check_inbox`, and `send_email` are LangChain tools.
- `dynamic_tool_call` middleware switches available tools at runtime:
  - When unauthenticated, only `authenticate` is available.
  - After successful authentication, `check_inbox` and `send_email` become available.
- `dynamic_prompt_func` middleware selects the system prompt based on current state.
- `HumanInTheLoopMiddleware` interrupts the `send_email` tool so that email dispatch must be explicitly approved by a human before the assistant can continue.

### Dynamic agents and middleware

This project uses two middleware capabilities:

- `@dynamic_prompt` to dynamically generate the assistant prompt based on `authenticated` state.
- `@wrap_model_call` to dynamically override the tool list before each model invocation.

These features together create a dynamic agent that can:

- adapt its instructions based on authentication status
- enforce a strict zero-trust workflow
- switch available capabilities during a conversation

### Human-in-the-loop flow

The email assistant is designed for safe operational behavior:

- Authentication is required before any inbox or send actions.
- `check_inbox` is allowed once authenticated.
- `send_email` is protected by `HumanInTheLoopMiddleware`.
- This means the agent can draft or propose an email, but a human review step is required before a final send occurs.

### Long conversations and session state

The UI and agent support long-running conversations by preserving thread history and state:

- The chat frontend enables thread selection and conversation history.
- `fetchStateHistory: true` is configured in the stream provider so the UI can load past messages and maintain session continuity.
- LangGraph state storage preserves the agent's `authenticated` status and any message history across requests.

## How it works

1. User opens the chat UI and connects to a LangGraph server.
2. The assistant starts in an unauthenticated state.
3. The agent asks for email credentials via the `authenticate` tool.
4. On success, middleware switches prompt and activates email tools.
5. The agent first reads the inbox using `check_inbox`.
6. The user can request a reply; `send_email` is gated behind human approval.

## Setup

### Prerequisites

- Node.js 18+ and `pnpm`
- Python 3.11+ or compatible
- A LangGraph-compatible backend or graph runner
- `GROQ_API_KEY` for the configured Groq model provider (used by `3.5_email_agent.py`)

### Backend / agent setup

Create a Python environment and install dependencies required by the agent. At a minimum, install:

```bash
pip install python-dotenv langchain langgraph
```

Then make sure the environment can access the model provider:

```bash
export GROQ_API_KEY="your_groq_api_key"
```

On Windows PowerShell:

```powershell
$env:GROQ_API_KEY = "your_groq_api_key"
```

### Frontend setup

From `agent-chat-ui/`:

```bash
cd agent-chat-ui
pnpm install
pnpm dev
```

The UI will start on `http://localhost:3000` by default.

### Environment variables

The frontend supports optional environment variables defined from `.env`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:2024
NEXT_PUBLIC_ASSISTANT_ID=agent
```

Copy `agent-chat-ui/.env.example` to `.env` if you want to hardcode values.

## Testing the project

### 1. Start the chat UI

Run the frontend and point it at your LangGraph deployment.

- `Deployment URL`: URL of the LangGraph server
- `Assistant/Graph ID`: graph or assistant ID, typically `agent`
- `LangSmith API Key`: optional for deployed LangGraph hosts

### 2. Verify the unauthenticated flow

- Ask the assistant to read emails or send a message.
- The agent should respond that it must authenticate first.
- Provide the email and password and verify the `authenticate` tool runs.

### 3. Verify authenticated behavior

- After authentication, the agent should immediately check the inbox with `check_inbox`.
- Confirm the inbox summary appears and the assistant can reference recent email content.

### 4. Verify human-in-the-loop gating

- Ask the assistant to send an email.
- The `send_email` tool is configured to interrupt under `HumanInTheLoopMiddleware`.
- Confirm that final send requires explicit approval or review before it executes.

### 5. Verify long conversations

- Send multiple messages and continue the same thread.
- Reload the UI or revisit the thread.
- Confirm the previous messages and state are reloaded correctly.

## Notes on implementation

### Agent tools

- `authenticate(email, password, runtime)` returns a `Command` that updates the agent state and sends a tool message.
- `check_inbox()` simulates reading recent email content.
- `send_email(to, subject, body)` returns a confirmation string.

### Dynamic prompt design

There are two prompt modes:

- `unauthenticated_prompt`: instructs the assistant to authenticate before performing email actions.
- `authenticated_prompt`: instructs the assistant to manage inbox and email tasks securely.

The dynamic prompt is selected at runtime based on whether `authenticated` is `True`.

### Middleware stack

The agent middleware pipeline includes:

- `dynamic_tool_call`: to decide which tools are available per request.
- `dynamic_prompt_func`: to choose the correct system prompt based on state.
- `HumanInTheLoopMiddleware`: to require human confirmation for sensitive actions.
