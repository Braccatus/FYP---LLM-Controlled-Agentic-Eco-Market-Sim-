from mirascope import llm
from pydantic import BaseModel

class Answer(BaseModel):
    reasoning: str

@llm.call(provider="openai", model="gpt-4.1-mini", stream=True)
def interest_rate_change(percent: int) -> str:
    return f"Explain how a {percent}% change increase could affect an economy."

for chunk, _ in interest_rate_change(2):
    print(chunk.content or "", end="", flush=True)

    