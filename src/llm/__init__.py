from typing import List
import json
import copy
from langchain_openai import ChatOpenAI
from llm.agents import (
    QueryAgent,
    ReasoningAgent,
    PlannerAgent
)
from db.db import Db


class ContextManager:
    def __init__(self, llm: ChatOpenAI, dbs: List[Db]) -> None:
        self.llm = llm

        self.dbs = {
            f"{db.db_name}": db
            for db in dbs
        }
    
        query_agent = QueryAgent(llm, self.dbs)
        reasoning_agent = ReasoningAgent(llm)

        self.agents = {
            query_agent.agent_name: query_agent,
            reasoning_agent.agent_name: reasoning_agent
        }

        self.planner_agent = PlannerAgent(
            llm,
            self.agents,
            self.dbs
        )

    def answer(self, question: str):
        
        answer_plan = self.planner_agent(
            instruction=question
        )["plan"]

        context = [
            {
                "speaker": self.planner_agent.agent_name,
                "speech": answer_plan
            }
        ]

        for instruction in answer_plan:
            agent = self.agents[instruction['agent_name']]

            if 'context' in instruction['input_variables']:
                instruction['input_variables']['context'] = copy.deepcopy(context)

            response = agent(**instruction['input_variables'])

            context.append(
                {
                    "speaker": agent.agent_name,
                    "speech": response
                }
            )
        
        return context
