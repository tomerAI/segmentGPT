import functools
from typing import List, TypedDict, Annotated
from langchain_core.messages import BaseMessage
from langchain_openai.chat_models import ChatOpenAI
from utilities.helper import HelperUtilities
from tools.tool_empty import EmptyTool
from tools.tool_metadata import MetadataTool
from tools.tool_sql import SQLTool
import operator

class SQLTeamState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    team_members: List[str]
    next: str

class SQLTeam:
    def __init__(self, llm_model):
        self.llm = ChatOpenAI(model=llm_model)
        self.utilities = HelperUtilities()
        self.tools = {
            'metadata': MetadataTool(),
            'sql': SQLTool(),
            'placeholder': EmptyTool()
        }

    def metadata_agent(self):
        metadata_agent = self.utilities.create_agent(
            self.llm,
            [self.tools['metadata']],
            """
            Your task is to retrieve and return metadata from the PostgreSQL database. 
            Use the provided tools to gather information about tables, columns, data types, and indexes specific to PostgreSQL.
            """
        )
        return functools.partial(self.utilities.agent_node, agent=metadata_agent, name="MetadataAgent")

    def sql_creation_agent(self):
        sql_creation_agent = self.utilities.create_agent(
            self.llm,
            [self.tools['placeholder']],
            """
            Your task is to create PostgreSQL queries based on the user's request. 
            Ensure the SQL code aligns with the PostgreSQL database schema and the user’s intent.
            Consider any PostgreSQL-specific functions or optimizations that could be applied.
            """
        )
        return functools.partial(self.utilities.agent_node, agent=sql_creation_agent, name="SQLCreationAgent")

    def sql_review_agent(self):
        sql_review_agent = self.utilities.create_agent(
            self.llm,
            [self.tools['placeholder']],
            """
            Your task is to review the PostgreSQL query for syntax errors, security vulnerabilities, and performance issues. 
            Pay special attention to PostgreSQL-specific syntax and best practices.
            Ensure that the query follows PostgreSQL standards and optimizations, such as using appropriate indexing, joins, and constraints.
            """
        )
        return functools.partial(self.utilities.agent_node, agent=sql_review_agent, name="SQLReviewAgent")

    def sql_execution_agent(self):
        sql_execution_agent = self.utilities.create_agent(
            self.llm,
            [self.tools['sql']],
            """
            Your task is to execute the PostgreSQL query and return the results. 
            Ensure that the execution is efficient and that the connection to the PostgreSQL database is securely managed.
            Handle any errors or exceptions that may arise during query execution.
            """
        )
        return functools.partial(self.utilities.agent_node, agent=sql_execution_agent, name="SQLExecutionAgent")

    def output_formatting_agent(self):
        """Creates an agent that summarizes the results of a PostgreSQL query execution."""
        output_agent = self.utilities.create_agent(
            self.llm,
            [self.tools['placeholder']],
            """
            Your task is to summarize the output of the executed PostgreSQL query. 
            Provide a concise summary that captures the key points of the data, including any notable trends, counts, or statistics.
            
            Ensure the summary is easy to understand and highlights the most relevant information for the user.
            Focus on PostgreSQL-specific data types and formatting when summarizing the results.
            """
        )
        return functools.partial(self.utilities.agent_node, agent=output_agent, name="OutputFormattingAgent")

    def supervisor_agent(self, members: List[str]):
        supervisor_agent = self.utilities.create_team_supervisor(
            self.llm,
            """
            You are the supervisor managing a PostgreSQL query execution workflow. Your role is to ensure that each agent performs their task correctly and in the proper sequence. 

            The agents you have at your disposal are:
            - MetadataAgent: Retrieves the necessary metadata from the PostgreSQL database.
            - SQLCreationAgent: Generates the SQL code based on the user query and the available metadata.
            - SQLReviewAgent: Reviews the generated SQL code to ensure it is syntactically correct, efficient, and secure.
            - SQLExecutionAgent: Executes the approved SQL code on the PostgreSQL database.
            - OutputFormattingAgent: Summarizes the results of the executed SQL query to provide a clear and concise output.
            
            The preferred workflow is as follows:
            1. Begin with MetadataAgent to gather the necessary information about the database structure.
            2. Pass this metadata to SQLCreationAgent to generate the appropriate SQL query.
            3. Send the generated SQL to SQLReviewAgent for a thorough review.
            4. If the SQL code meets our high standards, proceed to SQLExecutionAgent to run the query.
            5. Once the query is executed, pass the results to OutputFormattingAgent to create a summary.
            6. Finally, return the formatted summary to the user.

            If any agent's output does not meet the expected standards, especially during the review phase, employ an iterative approach. Send the task back to the relevant agent for refinement until the output is of the highest quality.

            Your primary goal is to ensure a seamless and efficient workflow that consistently delivers accurate, secure, and high-quality results that meet the user's needs.
            """,
            members
        )
        return supervisor_agent
