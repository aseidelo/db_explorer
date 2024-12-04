from os.path import join
import json
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from typing import List, Dict
from llm.prompt_utils import (
    load_prompt_template_from_file,
    load_input_variables_from_prompt_template
)
from db.db import Db


class Agent:

    agent_name = "base_agent"
    description = "Base agent"
    prompt_template = "Answer the question: {question}"
    
    def __init__(
            self,
            llm: ChatOpenAI) -> None:

        self.complete_prompt_template = self.prompt_template + "\n\n{output_instructions}"
        self.llm = llm
        self.prompt_input_variables = load_input_variables_from_prompt_template(self.prompt_template)
        self.extended_variables = []
        self.input_variables = self.prompt_input_variables + self.extended_variables
        self.output_parser = JsonOutputParser(pydantic_object=self.OutputParser)
        self.prompt = PromptTemplate(
            template=self.complete_prompt_template,
            input_variables=self.prompt_input_variables,
            partial_variables={"output_instructions": self.output_parser.get_format_instructions()},
        )
        self.chain = self.prompt | self.llm | self.output_parser

    class OutputParser(BaseModel):
        response: str = Field(description="Query response")

    def __call__(self, **args):
        print(self.prompt.invoke(args).text)
        return self.chain.invoke(args)

    def short_description(self):
        return json.dumps(
            {
                'name': self.agent_name,
                'description': self.description,
                'input_variables': self.input_variables
            }
        )


class QueryAgent(Agent):

    agent_name = "query_agent"
    description = "Agent that generates a SQL query for a database given an natural language instruction"
    prompt_template = load_prompt_template_from_file(
        join('prompts', 'query_agent.txt')
    )

    def __init__(self, llm: ChatOpenAI, dbs: dict) -> None:
        super().__init__(llm)
        self.input_variables = ["instruction", "database_name", "database_metadata"]
        self.output_parser = JsonOutputParser(pydantic_object=self.OutputParser)
        self.prompt = PromptTemplate(
            template=self.complete_prompt_template,
            input_variables=self.input_variables,
            partial_variables={
                "output_instructions": self.output_parser.get_format_instructions()
            },
        )
        self.chain = self.prompt | self.llm | self.output_parser
        self.dbs = dbs

    class OutputParser(BaseModel):
        sql_query: str = Field(description="SQL query in the sqlalchemy text() format")
        parameters: dict = Field(description="Key-value pairs to substitute sql_query parameters")
    
    def __call__(self, **args):
        db = self.dbs[args["database_name"]]

        res = super().__call__(
            database_name=args["database_name"],
            database_metadata=db.full_description(),
            instruction=args["instruction"]
        )

        res['query_response'] = db.query(
            res['sql_query'],
            res['parameters']
        )
        return res

class ReasoningAgent(Agent):
    agent_name = "reasoning_agent"
    description = "Agent that answers a question given a context"
    prompt_template = load_prompt_template_from_file(
        join('prompts', 'reasoning_agent.txt')
    )

    def __init__(self, llm: ChatOpenAI) -> None:
        super().__init__(llm)


class AgentCall(BaseModel):
    agent_name: str = Field(description=f"Agent name")
    input_variables: dict = Field(description="Dict of input variables")


class PlannerAgent(Agent):
    agent_name = "planner_agent"
    description = "Agent that plans the steps to respond a question"
    prompt_template = load_prompt_template_from_file(
        join('prompts', 'planner_agent.txt')
    )    

    def __init__(self, llm: ChatOpenAI, agents: dict, dbs: List[Db]) -> None:
        super().__init__(llm)
        self.agents = agents
        self.dbs = dbs
        self.input_variables = ["instruction"]
        self.output_parser = JsonOutputParser(pydantic_object=self.OutputParser)
        self.prompt = PromptTemplate(
            template=self.complete_prompt_template,
            input_variables=self.input_variables,
            partial_variables={
                "agents": "\n".join([agent.short_description() for _, agent in self.agents.items()]),
                "databases": "\n".join([json.dumps(self.dbs[db_name].short_description()) for db_name in self.dbs]),
                "output_instructions": self.output_parser.get_format_instructions()
            },
        )
        self.chain = self.prompt | self.llm | self.output_parser


    class OutputParser(BaseModel):
        plan: List[AgentCall] = Field(description="List of agent calls")
