# import basics
import os
from dotenv import load_dotenv

from langchain.agents import AgentExecutor

# from langchain_openai import ChatOpenAI
from langchain_mistralai import ChatMistralAI

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from langchain.agents import create_tool_calling_agent
from langchain_core.prompts import PromptTemplate
from langchain_community.vectorstores import SupabaseVectorStore

# from langchain_openai import OpenAIEmbeddings
from langchain_mistralai import MistralAIEmbeddings

from langchain import hub

from supabase.client import Client, create_client
from langchain_core.tools import tool

# load environment variables
load_dotenv()  

# initiate supabase database
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")

supabase: Client = create_client(supabase_url, supabase_key)

# initiate embeddings model
embeddings = MistralAIEmbeddings(model="mistral-embed")

# initiate vector store
vector_store = SupabaseVectorStore(
    embedding=embeddings,
    client=supabase,
    table_name="embed_documents_mistral",
    query_name="match_documents_mistral",
)

# initiate large language model (temperature = 0)
llm = ChatMistralAI(temperature=0)

# fetch the prompt from the prompt hub
prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "Tu es un assistant juridique expert spécialisé dans le droit mauricien. "
        "Utilise les outils à ta disposition pour rechercher des informations précises dans le code civil "
        "avant de répondre. Si tu ne trouves pas l'information, dis-le honnêtement."
    ),
    (
        "human", "{input}"
    ),
    # Le placeholder ci-dessous est OBLIGATOIRE pour les agents : 
    # c'est là que l'historique des appels d'outils et leurs réponses sont injectés.
    (
        "placeholder", "{agent_scratchpad}"
    ),
])

# create the tools
@tool(response_format="content_and_artifact")
def retrieve(query: str):
    """Retrieve information related to a query."""
    retrieved_docs = vector_store.similarity_search(query, k=2)
    serialized = "\n\n".join(
        (f"Source: {doc.metadata}\n" f"Content: {doc.page_content}")
        for doc in retrieved_docs
    )
    return serialized, retrieved_docs

# combine the tools and provide to the llm
tools = [retrieve]
agent = create_tool_calling_agent(llm, tools, prompt)

# create the agent executor
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# invoke the agent
response = agent_executor.invoke({"input": "Donne moi un exemple d'article judiciaire de Maurice dans le code civil"})

# put the result on the screen
print(response["output"])