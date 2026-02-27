from mirascope import llm
from openai import OpenAI
from pydantic import BaseModel

class Capital(BaseModel):
    city: str
    country: str

@llm.call(provider="openai", model="gpt-4.1-mini", response_model=Capital)
def extract_capital(query: str) -> str:
    return f"{query}"

capital = extract_capital("The capital of Italy is Rome")
#print(capital)

@llm.call(provider="openai", model="gpt-4.1-mini", json_mode=True)
def city_info(city: str) -> str:
    return f"Provide information about {city} in JSON format"

response = city_info("Rome")
#print(response)

#JSON WITH RESPONSE MODEL

class CityInfo(BaseModel):
    population: str
    famous_for: str

@llm.call(provider="openai", model="gpt-4.1-mini", response_model=CityInfo, json_mode=True)
def city_information(city: str) -> str:
    return f"Provide information about {city} in JSON format"

response = city_information("Athens")
#print(response)
#print(response.population)
#print(response.famous_for)


@llm.call(provider="openai", model="gpt-4.1-mini", stream=True)
def stream_city_info(percent:int) -> int:
    return f"How would a {percent}% interest rate increase, affect the market?"

for chunk, _ in stream_city_info("2"):
    print(chunk.content, end="", flush=True)
