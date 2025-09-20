from rich import print
import agent_state as agent
import graph as g1

if __name__ == "__main__":
    finalState = g1.graph.invoke(agent.agentQA)
    print(finalState)
