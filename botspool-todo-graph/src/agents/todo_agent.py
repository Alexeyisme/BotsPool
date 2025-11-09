"""
BotsPool ToDo Graph Agent

Adapted from the existing ToDo-Agent implementation to work with
the BotsPool Core Gateway architecture.
"""

import uuid
from datetime import datetime
from typing import Literal, Optional, TypedDict, Dict, Any, List

from pydantic import BaseModel, Field
from trustcall import create_extractor
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import (
    merge_message_runs,
    SystemMessage,
    HumanMessage,
    ToolMessage,
)
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.store.base import BaseStore
from langgraph.store.memory import InMemoryStore
from langgraph.prebuilt import ToolNode

from botspool_shared_utils.notifications import (
    NotificationClientConfig,
    create_notification_toolset,
)

from ..config import Settings, get_settings


class Spy:
    """Inspect the tool calls for Trustcall."""

    def __init__(self):
        self.called_tools = []

    def __call__(self, run):
        q = [run]
        while q:
            r = q.pop()
            if r.child_runs:
                q.extend(r.child_runs)
            if r.run_type == "chat_model":
                self.called_tools.append(
                    r.outputs["generations"][0][0]["message"]["kwargs"]["tool_calls"]
                )


def extract_tool_info(tool_calls, schema_name="Memory"):
    """Extract information from tool calls for both patches and new memories."""
    changes = []

    for call_group in tool_calls:
        for call in call_group:
            if call["name"] == "PatchDoc":
                if call["args"]["patches"]:
                    changes.append(
                        {
                            "type": "update",
                            "doc_id": call["args"]["json_doc_id"],
                            "planned_edits": call["args"]["planned_edits"],
                            "value": call["args"]["patches"][0]["value"],
                        }
                    )
                else:
                    changes.append(
                        {
                            "type": "no_update",
                            "doc_id": call["args"]["json_doc_id"],
                            "planned_edits": call["args"]["planned_edits"],
                        }
                    )
            elif call["name"] == schema_name:
                changes.append({"type": "new", "value": call["args"]})

    result_parts = []
    for change in changes:
        if change["type"] == "update":
            result_parts.append(
                f"Document {change['doc_id']} updated:\n"
                f"Plan: {change['planned_edits']}\n"
                f"Added content: {change['value']}"
            )
        elif change["type"] == "no_update":
            result_parts.append(
                f"Document {change['doc_id']} unchanged:\n" f"{change['planned_edits']}"
            )
        else:
            result_parts.append(
                f"New {schema_name} created:\n" f"Content: {change['value']}"
            )

    return "\n\n".join(result_parts)


# Schema definitions
class Profile(BaseModel):
    """User profile schema."""

    name: Optional[str] = Field(description="The user's name", default=None)
    location: Optional[str] = Field(description="The user's location", default=None)
    job: Optional[str] = Field(description="The user's job", default=None)
    connections: List[str] = Field(
        description="Personal connection of the user, such as family members, friends, or coworkers",
        default_factory=list,
    )
    interests: List[str] = Field(
        description="Interests that the user has", default_factory=list
    )


class ToDo(BaseModel):
    """ToDo schema."""

    task: str = Field(description="The task to be completed.")
    time_to_complete: Optional[int] = Field(
        description="Estimated time to complete the task (minutes)."
    )
    deadline: Optional[datetime] = Field(
        description="When the task needs to be completed by (if applicable)",
        default=None,
    )
    solutions: List[str] = Field(
        description="List of specific, actionable solutions (e.g., specific ideas, service providers, or concrete options relevant to completing the task)",
        min_items=1,
        default_factory=list,
    )
    status: Literal["not started", "in progress", "done", "archived"] = Field(
        description="Current status of the task", default="not started"
    )


class UpdateMemory(TypedDict):
    """Decision on what memory type to update."""

    update_type: Literal["user", "todo", "instructions"]


class ToDoAgent:
    """BotsPool ToDo Graph Agent."""

    def __init__(self, settings: Settings, checkpointer=None):
        self.settings = settings
        self.model = ChatOpenAI(
            model=settings.openai_model,
            temperature=settings.openai_temperature,
            api_key=settings.openai_api_key,
        )

        # Initialize memory store for structured data (profile, todos, instructions)
        self.store = InMemoryStore()

        # Create extractors
        self.profile_extractor = create_extractor(
            self.model,
            tools=[Profile],
            tool_choice="Profile",
        )

        # Notification tools
        notification_config = NotificationClientConfig.from_env(agent="todo")
        self.notification_toolset = create_notification_toolset(notification_config)
        self.notification_tools = [
            self.notification_toolset.send_notification,
            self.notification_toolset.schedule_reminder,
            self.notification_toolset.cancel_reminder,
            self.notification_toolset.list_user_reminders,
        ]

        # Build the graph with optional checkpointer
        self.graph = self._build_graph(checkpointer)

    def _build_graph(self, checkpointer=None):
        """Build the LangGraph state graph."""
        builder = StateGraph(MessagesState)

        # Add nodes
        builder.add_node("task_mAIstro", self.task_mAIstro)
        builder.add_node("update_todos", self.update_todos)
        builder.add_node("update_profile", self.update_profile)
        builder.add_node("update_instructions", self.update_instructions)

        # Use custom wrapper for notification tools (injects context)
        builder.add_node("notification_tools", self.execute_notification_tools)

        # Define flow
        builder.add_edge(START, "task_mAIstro")
        builder.add_conditional_edges("task_mAIstro", self.route_message)
        builder.add_edge("update_todos", "task_mAIstro")
        builder.add_edge("update_profile", "task_mAIstro")
        builder.add_edge("update_instructions", "task_mAIstro")
        builder.add_edge("notification_tools", "task_mAIstro")

        # Compile with checkpointer if provided
        if checkpointer is not None:
            return builder.compile(checkpointer=checkpointer)
        else:
            # Fallback to MemorySaver if no checkpointer provided
            return builder.compile(checkpointer=MemorySaver())

    def task_mAIstro(self, state: MessagesState, config: RunnableConfig):
        """Main task management node."""
        # Get user ID from config
        user_id = config.get("configurable", {}).get("user_id", "default-user")
        todo_category = config.get("configurable", {}).get("todo_category", "general")
        task_maistro_role = config.get("configurable", {}).get(
            "task_maistro_role",
            "You are a helpful task management assistant. You help create, organize, and manage the user's ToDo list.",
        )

        # Extract chat_id from session_id
        session_id = config.get("configurable", {}).get("session_id", "")
        chat_id = None
        if session_id and "_" in session_id:
            try:
                chat_id = int(session_id.split("_")[0])
            except (ValueError, TypeError):
                pass

        # Also try from metadata
        if not chat_id:
            metadata = config.get("configurable", {}).get("metadata", {})
            if "chat_id" in metadata:
                try:
                    chat_id = int(metadata["chat_id"])
                except (ValueError, TypeError):
                    pass

        # Retrieve memories from store
        profile_namespace = ("profile", todo_category, user_id)
        profile_memories = self.store.search(profile_namespace)
        user_profile = profile_memories[0].value if profile_memories else None

        todo_namespace = ("todo", todo_category, user_id)
        todo_memories = self.store.search(todo_namespace)
        todo = "\n".join(f"{mem.value}" for mem in todo_memories)

        instructions_namespace = ("instructions", todo_category, user_id)
        instructions_memories = self.store.search(instructions_namespace)
        instructions = instructions_memories[0].value if instructions_memories else ""

        # System message
        system_msg = self._get_system_message(
            task_maistro_role, user_profile, todo, instructions, user_id, chat_id
        )

        # Respond using memory and chat history
        # Bind both memory update tool and notification tools
        tool_bindings = [UpdateMemory, *self.notification_tools]
        response = self.model.bind_tools(
            tool_bindings, parallel_tool_calls=False
        ).invoke([SystemMessage(content=system_msg)] + state["messages"])

        return {"messages": [response]}

    def update_profile(self, state: MessagesState, config: RunnableConfig):
        """Update user profile."""
        user_id = config.get("configurable", {}).get("user_id", "default-user")
        todo_category = config.get("configurable", {}).get("todo_category", "general")

        namespace = ("profile", todo_category, user_id)
        existing_items = self.store.search(namespace)

        existing_memories = (
            [
                (existing_item.key, "Profile", existing_item.value)
                for existing_item in existing_items
            ]
            if existing_items
            else None
        )

        trustcall_instruction = self._get_trustcall_instruction()
        updated_messages = list(
            merge_message_runs(
                messages=[SystemMessage(content=trustcall_instruction)]
                + state["messages"][:-1]
            )
        )

        result = self.profile_extractor.invoke(
            {"messages": updated_messages, "existing": existing_memories}
        )

        # Save memories
        for r, rmeta in zip(result["responses"], result["response_metadata"]):
            self.store.put(
                namespace,
                rmeta.get("json_doc_id", str(uuid.uuid4())),
                r.model_dump(mode="json"),
            )

        tool_calls = state["messages"][-1].tool_calls
        return {
            "messages": [
                {
                    "role": "tool",
                    "content": "updated profile",
                    "tool_call_id": tool_calls[0]["id"],
                }
            ]
        }

    def update_todos(self, state: MessagesState, config: RunnableConfig):
        """Update ToDo list."""
        user_id = config.get("configurable", {}).get("user_id", "default-user")
        todo_category = config.get("configurable", {}).get("todo_category", "general")

        namespace = ("todo", todo_category, user_id)
        existing_items = self.store.search(namespace)

        existing_memories = (
            [
                (existing_item.key, "ToDo", existing_item.value)
                for existing_item in existing_items
            ]
            if existing_items
            else None
        )

        trustcall_instruction = self._get_trustcall_instruction()
        updated_messages = list(
            merge_message_runs(
                messages=[SystemMessage(content=trustcall_instruction)]
                + state["messages"][:-1]
            )
        )

        spy = Spy()
        todo_extractor = create_extractor(
            self.model, tools=[ToDo], tool_choice="ToDo", enable_inserts=True
        ).with_listeners(on_end=spy)

        result = todo_extractor.invoke(
            {"messages": updated_messages, "existing": existing_memories}
        )

        # Save memories
        for r, rmeta in zip(result["responses"], result["response_metadata"]):
            self.store.put(
                namespace,
                rmeta.get("json_doc_id", str(uuid.uuid4())),
                r.model_dump(mode="json"),
            )

        tool_calls = state["messages"][-1].tool_calls
        todo_update_msg = extract_tool_info(spy.called_tools, "ToDo")
        return {
            "messages": [
                {
                    "role": "tool",
                    "content": todo_update_msg,
                    "tool_call_id": tool_calls[0]["id"],
                }
            ]
        }

    def update_instructions(self, state: MessagesState, config: RunnableConfig):
        """Update user instructions."""
        user_id = config.get("configurable", {}).get("user_id", "default-user")
        todo_category = config.get("configurable", {}).get("todo_category", "general")

        namespace = ("instructions", todo_category, user_id)
        existing_memory = self.store.get(namespace, "user_instructions")

        system_msg = self._get_instructions_message(
            existing_memory.value if existing_memory else None
        )
        new_memory = self.model.invoke(
            [SystemMessage(content=system_msg)]
            + state["messages"][:-1]
            + [
                HumanMessage(
                    content="Please update the instructions based on the conversation"
                )
            ]
        )

        key = "user_instructions"
        self.store.put(namespace, key, {"memory": new_memory.content})

        tool_calls = state["messages"][-1].tool_calls
        return {
            "messages": [
                {
                    "role": "tool",
                    "content": "updated instructions",
                    "tool_call_id": tool_calls[0]["id"],
                }
            ]
        }

    async def execute_notification_tools(
        self, state: MessagesState, config: RunnableConfig
    ):
        """Execute notification tools with auto-injected context.

        This node intercepts notification tool calls and injects context
        (chat_id, user_id) before calling the internal implementations.
        """
        # Extract context from config
        configurable = config.get("configurable", {})
        metadata = configurable.get("metadata", {})
        session_id = configurable.get("session_id", "")
        user_id = configurable.get("user_id")

        # Extract chat_id from session_id (format: "{chat_id}_{agent}")
        chat_id = None
        if session_id and "_" in session_id:
            try:
                chat_id = int(session_id.split("_")[0])
            except (ValueError, TypeError):
                pass

        # Also try from metadata
        if not chat_id and "chat_id" in metadata:
            try:
                chat_id = int(metadata["chat_id"])
            except (ValueError, TypeError):
                pass

        # Process each tool call
        tool_messages = []
        last_message = state["messages"][-1]

        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]  # Args from model
            tool_id = tool_call["id"]

            try:
                # Call the appropriate internal implementation with injected context
                if tool_name == "send_notification":
                    result = await self.notification_toolset.send_notification_impl(
                        message=tool_args["message"],
                        chat_id=chat_id,
                        user_id=user_id,
                        priority=tool_args.get("priority", "normal"),
                        notification_type=tool_args.get("notification_type", "info"),
                    )
                elif tool_name == "schedule_reminder":
                    reminder_type = tool_args.get("reminder_type", "reminder")
                    if reminder_type not in {"reminder", "info", "alert", "update"}:
                        reminder_type = "reminder"
                    result = await self.notification_toolset.schedule_reminder_impl(
                        message=tool_args["message"],
                        hours_from_now=tool_args["hours_from_now"],
                        chat_id=chat_id,
                        user_id=user_id,
                        reminder_type=reminder_type,
                    )
                elif tool_name == "list_user_reminders":
                    result = await self.notification_toolset.list_user_reminders_impl(
                        user_id=user_id
                    )
                elif tool_name == "cancel_reminder":
                    # cancel_reminder doesn't need context injection
                    result = await self.notification_toolset.cancel_reminder.ainvoke(
                        tool_args
                    )
                else:
                    result = f"Error: Unknown tool '{tool_name}'"
            except Exception as e:
                import traceback

                result = (
                    f"Error executing {tool_name}: {str(e)}\n{traceback.format_exc()}"
                )

            # Create tool message
            tool_messages.append(ToolMessage(content=str(result), tool_call_id=tool_id))

        return {"messages": tool_messages}

    def route_message(
        self, state: MessagesState, config: RunnableConfig
    ) -> Literal[
        END,
        "update_todos",
        "update_instructions",
        "update_profile",
        "notification_tools",
    ]:
        """Route message to appropriate update function."""
        message = state["messages"][-1]
        if len(message.tool_calls) == 0:
            return END
        else:
            tool_call = message.tool_calls[0]
            tool_name = tool_call.get("name", "")

            # If it's a notification tool, route to ToolNode
            if tool_name in [
                "send_notification",
                "schedule_reminder",
                "cancel_reminder",
                "list_user_reminders",
            ]:
                return "notification_tools"

            # Handle UpdateMemory tool
            if "update_type" in tool_call.get("args", {}):
                if tool_call["args"]["update_type"] == "user":
                    return "update_profile"
                elif tool_call["args"]["update_type"] == "todo":
                    return "update_todos"
                elif tool_call["args"]["update_type"] == "instructions":
                    return "update_instructions"
                else:
                    raise ValueError(
                        f"Unknown update type: {tool_call['args']['update_type']}"
                    )
            else:
                # Unknown tool without update_type, just end
                return END

    def _get_system_message(
        self,
        task_maistro_role: str,
        user_profile: str,
        todo: str,
        instructions: str,
        user_id: str = None,
        chat_id: int = None,
    ) -> str:
        """Get system message for the agent."""
        notification_info = """

You have access to notification tools that allow you to proactively send messages to the user:
- send_notification: Send an immediate notification
- schedule_reminder: Schedule a future reminder
- cancel_reminder: Cancel a scheduled reminder
- list_user_reminders: List all scheduled reminders

Use these tools when appropriate (e.g., to confirm task completion, remind about deadlines, etc.)."""

        return f"""{task_maistro_role}{notification_info}

You have a long term memory which keeps track of three things:
1. The user's profile (general information about them) 
2. The user's ToDo list
3. General instructions for updating the ToDo list

Here is the current User Profile (may be empty if no information has been collected yet):
<user_profile>
{user_profile}
</user_profile>

Here is the current ToDo List (may be empty if no tasks have been added yet):
<todo>
{todo}
</todo>

Here are the current user-specified preferences for updating the ToDo list (may be empty if no preferences have been specified yet):
<instructions>
{instructions}
</instructions>

Here are your instructions for reasoning about the user's messages:

1. Reason carefully about the user's messages as presented below. 

2. Decide whether any of the your long-term memory should be updated:
- If personal information was provided about the user, update the user's profile by calling UpdateMemory tool with type `user`
- If tasks are mentioned, update the ToDo list by calling UpdateMemory tool with type `todo`
- If the user has specified preferences for how to update the ToDo list, update the instructions by calling UpdateMemory tool with type `instructions`

3. Tell the user that you have updated your memory, if appropriate:
- Do not tell the user you have updated the user's profile
- Tell the user them when you update the todo list
- Do not tell the user that you have updated instructions

4. Err on the side of updating the todo list. No need to ask for explicit permission.

5. Respond naturally to user user after a tool call was made to save memories, or if no tool call was made."""

    def _get_trustcall_instruction(self) -> str:
        """Get Trustcall instruction."""
        return f"""Reflect on following interaction. 

Use the provided tools to retain any necessary memories about the user. 

Use parallel tool calling to handle updates and insertions simultaneously.

System Time: {datetime.now().isoformat()}"""

    def _get_instructions_message(self, current_instructions: str) -> str:
        """Get instructions update message."""
        return f"""Reflect on the following interaction.

Based on this interaction, update your instructions for how to update ToDo list items. Use any feedback from the user to update how they like to have items added, etc.

Your current instructions are:

<current_instructions>
{current_instructions}
</current_instructions>"""

    async def process_message(
        self, message: str, user_id: str, config: Dict[str, Any] = None
    ) -> str:
        """Process a user message and return response."""
        if config is None:
            config = {}

        # Create messages state
        state = {"messages": [HumanMessage(content=message)]}

        # Add configuration
        # thread_id is required for checkpointer persistence
        session_id = config.get("session_id", "default")
        thread_id = config.get("thread_id", f"{user_id}_{session_id}")
        runnable_config = {
            "configurable": {
                "thread_id": thread_id,  # Required for checkpointer persistence
                "user_id": user_id,
                "session_id": session_id,  # Required for notification tools
                "todo_category": config.get("todo_category", "general"),
                "task_maistro_role": config.get(
                    "task_maistro_role",
                    "You are a helpful task management assistant. You help create, organize, and manage the user's ToDo list.",
                ),
            }
        }

        # Run the graph
        result = await self.graph.ainvoke(state, config=runnable_config)

        # Extract response
        if result and "messages" in result and result["messages"]:
            last_message = result["messages"][-1]
            if hasattr(last_message, "content"):
                return last_message.content
            elif isinstance(last_message, dict) and "content" in last_message:
                return last_message["content"]

        return "I'm sorry, I couldn't process your request. Please try again."
