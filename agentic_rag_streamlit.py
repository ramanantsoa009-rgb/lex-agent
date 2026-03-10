# import basics
import os
from dotenv import load_dotenv
import streamlit as st
from langchain.agents import AgentExecutor
from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage, HumanMessage
from langchain.agents import create_tool_calling_agent
from config_ia.conf_ia import conf_ia
from tools.tool_retriever import retrieve
from prompts import system_prompt

# load environment variables
load_dotenv()
 
# initiating llm
IA = ChatMistralAI(model=conf_ia.MODEL_NAME,temperature=conf_ia.TEMPERATURE, max_retries=conf_ia.MAX_RETRIES)

# defining the prompt template for the agent 
prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        system_prompt.SYSTEM_PROMPT
    ),
    (
        "human", "{input}"
    ),
    (
        "placeholder", "{agent_scratchpad}"
    ),
])

# combining all tools in a list
tools = [retrieve]

# initiating the agent
agent = create_tool_calling_agent(IA, tools, prompt)

# create the agent executor
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# initiating streamlit app
st.set_page_config(
    page_title="Lex - Nexsus RAG",
    page_icon="")
st.title("Lex - Nexsus RAG Agent")

# initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# display chat messages from history on app rerun
for message in st.session_state.messages:
    if isinstance(message, HumanMessage):
        with st.chat_message("user"):
            st.markdown(message.content)
    elif isinstance(message, AIMessage):
        with st.chat_message("assistant"):
            st.markdown(message.content)

# create the bar where we can type messages // html placeholder for the user input
user_question = st.chat_input("Poser votre question ici...")

# did the user submit a request ?
if user_question:
    # add the message from the user (prompt) to the screen with streamlit
    with st.chat_message("user"):
        st.markdown(user_question)
        st.session_state.messages.append(HumanMessage(user_question))

    # invoking the agent
    result = agent_executor.invoke({"input": user_question, "chat_history":st.session_state.messages})
    ai_message = result["output"]

    # adding the response from the llm to the screen (and chat)
    with st.chat_message("assistant"):
        st.markdown(ai_message)
        st.session_state.messages.append(AIMessage(ai_message))