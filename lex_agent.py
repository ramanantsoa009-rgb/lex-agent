import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

# ── Tes imports existants (inchangés) ────────────────────────────────────────

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate
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
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

tools = [retrieve]
agent = create_tool_calling_agent(IA, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(title="LexMaurice API", version="1.0.0")

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
        result = agent_executor.invoke({
            "input": current_question,
            "chat_history": chat_history,
        })
        return ChatResponse(message=result["output"])

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Lancement direct ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 3002))
    uvicorn.run(app, host="0.0.0.0", port=port)