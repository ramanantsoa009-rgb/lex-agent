### DEBUT IMPORT MODULES
import os
from dotenv import load_dotenv
from config_ia.conf_ia import conf_ia
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_mistralai import MistralAIEmbeddings
from langchain_mistralai import ChatMistralAI
from langchain_core.tools import tool
from supabase.client import Client, create_client
### FIN IMPORT MODULES

### Load environment variables
load_dotenv()

# initiating supabase
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase_table_name = os.environ.get("SUPABASE_TABLE_NAME")
supabase_query_name = os.environ.get("SUPABASE_QUERY_NAME")

# create a single instance of the Supabase client to be used throughout the app
supabase: Client = create_client(supabase_url, supabase_key)

# initiating embeddings model
embeddings = MistralAIEmbeddings(model=conf_ia.EMBEDDING_MODEL)

# initiating vector store
vector_store = SupabaseVectorStore(
    embedding=embeddings,
    client=supabase,
    table_name=supabase_table_name,
    query_name=supabase_query_name,
)
 
# initiating llm - IA
IA = ChatMistralAI(model=conf_ia.MODEL_NAME,temperature=conf_ia.TEMPERATURE, max_retries=conf_ia.MAX_RETRIES)

@tool(response_format="content_and_artifact")
def retrieve(query: str):
    """Retrieve information related to a query."""
    retrieved_docs = vector_store.similarity_search(query, k=2)
    serialized = "\n\n".join(
    (f"Source: {doc.metadata}\n" f"Content: {doc.page_content}")
        for doc in retrieved_docs
    )
    return serialized, retrieved_docs
    


