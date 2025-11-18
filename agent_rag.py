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
        """Search and retrieve relevant content from the indexed academic articles using semantic similarity.

        This tool performs vector-based semantic search across all indexed PDF documents,
        returning the most relevant text chunks with proper citations. It's the primary way
        to access specific information from the uploaded articles.
        
        Query formats supported:
        
        1. Simple semantic search (default):
           - "metodologia de análise de dados"
           - "principais resultados do estudo"
           - "limitações da pesquisa"
        
        2. Filtered search by specific article:
           - "source: artigo1.pdf conceitos fundamentais"
           - "from artigo2.pdf metodologia experimental"
           - Supports fuzzy matching (e.g., "artigo1" matches "artigo1.pdf")
        
        Features:
        - Returns up to K most relevant chunks (default: 7)
        - Each result includes: document number, source filename, page number, and content
        - Automatic citation formatting: (source: filename, page: N)
        - Fuzzy matching for article names (60% similarity threshold)
        - Lists available sources if requested article is not found
        
        Return format:
        Document 1 (source: article.pdf, page: 5):
        [relevant text chunk]
        
        Document 2 (source: article.pdf, page: 7):
        [relevant text chunk]
        
        Use cases:
        - Answer specific questions about article content
        - Find definitions, methodologies, or results
        - Compare information across different articles
        - Verify claims with citations from the source material
        - Extract data, figures, or conclusions mentioned in articles
        
        Note: Returns "No relevant info was found in the document" if no matches exist.
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
        """Retrieve recent messages from the collaborative chat to understand the conversation context.

        This tool accesses the persistent conversation history shared by all participants,
        allowing the assistant to understand what has been discussed, who participated,
        and what topics were covered in previous messages.
        
        The query parameter can be:
        - A number (e.g., "10", "15") to specify how many recent messages to retrieve
        - A general request (e.g., "últimas mensagens", "histórico recente")
        - Left as default to retrieve the last 20 messages
        
        Limitations:
        - Maximum of 20 messages can be retrieved per call
        - Minimum of 0 messages (returns empty if history doesn't exist)
        
        Each message in the history follows the format:
        role::username::message_content
        
        Where:
        - role: "user" (participant message) or "assistant" (AI response)
        - username: name of the participant who sent the message
        - message_content: the actual message text
        
        Use this tool when you need to:
        - Understand the conversation flow before answering
        - Reference what participants have previously discussed
        - Identify who has been actively participating
        - Provide contextual responses based on prior messages
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
        """Generate personalized fixation exercises for each active participant based on the articles and conversation context.

        This tool automatically analyzes the conversation history to understand what topics were discussed,
        identifies all participants, and retrieves relevant content from the indexed articles to create
        meaningful exercises.
        
        The query parameter is optional and can be used to:
        - Specify a focus area (e.g., "metodologia", "resultados do capítulo 2")
        - Provide general instructions (e.g., "exercícios sobre os conceitos principais")
        - Be left generic (e.g., "criar exercícios") - the tool will infer topics from conversation context
        
        The tool will:
        1. Extract participants from conversation history
        2. Analyze recent discussion topics and keywords
        3. Retrieve relevant chunks from multiple articles using advanced search strategies
        4. Generate 1 exercise per participant with appropriate difficulty
        
        Returns a structured JSON payload with instructions, reference chunks, and context for the LLM
        to generate high-quality, contextualized exercises.
        """
        topic = query.strip() if query and query.strip() else "panorama geral dos artigos"
        participants = get_participants_from_history()
        if not participants:
            participants = ["Grupo"]

        # Ler histórico do chat com mais contexto
        conversation_history = ""
        discussion_topics = []
        if os.path.exists(history_path):
            try:
                with open(history_path, "r", encoding="utf-8") as fh:
                    lines = fh.read().splitlines()
                # Pegar últimas 50 mensagens para melhor contexto
                recent_lines = lines[-50:] if len(lines) > 50 else lines
                conversation_history = "\n".join(recent_lines) if recent_lines else ""
                
                # Extrair tópicos discutidos (mensagens de usuários)
                for line in recent_lines:
                    parts = line.split("::", 2)
                    if len(parts) >= 3 and parts[0].strip().lower() == "user":
                        discussion_topics.append(parts[2].strip())
            except Exception as e:
                conversation_history = f"Erro ao ler histórico: {e}"

        # Buscar trechos relevantes dos artigos com estratégia melhorada
        reference_chunks = []
        sources_covered = set()
        
        try:
            # Estratégia 1: Busca baseada no tópico principal
            search_query = topic
            if conversation_history:
                # Extrair palavras-chave do histórico de forma mais inteligente
                words = conversation_history.lower().split()
                stopwords = {
                    "o", "a", "os", "as", "de", "da", "do", "das", "dos", "em", "no", "na", 
                    "que", "para", "com", "é", "um", "uma", "e", "ou", "se", "não", "ser", 
                    "ter", "fazer", "dizer", "colaborai", "@colaborai", "user", "assistant",
                    "sobre", "mais", "como", "mas", "por", "ao", "aos", "sua", "seu", "isso",
                    "esse", "essa", "então", "já", "também", "onde", "quando", "qual"
                }
                
                # Contar frequência de palavras relevantes
                word_freq = {}
                for w in words:
                    if len(w) > 4 and w not in stopwords and w.isalpha():
                        word_freq[w] = word_freq.get(w, 0) + 1
                
                # Pegar top 8 palavras mais frequentes
                top_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:8]
                if top_keywords:
                    extra_keywords = " ".join([kw[0] for kw in top_keywords])
                    search_query = f"{topic} {extra_keywords}".strip()
            
            # Busca principal
            docs_main = retriever.invoke(search_query) if search_query else []
            
            # Estratégia 2: Busca complementar com termos da discussão
            docs_discussion = []
            if discussion_topics and len(discussion_topics) > 0:
                # Usar últimas 3 mensagens de usuários para busca contextual
                recent_discussion = " ".join(discussion_topics[-3:])
                if recent_discussion.strip():
                    docs_discussion = retriever.invoke(recent_discussion[:200])
            
            # Estratégia 3: Busca genérica para conceitos fundamentais
            docs_general = retriever.invoke("principais conceitos metodologia resultados conclusões")
            
            # Combinar e diversificar resultados
            all_docs = []
            # Priorizar docs da busca principal
            for doc in docs_main[:10]:
                if doc not in all_docs:
                    all_docs.append(doc)
            # Adicionar docs da discussão
            for doc in docs_discussion[:5]:
                if doc not in all_docs:
                    all_docs.append(doc)
            # Adicionar docs gerais
            for doc in docs_general[:5]:
                if doc not in all_docs:
                    all_docs.append(doc)
                    
        except Exception as e:
            all_docs = []
            reference_chunks.append({
                "source": "erro", 
                "page": "-", 
                "excerpt": f"Falha ao consultar repositório: {e}"
            })

        # Processar documentos recuperados, garantindo diversidade de fontes
        for doc in all_docs[:12]:  # Aumentar para 12 trechos
            meta = getattr(doc, "metadata", {}) or {}
            source = meta.get("source_file", meta.get("source", "desconhecido"))
            page_no = meta.get("page_number", meta.get("page", "?"))
            snippet = (doc.page_content or "").strip()
            
            if not snippet:
                continue
                
            # Preferir diversidade de fontes
            snippet_preview = snippet[:600] + ("..." if len(snippet) > 600 else "")
            reference_chunks.append({
                "source": source,
                "page": page_no,
                "excerpt": snippet_preview,
            })
            sources_covered.add(source)

        # Resumo dos tópicos discutidos
        topics_summary = ""
        if discussion_topics:
            # Pegar últimas 5 mensagens significativas
            significant_topics = [t for t in discussion_topics[-10:] if len(t) > 20][-5:]
            if significant_topics:
                topics_summary = "\n".join([f"- {t[:150]}" for t in significant_topics])

        payload = {
            "topic": topic,
            "participants": participants,
            "num_participants": len(participants),
            "conversation_history": conversation_history if conversation_history else "Nenhum histórico de conversa disponível.",
            "recent_topics_discussed": topics_summary if topics_summary else "Nenhum tópico específico identificado.",
            "sources_available": list(sources_covered) if sources_covered else ["Nenhuma fonte identificada"],
            "instructions": (
                "Você deve criar exercícios de fixação PERSONALIZADOS E BEM ESTRUTURADOS para cada participante.\n\n"
                "## DIRETRIZES OBRIGATÓRIAS:\n\n"
                "### 1. QUALIDADE DAS QUESTÕES\n"
                "- Crie 2-3 exercícios por participante (não mais que isso)\n"
                "- FOQUE em conceitos-chave, metodologias, resultados e implicações dos artigos\n"
                "- EVITE perguntas triviais (ex: 'Qual o título do artigo?')\n"
                "- EVITE perguntas impossíveis de responder com o conteúdo fornecido\n"
                "- Dificuldade MEDIANA: requer compreensão, não apenas memorização\n\n"
                "### 2. TIPOS DE QUESTÕES (varie entre estes):\n"
                "- **Compreensão**: Explicar conceitos apresentados nos artigos\n"
                "- **Comparação**: Relacionar ideias de diferentes artigos ou seções\n"
                "- **Aplicação**: Como aplicar os conceitos em situações práticas\n"
                "- **Análise crítica**: Avaliar metodologias, limitações ou implicações\n"
                "- **Síntese**: Integrar múltiplas ideias dos artigos\n\n"
                "### 3. CONTEXTUALIZAÇÃO\n"
                "- USE os tópicos recentemente discutidos para criar questões relevantes\n"
                "- REFERENCIE explicitamente os artigos (nome e página) nas questões\n"
                "- CONECTE as questões com o que foi conversado no chat\n\n"
                "### 4. DIVERSIDADE\n"
                "- Distribua questões entre diferentes artigos quando possível\n"
                "- Varie os tipos de questões para cada participante\n"
                "- Personalize levemente para cada pessoa (baseado em suas mensagens anteriores, se houver)\n\n"
                "## FORMATO DE SAÍDA OBRIGATÓRIO:\n\n"
                "### EXERCÍCIOS DE FIXAÇÃO\n"
                "**Tópico:** [tópico]\n\n"
                "#### Exercícios para [Nome do Participante 1]\n"
                "1. [Questão 1]\n"
                "2. [Questão 2]\n"
                "[Repetir para cada participante]\n\n"
            ),
            "reference_chunks": reference_chunks if reference_chunks else [
                {"source": "N/A", "page": "-", "excerpt": "Nenhum trecho disponível dos artigos."}
            ],
            "metadata": {
                "total_chunks": len(reference_chunks),
                "sources_count": len(sources_covered),
                "conversation_messages": len(conversation_history.splitlines()) if conversation_history else 0,
            }
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

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
