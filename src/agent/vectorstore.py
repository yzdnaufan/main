"""Class for a VectorStore-backed memory object."""

from typing import Any, Dict, List, Optional, Sequence, Union, Tuple

from langchain.memory.chat_memory import BaseChatMemory, BaseMemory
from langchain.memory.utils import get_prompt_input_key
from langchain.pydantic_v1 import Field
from langchain.schema import Document
from langchain.vectorstores.base import VectorStoreRetriever
from langchain.schema.messages import BaseMessage, ChatMessage, AIMessage, HumanMessage
from langchain.document_transformers import (
    LongContextReorder,
)

class ConversationVectorStoreRetrieverMemory(BaseChatMemory):
    """VectorStoreRetriever-backed memory."""

    retriever: VectorStoreRetriever = Field(exclude=True)
    """VectorStoreRetriever object to connect to."""

    memory_key: str = "chat_history"  #: :meta private:
    """Key name to locate the memories in the result of load_memory_variables."""

    input_key: Optional[str] = "input"
    """Key name to index the inputs to load_memory_variables."""

    user_id_key: Optional[str] = "user_id"
    """Key name to index the user_id to load_memory_variables."""

    output_key: Optional[str] = "output"
    """Key name to index the outputs to load_memory_variables."""

    separator: str = " <NEO_SEPARATOR> "
    """Separator to use between inputs and outputs when formatting the document."""

    return_docs: bool = False
    """Whether or not to return the result of querying the database directly."""

    exclude_input_keys: Sequence[str] = Field(default_factory=tuple)
    """Input keys to exclude in addition to memory key when constructing the document"""

    human_prefix: str = "Human"
    ai_prefix: str = "AI"
    system_prefix: str = "System"

    @property
    def memory_variables(self) -> List[str]:
        """The list of keys emitted from the load_memory_variables method."""
        return [self.memory_key]

    def _get_prompt_input_key(self, inputs: Dict[str, Any]) -> str:
        """Get the input key for the prompt."""
        if self.input_key is None:
            return get_prompt_input_key(inputs, self.memory_variables)
        return self.input_key
    
    def _conversation_message_to_document(self, input: HumanMessage, output: AIMessage, user_id: str) -> Document:
        """Format context from this conversation to buffer."""
        # Each document should only include the current turn, not the chat history
        texts = [
            f"{input}",
            f"{output}",
        ]

        page_content = self.separator.join(texts)
        return Document(
            page_content=page_content,
            metadata={
                self.user_id_key : str(user_id),
            }
        )
    
    def _document_to_conversation_message(self, document: Document) -> Tuple[HumanMessage, AIMessage]:
        """Format context from this conversation to buffer."""
        # Each document should only include the current turn, not the chat history
        texts = document.page_content.split(self.separator)
        # print(f"texts -> {texts}")

        try:
            human_message = HumanMessage(content=texts[0])
            ai_message = AIMessage(content=texts[1])
        except Exception as e:
            human_message = HumanMessage(content=texts[0])
            ai_message = AIMessage(content="")
        
        return human_message, ai_message

    def load_memory_variables(
        self, inputs: Dict[str, Any]
    ) -> Dict[str, Union[List[Any], str]]:
        """Return history buffer."""
        input_key = self._get_prompt_input_key(inputs)
        query = inputs[input_key]
        print(f"load_memory_variables -> {query}")
        try:
            docs = self.retriever.get_relevant_documents(query)
        except Exception as e:
            print(f"Exception load_memory_variables -> {e}")
            docs = []

        reordering = LongContextReorder()
        reordered_docs = reordering.transform_documents(docs)

        result: Union[List[BaseMessage], List[Document], str]
        if self.return_messages:
            result = [message for doc in reordered_docs for message in self._document_to_conversation_message(doc)]
        elif not self.return_docs:
            result = "\n".join([doc.page_content for doc in docs])
        else:
            result = docs

        # print(f"result -> {result}")
        return {self.memory_key: result}

    def _form_documents(
        self, inputs: Dict[str, Any], outputs: Dict[str, str]
    ) -> List[Document]:
        """Format context from this conversation to buffer."""
        # Each document should only include the current turn, not the chat history
        input_key = self._get_prompt_input_key(inputs)
        exclude = set(self.exclude_input_keys)
        exclude.add(self.memory_key)
        filtered_inputs = {k: v for k, v in inputs.items() if k not in exclude}

        document = self._conversation_message_to_document(filtered_inputs[input_key], outputs[self.output_key], filtered_inputs[self.user_id_key])
        print(f"document -> {document}")

        return [document]

    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, str]) -> None:
        """Save context from this conversation to buffer."""
        print(f"save_context -> {inputs} -> {outputs}")
        documents = self._form_documents(inputs, outputs)
        self.retriever.add_documents(documents)

    def clear(self) -> None:
        """Nothing to clear."""