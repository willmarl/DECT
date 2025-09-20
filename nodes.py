from schema import QAschema
import agent_state as agent

def userInput(state: QAschema):
    x = input("Ask question >> ")
    state.debug = x
    return state

def aiResponse(state: QAschema):
    response = agent.llm.invoke(state.debug)
    state.debug = response.content # type: ignore
    return state