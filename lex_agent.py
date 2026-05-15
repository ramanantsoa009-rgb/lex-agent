import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

# ── Tes imports existants (inchangés) ────────────────────────────────────────

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage
from config_ia.conf_ia import conf_ia
from tools.tool_retriever import retrieve
from prompts import system_prompt

load_dotenv()

# ── Agent (exactement ton code, rien ne change) ───────────────────────────────
IA = ChatMistralAI(
    model=conf_ia.MODEL_NAME,
    temperature=conf_ia.TEMPERATURE,
    max_retries=conf_ia.MAX_RETRIES
)

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt.SYSTEM_PROMPT),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

tools = [retrieve]
agent = create_tool_calling_agent(IA, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(title="LexMaurice API - Update Test", version="1.0.0")

# CORS — autorise ton app Lovable à appeler l'API
allowed_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Modèles de données ────────────────────────────────────────────────────────
class Message(BaseModel):
    role: str       # "user" ou "assistant"
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]

class ChatResponse(BaseModel):
    message: str
    source: str
    code: str = "200"
    formattedError: str = ""

# ── Conversion du format frontend vers format LangChain ───────────────────────
def to_langchain_history(messages: List[Message]):
    """
    Convertit la liste de messages du frontend en historique LangChain.
    On exclut le dernier message (c'est la question courante, pas l'historique).
    """
    history = []
    for msg in messages[:-1]:   # tout sauf le dernier
        if msg.role == "user":
            history.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            history.append(AIMessage(content=msg.content))
    return history

# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/")
def health_check():
    return {"status": "LexMaurice API is running", "version": "1.0.0"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not request.messages:
        raise HTTPException(status_code=400, detail="No messages provided")

    # Question courante = dernier message
    current_question = request.messages[-1].content

    # Historique = tout ce qui precede, au format LangChain
    chat_history = to_langchain_history(request.messages)

    try:
        # Récupération forcée — le modèle 3B ne call pas le tool de lui-même
        retrieved_content, _ = retrieve.func(current_question)

        # Injection du contexte directement dans le prompt
        enriched_input = (
            f"<retrieved_context>\n{retrieved_content}\n</retrieved_context>\n\n"
            f"{current_question}"
        )

        result = agent_executor.invoke({
            "input": enriched_input,
            "chat_history": chat_history,
        })

        # Extraction des sources depuis le contenu récupéré
        sources = [line for line in retrieved_content.split('\n') if line.startswith("Source: ")]
        source_str = "\n".join(sources) if sources else "No sources available"

        return ChatResponse(message=result["output"], source=source_str)

    except Exception as e:
        error_str = str(e)
        if "57014" in error_str or "statement timeout" in error_str.lower():
            return ChatResponse(
                message="La base de données juridique est temporairement indisponible (délai de recherche dépassé). Veuillez réessayer dans quelques instants.",
                source="No sources available",
                code="503",
                formattedError="statement timeout"
            )
        raise HTTPException(status_code=500, detail=error_str)


# ── Lancement direct ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 3002))
    uvicorn.run(app, host="0.0.0.0", port=port)