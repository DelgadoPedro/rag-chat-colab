## Agent in which a human passes continuous feedback to draft a document, until the human is satisifed 

import os
import json
from typing import Annotated, Sequence, TypedDict, Callable, Optional
import difflib
import re

from langchain_core.messages import BaseMessage, ToolMessage, SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from sentence_transformers import SentenceTransformer
from langgraph.graph import StateGraph, END
from langchain_text_splitters  import RecursiveCharacterTextSplitter
from langchain_core.tools import tool
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader

from operator import add as add_messages
from dotenv import load_dotenv

def build_llm(model: str = "nvidia/nemotron-nano-12b-v2-vl:free", temperature: float = 0):
    llm = ChatOpenAI(
        model=model,
        api_key=os.environ.get("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
        temperature=temperature
    )
    return llm

def build_embeddings(embedding_model_name: str = "all-MiniLM-L6-v2"):
    class SentenceTransformerEmbeddings:
        def __init__(self, model_name):
            self.model = SentenceTransformer(model_name, device="cpu")

        def embed_documents(self, texts):
            return self.model.encode(texts, convert_to_tensor=False)

        def embed_query(self, text):
            return self.model.encode([text], convert_to_tensor=False)[0]

    return SentenceTransformerEmbeddings(embedding_model_name)

def load_pdf_pages(file_path: str, source_name: Optional[str] = None):
    """Load pages from a PDF and annotate each page's metadata with a stable source name.

    If `source_name` is provided, it will be used for `source_file` in metadata. This
    prevents temporary filenames from leaking into chunk metadata when files are
    uploaded and written to temporary paths.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    loader = PyPDFLoader(file_path)
    pages = loader.load()
    # Use the provided source_name if given, otherwise the basename of the path
    basename = source_name or os.path.basename(file_path)
    for idx, page in enumerate(pages):
        try:
            meta = page.metadata or {}
        except Exception:
            meta = {}
        # prefer existing page number metadata if present, else use index+1
        page_number = meta.get("page") or meta.get("page_number") or (idx + 1)
        meta["source_file"] = basename
        meta["page_number"] = page_number
        page.metadata = meta
    return pages

def build_vectorstore_from_pages(pages, embeddings, persist_directory: str = "./vdb", collection_name: str = "book"):
    if not os.path.exists(persist_directory):
        os.makedirs(persist_directory)

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    # Split each page individually so that chunk metadata keeps the originating page metadata
    chunks = []
    for page in pages:
        page_chunks = splitter.split_documents([page])
        for ch in page_chunks:
            # ensure chunk metadata contains source_file and page_number
            try:
                ch_meta = ch.metadata or {}
            except Exception:
                ch_meta = {}
            # overlay page metadata (page metadata takes precedence)
            page_meta = getattr(page, "metadata", {}) or {}
            merged = {**ch_meta, **page_meta}
            ch.metadata = merged
            chunks.append(ch)

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=persist_directory,
        collection_name=collection_name,
    )
    return vectorstore


def load_vectorstore_from_persist(persist_directory: str = "./vdb", collection_name: str = "book", embeddings=None):
    if not os.path.exists(persist_directory):
        raise FileNotFoundError(f"Persist directory not found: {persist_directory}")
    if embeddings is None:
        embeddings = build_embeddings()

    vectorstore = Chroma(
        persist_directory=persist_directory,
        collection_name=collection_name,
        embedding_function=embeddings,
    )
    return vectorstore

def build_retriever(vectorstore, k: int = 7):
    return vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": k})

def build_agent(retriever, llm, history_file: Optional[str] = None):
    history_path = history_file or os.environ.get("RAG_HISTORY_FILE") or os.path.join("./vdb", "conversation_history.txt")

    def get_participants_from_history(max_messages: int = 200):
        if not os.path.exists(history_path):
            return []
        try:
            with open(history_path, "r", encoding="utf-8") as fh:
                lines = fh.read().splitlines()
        except Exception:
            return []
        participants = []
        seen = set()
        for line in lines[-max_messages:]:
            parts = line.split("::", 2)
            if len(parts) < 3:
                continue
            role, user = parts[0], parts[1]
            if role.strip().lower() != "user":
                continue
            user = user.strip() or "Usuário"
            if user not in seen:
                seen.add(user)
                participants.append(user)
        return participants

    @tool
    def retriever_tool(query: str) -> str:
        """Search and return relevant chunks from the loaded PDF.

        The returned text includes simple citations (source file and page number)
        alongside the chunk content to help the LLM cite the origin.
        """
        source_name = None
        search_query = query
        try:
            m = re.search(r"source\s*:\s*([^\n,;]+)", query, flags=re.IGNORECASE)
            if not m:
                m = re.search(r"from\s+[\"']?([^\n\"'.,;]+)[\"']?", query, flags=re.IGNORECASE)
            if m:
                source_name = m.group(1).strip()
                search_query = (query[:m.start()] + query[m.end():]).strip()
        except Exception:
            source_name = None

        docs = retriever.invoke(search_query)
        if not docs:
            return "No relevant info was found in the document"
        results = []
        available_sources = []
        for d in docs:
            meta = getattr(d, "metadata", {}) or {}
            src = meta.get("source_file", meta.get("source"))
            if src and src not in available_sources:
                available_sources.append(src)

        filtered_docs = docs
        matched_source = None
        if source_name:
            matches = difflib.get_close_matches(source_name, available_sources, n=1, cutoff=0.6)
            if matches:
                matched_source = matches[0]
                filtered_docs = [d for d in docs if (getattr(d, "metadata", {}) or {}).get("source_file") == matched_source]
            else:
                lowered = {s.lower(): s for s in available_sources}
                if source_name.lower() in lowered:
                    matched_source = lowered[source_name.lower()]
                    filtered_docs = [d for d in docs if (getattr(d, "metadata", {}) or {}).get("source_file") == matched_source]
                else:
                    return f"No document found matching '{source_name}'. Available: {', '.join(available_sources) if available_sources else 'none'}"

        for i, doc in enumerate(filtered_docs):
            meta = getattr(doc, "metadata", {}) or {}
            source = meta.get("source_file", meta.get("source", "unknown"))
            page_no = meta.get("page_number", meta.get("page", "?"))
            snippet = doc.page_content.strip()
            citation = f"(source: {source}, page: {page_no})"
            results.append(f"Document {i+1} {citation}:\n{snippet}")
        if matched_source:
            note = f"[Filtered to source: {matched_source}]\n\n"
        else:
            note = ""
        return "\n\n".join(results)
    
    @tool
    def conversation_history_tool(query: str) -> str:
        """Return the most recent N messages from a conversation history text file.

        The query can be an integer (as string) indicating how many recent messages to return.
        Defaults to 20 and will never return more than 20 messages.
        """
        try:
            n = int(query.strip()) if query and query.strip().isdigit() else 20
        except Exception:
            n = 20
        n = max(0, min(20, n))
        if not os.path.exists(history_path):
            return "No conversation history found."
        try:
            with open(history_path, "r", encoding="utf-8") as fh:
                lines = fh.read().splitlines()
        except Exception as e:
            return f"Error reading history file: {e}"

        last_lines = lines[-n:]
        return "\n".join(last_lines) if last_lines else "No conversation history available."

    @tool
    def fixation_exercise_tool(query: str) -> str:
        """Prepare guidance for creating fixation exercises per active participant.

        The query may describe a focus topic (e.g. "capítulo 2" or "métodos").
        The tool aggregates participants seen in the conversation so far,
        retrieves relevant document chunks, and includes conversation history
        to contextualize the exercises based on what was discussed.
        """
        topic = query.strip() if query and query.strip() else "panorama geral dos artigos"
        participants = get_participants_from_history()
        if not participants:
            participants = ["Grupo"]

        # Ler histórico do chat
        conversation_history = ""
        if os.path.exists(history_path):
            try:
                with open(history_path, "r", encoding="utf-8") as fh:
                    lines = fh.read().splitlines()
                # Pegar últimas 30 mensagens para contexto
                recent_lines = lines[-30:] if len(lines) > 30 else lines
                conversation_history = "\n".join(recent_lines) if recent_lines else ""
            except Exception as e:
                conversation_history = f"Erro ao ler histórico: {e}"

        # Buscar trechos relevantes dos artigos
        reference_chunks = []
        try:
            # Se houver histórico, usar termos do histórico + tópico para buscar
            search_query = topic
            if conversation_history:
                # Extrair palavras-chave do histórico para melhorar busca
                words = conversation_history.lower().split()
                # Pegar palavras mais frequentes (excluindo stopwords simples)
                stopwords = {"o", "a", "os", "as", "de", "da", "do", "das", "dos", "em", "no", "na", "que", "para", "com", "é", "um", "uma", "e", "ou", "se", "não", "ser", "ter", "fazer", "dizer", "colaborai", "@colaborai"}
                keywords = [w for w in words if len(w) > 3 and w not in stopwords]
                if keywords:
                    # Adicionar algumas palavras-chave ao tópico
                    extra_keywords = " ".join(set(keywords[:5]))
                    search_query = f"{topic} {extra_keywords}".strip()
            
            docs = retriever.invoke(search_query) if search_query else retriever.invoke("principais ideias dos artigos")
        except Exception as e:
            docs = []
            reference_chunks.append({"source": "erro", "page": "-", "excerpt": f"Falha ao consultar repositório: {e}"})

        for doc in docs[:6]:  # Aumentar para 6 trechos para ter mais contexto
            meta = getattr(doc, "metadata", {}) or {}
            source = meta.get("source_file", meta.get("source", "desconhecido"))
            page_no = meta.get("page_number", meta.get("page", "?"))
            snippet = (doc.page_content or "").strip()
            if not snippet:
                continue
            snippet = snippet[:500] + ("..." if len(snippet) > 500 else "")
            reference_chunks.append(
                {
                    "source": source,
                    "page": page_no,
                    "excerpt": snippet,
                }
            )

        payload = {
            "topic": topic,
            "participants": participants,
            "conversation_history": conversation_history if conversation_history else "Nenhum histórico de conversa disponível.",
            "instructions": (
                "Crie exercícios de fixação de DIFICULDADE MEDIANA para cada participante listado. "
                "IMPORTANTE: Os exercícios devem:\n"
                "1. Abordar diretamente os artigos científicos anexados, utilizando os trechos fornecidos como base.\n"
                "2. Focar em CONCEITOS IMPORTANTES e fundamentais dos documentos, não em detalhes triviais.\n"
                "3. Ter dificuldade mediana: não sejam muito fáceis (respostas óbvias) nem muito difíceis (requerendo conhecimento avançado não presente nos artigos).\n"
                "4. Testar compreensão, aplicação e análise dos conceitos apresentados nos artigos.\n"
                "5. Incluir referências explícitas aos artigos (fonte e página) quando apropriado.\n"
                "6. Considerar o contexto da conversa para criar perguntas relevantes ao que foi discutido.\n\n"
                "FORMATO DE SAÍDA:\n"
                "- Apresente os exercícios organizados por participante.\n"
                "- Cada exercício deve ser claro, específico e relacionado aos artigos.\n"
                "- Use os trechos dos artigos fornecidos para criar perguntas que testem a compreensão dos conceitos importantes.\n"
                "- Ao final de TODA a mensagem, inclua uma seção 'RESPOSTAS' ou 'GABARITO' com todas as respostas dos exercícios propostos.\n"
                "- As respostas devem ser completas, explicativas e referenciar os artigos quando aplicável."
            ),
            "reference_chunks": reference_chunks if reference_chunks else [{"source": "N/A", "page": "-", "excerpt": "Nenhum trecho disponível dos artigos."}],
        }
        return json.dumps(payload, ensure_ascii=False)

    tools = [retriever_tool, conversation_history_tool, fixation_exercise_tool]
    llm_with_tools = llm.bind_tools(tools)

    class AgentState(TypedDict):
        messages: Annotated[Sequence[BaseMessage], add_messages]

    def should_continue(state: AgentState):
        # Inspect the last message's tool calls and return the tool name
        last = state["messages"][-1]
        if not hasattr(last, "tool_calls") or len(last.tool_calls) == 0:
            return False
        # return the first tool name called (graph can decide routing based on this)
        tool_name = last.tool_calls[0].get("name") if isinstance(last.tool_calls[0], dict) else getattr(last.tool_calls[0], "name", None)
        return tool_name or False

    system_prompt = (
        "Você é um assistente que responde perguntas sobre os PDFs carregados na base de conhecimento. "
        "IMPORTANTE: SEMPRE responda em PORTUGUÊS. Todas as suas respostas devem estar em português brasileiro.\n\n"
        "Quando a informação depende do conteúdo recuperado dos documentos, inclua citações concisas às partes específicas do documento (ex: nome do arquivo e número da página). "
        "Apenas adicione citações quando elas suportam materialmente a resposta ou quando são diretamente relevantes — evite adicionar citações para observações triviais ou especulativas. "
        "Se você citar ou parafrasear um trecho recuperado, anexe uma citação curta entre parênteses após a sentença relevante (formato: source: <filename>, page: <n>).\n\n"
        "Ao usar a fixation_exercise_tool, siga cuidadosamente as instruções fornecidas na resposta da tool. "
        "Crie exercícios de DIFICULDADE MÉDIA que foquem em CONCEITOS IMPORTANTES dos artigos. "
        "Sempre inclua uma seção 'RESPOSTAS' ou 'GABARITO' no final com respostas completas e explicativas que referenciem os artigos quando aplicável."
    )

    tools_dict = {t.name: t for t in tools}

    def get_recent_history_messages(n: int = 5):
        """Lê as últimas N mensagens do histórico e converte para mensagens do LangChain."""
        if not os.path.exists(history_path):
            return []
        try:
            with open(history_path, "r", encoding="utf-8") as fh:
                lines = fh.read().splitlines()
            recent_lines = lines[-n:] if len(lines) > n else lines
            history_messages = []
            for line in recent_lines:
                parts = line.split("::", 2)
                if len(parts) < 3:
                    continue
                role, user, content = parts[0].strip(), parts[1].strip(), parts[2].strip()
                if role.lower() == "user":
                    # Formatar mensagem do usuário com o nome
                    formatted_content = f"{user}: {content}" if user else content
                    history_messages.append(HumanMessage(content=formatted_content))
                elif role.lower() == "assistant":
                    history_messages.append(AIMessage(content=content))
            return history_messages
        except Exception:
            return []

    def call_llm(state: AgentState) -> AgentState:
        msgs = list(state["messages"])
        # Adicionar últimas 5 mensagens do histórico para contexto
        history_msgs = get_recent_history_messages(5)
        # Combinar: system prompt + histórico + mensagens atuais
        msgs = [SystemMessage(content=system_prompt)] + history_msgs + msgs
        message = llm_with_tools.invoke(msgs)
        return {"messages": [message]}

    def take_action(state: AgentState) -> AgentState:
        tool_calls = state["messages"][-1].tool_calls
        results = []
        for t in tool_calls:
            tool_name = t["name"]
            args_query = t["args"].get("query", "")
            if tool_name not in tools_dict:
                result = "Incorrect tool name; select an available tool and try again."
            else:
                result = tools_dict[tool_name].invoke(args_query)
            results.append(ToolMessage(tool_call_id=t["id"], name=tool_name, content=str(result)))
        return {"messages": results}

    graph = StateGraph(AgentState)
    graph.add_node("llm", call_llm)
    graph.add_node("retriever", take_action)
    graph.add_node("history", take_action)
    graph.add_node("exercise", take_action)

    # Route based on which tool was called.
    graph.add_conditional_edges(
        "llm",
        should_continue,
        {
            "retriever_tool": "retriever",
            "conversation_history_tool": "history",
            "fixation_exercise_tool": "exercise",
            False: END,
        },
    )
    graph.add_edge("retriever", "llm")
    graph.add_edge("history", "llm")
    graph.add_edge("exercise", "llm")
    graph.set_entry_point("llm")
    return graph.compile()


def run_rag_agent_cli(file_path: str = "file.pdf", persist_directory: str = "./vdb"):
    load_dotenv()
    llm = build_llm()
    embeddings = build_embeddings()
    pages = load_pdf_pages(file_path)
    vectorstore = build_vectorstore_from_pages(pages, embeddings, persist_directory=persist_directory)
    retriever = build_retriever(vectorstore)
    agent = build_agent(retriever, llm)

    print("======= RAG AGENT ======")
    while True:
        user_input = input("\nQuestion: ")
        if user_input.lower() in ["exit", "quit"]:
            break
        messages = [HumanMessage(content=user_input)]
        result = agent.invoke({"messages": messages})
        print("\n==== ANSWER =====")
        print(result["messages"][-1].content)

if __name__ == "__main__":
    run_rag_agent_cli()
