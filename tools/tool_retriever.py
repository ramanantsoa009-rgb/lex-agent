### DEBUT IMPORT MODULES
import os
from dotenv import load_dotenv
from config_ia.conf_ia import conf_ia
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_mistralai import MistralAIEmbeddings
from langchain_mistralai import ChatMistralAI
from langchain_core.tools import tool
from supabase.client import Client, create_client
from supabase.lib.client_options import ClientOptions
### FIN IMPORT MODULES

### Load environment variables
load_dotenv()

# initiating supabase
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase_table_name = os.environ.get("SUPABASE_TABLE_NAME")
supabase_query_name = os.environ.get("SUPABASE_QUERY_NAME")

# create a single instance of the Supabase client to be used throughout the app
supabase: Client = create_client(
    supabase_url,
    supabase_key,
    options=ClientOptions(postgrest_client_timeout=60)
)

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
    """Retrieve Mauritian legal documents (legislation, case law, codes) relevant to a query. Always call this tool before answering any legal question."""
    try:
        retrieved_docs = vector_store.similarity_search(query, k=conf_ia.TOP_K_RESULTS)
    except Exception as e:
        return f"CORPUS_TIMEOUT: {type(e).__name__}: {str(e)[:300]}", []

    def make_id(meta: dict) -> str:
        if meta.get("id"):
            return str(meta["id"])
        title = meta.get("pdf", {}).get("info", {}).get("Title", "")
        lines = meta.get("loc", {}).get("lines", {})
        if title and lines:
            return f"{title.replace(' ', '-')}-L{lines.get('from', '?')}"
        return title or "UNKNOWN"

    serialized = "\n\n".join(
        f'<retrieved_context id="{make_id(doc.metadata)}">\n'
        f"Source: {doc.metadata}\n"
        f"Content: {doc.page_content}\n"
        f"</retrieved_context>"
        for doc in retrieved_docs
    )
    return serialized, retrieved_docs
    