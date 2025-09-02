import logging
import os
from collections.abc import Callable
from typing import Any

import numpy as np
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from livekit.agents import ChatContext, ChatMessage
from memoripy import ChatModel, EmbeddingModel, JSONStorage, MemoryManager
from openai import OpenAI
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ConceptExtractionResponse(BaseModel):
    """Model for structured response from concept extraction."""

    concepts: list[str] = Field(
        description="list of key concepts extracted from the text."
    )


class ChatCompletionsModel(ChatModel):
    """Implementation of ChatModel for concept extraction using LLM."""

    def __init__(self, llm_config: dict[str, Any]):
        """
        Initialize the ChatCompletionsModel with configuration.

        Args:
            llm_config: dictionary containing LLM configuration (base_url, api_key, model)
        """
        api_endpoint = llm_config["base_url"]
        api_key = llm_config["api_key"]
        model_name = llm_config["model"]

        logger.info(
            f"Initializing ChatCompletionsModel with endpoint: {api_endpoint}, model: {model_name}"
        )
        try:
            self.llm = ChatOpenAI(
                openai_api_base=api_endpoint,
                openai_api_key=api_key,
                model_name=model_name,
                request_timeout=30.0,
                max_retries=2,
            )
            self.parser = JsonOutputParser(pydantic_object=ConceptExtractionResponse)
            self.prompt_template = PromptTemplate(
                template=(
                    "Extract key concepts from the following text in a concise, context-specific manner. "
                    "Include only the most highly relevant and specific core concepts that best capture the text's meaning. "
                    "Return nothing but the JSON string.\n"
                    "{format_instructions}\n{text}"
                ),
                input_variables=["text"],
                partial_variables={
                    "format_instructions": self.parser.get_format_instructions()
                },
            )
            logger.info("ChatCompletionsModel initialized successfully.")
        except Exception as e:
            logger.error(
                f"Failed to initialize ChatCompletionsModel components: {e}",
                exc_info=True,
            )
            raise

    def invoke(self, messages: list[dict[str, Any]]) -> str:
        """
        Invoke the LLM with a list of messages.

        Args:
            messages: list of message dictionaries to send to the LLM

        Returns:
            Response content as a string
        """
        if not messages:
            logger.warning(
                "Empty messages list provided to ChatCompletionsModel.invoke()"
            )
            return ""

        try:
            response = self.llm.invoke(messages)
            return (
                str(response.content)
                if response and hasattr(response, "content")
                else ""
            )
        except Exception as e:
            logger.error(
                f"Error during ChatCompletionsModel invocation: {e}", exc_info=True
            )
            return "Error processing request."

    def extract_concepts(self, text: str) -> list[str]:
        """
        Extract key concepts from the input text.

        Args:
            text: The text to extract concepts from

        Returns:
            list of extracted concept strings
        """
        if not text or not isinstance(text, str) or not text.strip():
            logger.warning(
                "Empty or whitespace-only text provided to extract_concepts()"
            )
            return []

        try:
            chain = self.prompt_template | self.llm | self.parser
            response = chain.invoke({"text": text})
            concepts = response.get("concepts", [])

            # Validate concepts
            valid_concepts = []
            for concept in concepts:
                if isinstance(concept, str) and concept.strip():
                    valid_concepts.append(concept.strip())

            logger.debug(f"Concepts extracted: {valid_concepts}")
            return valid_concepts
        except Exception as e:
            logger.error(f"Error during concept extraction: {e}", exc_info=True)
            return []


class OllamaEmbeddingModel(EmbeddingModel):
    """
    EmbeddingModel backed by an OpenAI-compatible embeddings endpoint (e.g., Ollama).
    Expects config keys: base_url, api_key, model
    """

    def __init__(self, embedding_config: dict[str, Any]):
        self.base_url: str = embedding_config["base_url"]
        self.api_key: str = embedding_config.get("api_key", "ollama") or "ollama"
        self.model: str = embedding_config["model"]

        # OpenAI client pointed at Ollama (or any OpenAI-compatible server)
        self.client = OpenAI(base_url=self.base_url, api_key=self.api_key)

        # Optional: cache the dimension after first probe
        self._dimension: int | None = None
        logger.info(f"OllamaEmbeddingModel initialized: {self.model} @ {self.base_url}")

    def initialize_embedding_dimension(self) -> int:
        """
        Probe the embeddings API once to learn the vector dimension.
        """
        try:
            resp = self.client.embeddings.create(
                model=self.model, input="dimension_check"
            )
            vec = resp.data[0].embedding
            self._dimension = len(vec)
            logger.info(f"Embedding dimension determined: {self._dimension}")
            return self._dimension
        except Exception as e:
            logger.error(f"Failed to determine embedding dimension: {e}", exc_info=True)
            # Fallback
            self._dimension = 768
            logger.warning("Falling back to default embedding dimension 768.")
            return self._dimension

    @property
    def dimension(self) -> int | None:
        return self._dimension

    def get_embedding(self, text: str) -> np.ndarray:
        """
        Get embedding vector for a string. Returns zeros on error/empty input.
        """
        try:
            if not text or not isinstance(text, str) or not text.strip():
                dim = self._dimension or 768
                logger.warning("Empty text for embedding; returning zero vector")
                return np.zeros(dim)

            resp = self.client.embeddings.create(model=self.model, input=text)
            vec = resp.data[0].embedding
            if vec is None:
                dim = self._dimension or 768
                logger.error("No embedding returned; using zero vector")
                return np.zeros(dim)

            # Cache dimension if not set yet
            if self._dimension is None:
                self._dimension = len(vec)

            return np.array(vec, dtype=np.float32)
        except Exception as e:
            dim = self._dimension or 768
            logger.error(f"Error getting embedding from Ollama: {e}", exc_info=True)
            return np.zeros(dim)


class AgentMemoryManager:
    """Manages agent memory using the Memoripy library."""

    def __init__(self, participant_identity: str, config: dict[str, Any]):
        """
        Initialize the AgentMemoryManager.

        Args:
            participant_identity: Identifier for the participant
            config: Application configuration
        """
        self.participant_identity = participant_identity
        self.config = config
        self.memory_config = config["memory"]
        self.memory_manager = None
        self._initialize_memory_manager()

    def _initialize_memory_manager(self) -> None:
        """Initialize the Memoripy MemoryManager with model instances."""
        if not self.memory_config["use"]:
            logger.info(
                f"Memory is disabled in config for {self.participant_identity}. Skipping initialization."
            )
            return

        memory_dir_abs = self.memory_config["dir_abs"]

        # Ensure the directory exists
        os.makedirs(memory_dir_abs, exist_ok=True)
        logger.info(f"Ensuring memory directory exists: {memory_dir_abs}")

        user_memory_file = os.path.join(
            memory_dir_abs, f"{self.participant_identity}.json"
        )

        llm_cfg = self.config["llm"]
        embedding_cfg = self.config["embedding"]

        try:
            chat_model_instance = ChatCompletionsModel(llm_config=llm_cfg)
            embedding_model_instance = OllamaEmbeddingModel(
                embedding_config=embedding_cfg
            )
            embedding_model_instance.initialize_embedding_dimension()

            self.memory_manager = MemoryManager(
                chat_model=chat_model_instance,
                embedding_model=embedding_model_instance,
                storage=JSONStorage(user_memory_file),
            )
            logger.info(
                f"Initialized MemoryManager for user {self.participant_identity} with storage {user_memory_file}"
            )
        except Exception as e:
            logger.error(
                f"Failed to initialize MemoryManager components for {self.participant_identity}: {e}",
                exc_info=True,
            )
            self.memory_manager = None

    async def load_memory(self, update_chat_ctx_func: Callable) -> None:
        """
        Load conversation history from storage and update the agent's chat context.

        Args:
            update_chat_ctx_func: Function to update chat context with loaded memory
        """
        if not self.memory_config.get("use", False):
            logger.info(
                f"Memory is disabled in config for {self.participant_identity}. Skipping load."
            )
            return

        if not self.memory_manager:
            logger.warning(
                f"MemoryManager not initialized for {self.participant_identity}. Cannot load history."
            )
            return

        initial_messages_from_memory = []

        try:
            short_term_history, _ = self.memory_manager.load_history()
            # Use config value for number of interactions
            num_interactions_to_load = self.memory_config.get("load_last_n", 5)
            memory_interactions = (
                short_term_history[-num_interactions_to_load:]
                if short_term_history
                else []
            )

            for interaction in memory_interactions:
                if interaction.get("prompt"):
                    initial_messages_from_memory.append(
                        ChatMessage(role="user", content=[interaction["prompt"]])
                    )
                if interaction.get("output"):
                    initial_messages_from_memory.append(
                        ChatMessage(role="assistant", content=[interaction["output"]])
                    )

            if initial_messages_from_memory:
                await update_chat_ctx_func(ChatContext(initial_messages_from_memory))
                logger.info(
                    f"Prepended {len(initial_messages_from_memory)} interactions to the initial context for {self.participant_identity}."
                )
            else:
                logger.info(
                    f"No interactions loaded from memory for {self.participant_identity}."
                )

        except FileNotFoundError:
            logger.info(
                f"No previous history file found for {self.participant_identity}. Starting fresh."
            )
        except Exception as e:
            logger.error(
                f"Failed to load history via Memoripy for {self.participant_identity}: {e}",
                exc_info=True,
            )

    def _extract_message_content(self, message: ChatMessage) -> str:
        """
        Extract text content from a ChatMessage.

        Args:
            message: The ChatMessage to extract content from

        Returns:
            Extracted text content as a string
        """
        if not message or not message.content:
            return ""

        # Handle different content structures
        if isinstance(message.content, list):
            if not message.content:
                return ""
            content_item = message.content[0]
            if isinstance(content_item, str):
                return content_item
            elif hasattr(content_item, "text"):
                return content_item.text
            else:
                return str(content_item)
        else:
            return str(message.content)

    async def save_memory(self, chat_ctx: ChatContext) -> None:
        """
        Save the current conversation history to storage.

        Args:
            chat_ctx: ChatContext containing the conversation messages
        """
        if not self.memory_config.get("use", False):
            logger.info(
                f"Memory is disabled in config for {self.participant_identity}. Skipping save."
            )
            return

        if self.memory_manager is None:
            logger.warning(
                f"Memory manager not available for {self.participant_identity}. Skipping history save."
            )
            return

        if not chat_ctx or not chat_ctx.items:
            logger.info(
                f"No conversation items to save for {self.participant_identity}."
            )
            return

        logger.info(
            f"Saving conversation history via Memoripy for user: {self.participant_identity}"
        )
        logger.info(f"Conversation history messages count: {len(chat_ctx.items)}")

        i = 0
        processed_count = 0
        items = chat_ctx.items

        while i < len(items):
            user_msg = None
            assistant_msg = None

            # Find the next user message
            if items[i].role == "user":
                user_msg = items[i]
                # Find the corresponding assistant message (if it exists)
                if i + 1 < len(items) and items[i + 1].role == "assistant":
                    assistant_msg = items[i + 1]
                    i += 2  # Move past both
                else:
                    i += 1  # Move past only user msg
            elif items[i].role == "assistant":
                # Skip assistant message without preceding user message
                logger.warning(
                    f"Skipping assistant message without preceding user message at index {i}"
                )
                i += 1
                continue
            else:  # Skip system messages etc.
                i += 1
                continue

            # Process the interaction pair
            if user_msg:
                # Extract content using helper method
                user_prompt = self._extract_message_content(user_msg)
                assistant_response = (
                    self._extract_message_content(assistant_msg)
                    if assistant_msg
                    else ""
                )

                combined_text = f"{user_prompt} {assistant_response}".strip()

                if not combined_text:
                    logger.debug("Skipping empty interaction.")
                    continue

                try:
                    concepts = self.memory_manager.extract_concepts(combined_text)
                    embedding = self.memory_manager.get_embedding(combined_text)
                    self.memory_manager.add_interaction(
                        prompt=user_prompt,
                        output=assistant_response,
                        embedding=embedding,
                        concepts=concepts,
                    )
                    processed_count += 1
                    logger.debug(
                        f"Added interaction to Memoripy: User: '{user_prompt[:50]}...' Assistant: '{assistant_response[:50]}...'"
                    )
                except Exception as e:
                    logger.error(
                        f"Error processing interaction via Memoripy: {e} for interaction: User='{user_prompt[:50]}...', Assistant='{assistant_response[:50]}...'",
                        exc_info=True,
                    )

        if processed_count > 0:
            logger.info(
                f"Successfully added {processed_count} interactions into conversational memory for {self.participant_identity}"
            )
        else:
            logger.warning(
                f"No interactions were added to memory for {self.participant_identity}"
            )

    async def add_background_knowledge(
        self, file_id: str, filename: str, content: str
    ) -> None:
        """
        Add background knowledge from uploaded files to the agent's memory.

        Args:
            file_id: Unique identifier for the file
            filename: Original filename
            content: Text content of the file
        """
        if not self.memory_config.get("use", False):
            logger.info(
                f"Memory is disabled in config for {self.participant_identity}. Skipping background knowledge."
            )
            return

        if self.memory_manager is None:
            logger.warning(
                f"Memory manager not available for {self.participant_identity}. Cannot add background knowledge."
            )
            return

        try:
            # Create a knowledge prompt to integrate with memory
            knowledge_prompt = f"[BACKGROUND KNOWLEDGE from {filename}]"
            knowledge_response = f"I have access to background knowledge from the file '{filename}'. Here's a summary:\n\n{content[:2000]}..."

            # Extract concepts and embeddings
            combined_text = f"{knowledge_prompt} {knowledge_response}".strip()
            concepts = self.memory_manager.extract_concepts(combined_text)
            embedding = self.memory_manager.get_embedding(combined_text)

            # Add to memory as a special interaction
            self.memory_manager.add_interaction(
                prompt=knowledge_prompt,
                output=knowledge_response,
                embedding=embedding,
                concepts=concepts,
            )

            logger.info(
                f"Added background knowledge from {filename} (ID: {file_id}) to memory for {self.participant_identity}"
            )

        except Exception as e:
            logger.error(
                f"Failed to add background knowledge from {filename}: {e}",
                exc_info=True,
            )

    def get_relevant_knowledge(self, query: str, max_results: int = 3) -> list[str]:
        """
        Retrieve relevant background knowledge based on a query.

        Args:
            query: The query to search for relevant knowledge
            max_results: Maximum number of results to return

        Returns:
            List of relevant knowledge snippets
        """
        if not self.memory_config.get("use", False) or self.memory_manager is None:
            return []

        try:
            # Use Memoripy's search functionality to find relevant context
            relevant_memories = self.memory_manager.get_memories(
                query=query, max_results=max_results
            )

            knowledge_snippets = []
            for memory in relevant_memories:
                # Filter for background knowledge entries
                if memory.get("prompt", "").startswith("[BACKGROUND KNOWLEDGE"):
                    output = memory.get("output", "")
                    if output:
                        knowledge_snippets.append(output)

            logger.debug(
                f"Retrieved {len(knowledge_snippets)} relevant knowledge snippets for query: {query[:50]}..."
            )
            return knowledge_snippets

        except Exception as e:
            logger.error(f"Error retrieving relevant knowledge: {e}")
            return []
