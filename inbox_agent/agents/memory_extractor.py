from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate

from memory.extractor import MemoryCandidate


parser = PydanticOutputParser(
    pydantic_object=MemoryCandidate
)

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You are a Memory Extraction Agent.

Extract ONLY information that should be remembered for future interactions.

Store:

- preferences
- communication style
- language
- recurring workflow preferences
- calendar preferences

Never infer facts that are not explicitly stated.

Never invent memories.

Return JSON only.

{format_instructions}
""",
        ),
        (
            "human",
            "{text}",
        ),
    ]
).partial(
    format_instructions=parser.get_format_instructions()
)