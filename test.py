from rich import print
from llm_client import get_llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.runnables import RunnableParallel
from utils.prompts import STEP1

# Testing hard coded FR
fr = "The first name field should only allow Latin letters, and the name must be between 2 and 25 characters."

step1 = ChatPromptTemplate.from_messages([
    {"role": "system", "content": STEP1["system_prompt"]},
    {"role": "user", "content": STEP1["user_prompt"]},
    {"role": "user", "content": fr}
])

llm = get_llm()
chain = RunnableParallel(
    prompt = step1 | llm | JsonOutputParser(),
)

result = chain.invoke({})
print(result)
# if not testing, should save to for example data/pdf_logbook/sample_pdf/fr_1/step1.json