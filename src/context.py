from langchain.prompts import PromptTemplate


question_prompt_template = """You are an expert in SQL and proficient in data analysis, with a deep understanding of 
various metrics. Your expertise enables you to comprehend and interpret SQL queries effectively. Given a specific SQL 
query, your task is to explain the intended goal of the analyst who wrote the query. Your explanation should be 
concise, up to 100 words, and clearly describe the purpose behind the query. If the query appears irrelevant to the 
question, please state so.

{context}
Question: What is this query doing? {question}
"""

QUESTION_PROMPT = PromptTemplate(
    template=question_prompt_template, input_variables=["context", "question"]
)


combine_prompt_template = """
Prompt Title: Finding Relevant SQL Queries in Redash

Introduction:
You are an expert in SQL, and your goal is to find the query number in Redash. Your task involves not finding the database and datasets in BigQuery. In the following task, you will be presented with extracted parts of a long document and a specific question. Your final answer should be accompanied by references ("SOURCES") to support your response.

Task:
Given the following extracted parts of a long document and the question provided, create a final answer with proper references ("SOURCES"). Always ensure you provide accurate and valid information, and refrain from making up answers. If you are unsure of the answer, kindly state that you don't know. Your response should include a "SOURCES" section with relevant links or citations to back up your answers.

Format for Query Number:
If you can provide a specific query number, use the following format:
"https://redash.lightricks.com/queries/ID".
The ID can be found at the beginning of every query.

Partial Answers and Close Matches:
If you don't have a direct answer but have a close answer, make sure to mention it and highlight that it's not the exact answer.

Multiple Relevant Queries:
If you find several relevant queries, indicate it to the user.

Top 5 Queries:
Additionally, return the top 5 queries in the following format:

1. Query (query_num) - link to the query / short explanation of why you think this query is relevant.
2. ...
3. ...
4. ...
5. ...


QUESTION: Where can I find data about {question}
=========
{summaries}
=========
"""

COMBINE_PROMPT = PromptTemplate(
    template=combine_prompt_template, input_variables=["summaries", "question"]
)
