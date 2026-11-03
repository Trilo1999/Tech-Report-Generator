from typing import Optional, Sequence

try:
    from langchain.agents import AgentExecutor, create_tool_calling_agent
except ImportError:
    try:
        from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
    except ImportError:
        AgentExecutor = None
        create_tool_calling_agent = None
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.tools import BaseTool

from app.llms.llm_factory import get_default_chat_client
from app.utils.core_utils.history_factory_utils import message_history_factory


class BaseAgent:
    """Base class for tool-calling agents with memory."""

    def __init__(
        self,
        llm=None,
        tools: Optional[Sequence[BaseTool]] = None,
        system_prompt: str = "",
    ):
        """Initialize the base agent.

        Args:
            llm: LLM client to use.
            tools: Tools available to the agent.
            system_prompt: System prompt string.
        """
        self._llm = llm
        self.tools = tools or []
        self.system_prompt = system_prompt
        self._prompt = None
        self._agent = None
        self._agent_executor = None
        self._agent_with_memory = None

    @property
    def llm(self):
        if self._llm is None:
            self._llm = get_default_chat_client()
        return self._llm

    @llm.setter
    def llm(self, value):
        self._llm = value
        self._agent = None
        self._agent_executor = None
        self._agent_with_memory = None

    @property
    def prompt(self):
        if self._prompt is None:
            self._prompt = self.get_prompt()
        return self._prompt

    @property
    def agent(self):
        if self._agent is None:
            self._agent = self.get_agent()
        return self._agent

    @property
    def agent_executor(self):
        if self._agent_executor is None:
            self._agent_executor = self.get_agent_executor()
        return self._agent_executor

    @property
    def agent_with_memory(self):
        if self._agent_with_memory is None:
            self._agent_with_memory = self.get_agent_with_memory()
        return self._agent_with_memory

    def get_prompt(self):
        """Build the agent prompt template.

        Returns:
            ChatPromptTemplate with system prompt, chat_history, input prompt placeholder, and agent_scratchpad placeholder.
        """
        return ChatPromptTemplate.from_messages(
            [
                ("system", self.system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("user", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

    def get_agent(self):
        """Create the tool-calling agent.

        Returns:
            LangChain agent configured with llm, tools, and prompt.
        """
        return create_tool_calling_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self.prompt,
        )

    def get_agent_executor(self):
        """Create the agent executor.

        Returns:
            AgentExecutor with intermediate steps enabled.
        """
        return AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            return_intermediate_steps=True,
        )

    def get_agent_with_memory(self):
        """Create the agent runnable with Redis-backed memory.

        Returns:
            RunnableWithMessageHistory wrapping the agent executor.
        """
        return RunnableWithMessageHistory(
            self.agent_executor,
            message_history_factory,
            input_messages_key="input",
            history_messages_key="chat_history",
            output_messages_key="output",
        )
