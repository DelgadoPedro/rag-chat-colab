import os
import time
import uuid
import tempfile
import streamlit as st
from dotenv import load_dotenv

from agent_rag import (
    build_llm,
    build_embeddings,
    build_vectorstore_from_pages,
    build_retriever,
    build_agent,
    load_pdf_pages,
    load_vectorstore_from_persist,
)

USERS = ["Artur", "Pedro", "João", "Rebeca", "Lucas"]

def get_shared_vectorstore_dir() -> str:
    base = os.environ.get("RAG_VDB_DIR", "./vdb")
    if not os.path.exists(base):
        os.makedirs(base)
    return base


def ensure_session_state():
    """Initialize all session variables"""
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if "messages" not in st.session_state:
        st.session_state.messages = []  # list of {role: "user"|"assistant"|"system", content: str}
    if "agent" not in st.session_state:
        st.session_state.agent = None
    if "retriever" not in st.session_state:
        st.session_state.retriever = None
    if "selected_user" not in st.session_state:
        st.session_state.selected_user = USERS[0]


def get_history_file_path() -> str:
    return os.path.join(get_shared_vectorstore_dir(), "conversation_history.txt")


def get_index_registry_path() -> str:
    return os.path.join(get_shared_vectorstore_dir(), "indexed_files.txt")


def read_indexed_files() -> list:
    path = get_index_registry_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            lines = [l.strip() for l in fh.read().splitlines() if l.strip()]
        return lines
    except Exception:
        return []


def add_indexed_file(filename: str):
    path = get_index_registry_path()
    files = set(read_indexed_files())
    if filename in files:
        return
    try:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(f"{filename}\n")
    except Exception:
        pass


def append_history_to_file(message: dict):
    path = get_history_file_path()
    try:
        role = message.get("role", "")
        user = message.get("user", "")
        content = message.get("content", "").replace("\n", " ")
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(f"{role}::{user}::{content}\n")
    except Exception as e:
        st.error(f"Failed to write history: {e}")

def build_or_update_index_from_uploads(uploaded_files):
    """Build or update the vectorstore from a list of uploaded files.

    `uploaded_files` is expected to be a list of Streamlit UploadedFile objects.
    The function writes each upload to a temp file, loads pages using the original
    filename as `source_name` (so metadata keeps the real filename), indexes all
    pages together, and registers the filenames in `indexed_files.txt`.
    """
    temp_paths = []
    all_pages = []

    # Normalize single-file case
    if uploaded_files is None:
        return None
    if not isinstance(uploaded_files, (list, tuple)):
        uploaded_files = [uploaded_files]

    try:
        for f in uploaded_files:
            # `f` can be a Streamlit UploadedFile-like object with .read() and .name
            filename = getattr(f, "name", None)
            content = f.read() if hasattr(f, "read") else f
            suffix = os.path.splitext(filename or "")[1] or ".pdf"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(content)
                tmp_path = tmp.name
            temp_paths.append(tmp_path)
            # load pages with correct source name and extend
            all_pages.extend(load_pdf_pages(tmp_path, source_name=filename))
            # register the indexed filename so the UI can show it
            if filename:
                add_indexed_file(filename)

        embeddings = build_embeddings()
        vectorstore = build_vectorstore_from_pages(
            all_pages,
            embeddings,
            persist_directory=get_shared_vectorstore_dir(),
            collection_name="book",
        )
        retriever = build_retriever(vectorstore)
        return retriever
    finally:
        # cleanup temp files
        for p in temp_paths:
            try:
                if os.path.exists(p):
                    os.unlink(p)
            except Exception:
                pass


def main():
    load_dotenv()
    st.set_page_config(page_title="Chat Colaborativo RAG", page_icon="📄")
    ensure_session_state()

    # Auto-connect to an existing persisted vectorstore if present
    shared_dir = get_shared_vectorstore_dir()
    try:
        if st.session_state.retriever is None and os.path.exists(shared_dir) and os.listdir(shared_dir):
            with st.spinner("Conectando ao índice existente..."):
                embeddings = build_embeddings()
                vectorstore = load_vectorstore_from_persist(persist_directory=shared_dir, collection_name="book", embeddings=embeddings)
                st.session_state.retriever = build_retriever(vectorstore)
            st.success("Índice compartilhado encontrado.")
    except Exception as e:
        error_msg = str(e)
        if "meta tensor" in error_msg.lower() or "Cannot copy out of meta" in error_msg:
            st.warning(
                f"⚠️ Erro ao carregar modelo de embeddings: {error_msg}\n\n"
                "**Solução:** Tente fazer upload dos PDFs novamente para reconstruir o índice. "
                "O problema pode estar relacionado ao cache do modelo."
            )
        else:
            st.warning(f"Não foi possível conectar ao índice existente: {e}")

    st.title("📄 Chat Colaborativo RAG")
    st.caption("Faça upload de até 5 artigos em PDF, discuta com o grupo e chame o agente quando precisar.")

    with st.sidebar:

        st.header("Participante ativo")
        st.session_state.selected_user = st.selectbox("Quem está falando agora?", USERS, index=USERS.index(st.session_state.selected_user))
        st.caption("As mensagens serão atribuídas ao participante selecionado.")

        st.header("Arquivos")
        uploaded_files = st.file_uploader("Enviar PDF(s)", type=["pdf"], accept_multiple_files=True, help="Carregue 1 a 5 artigos científicos.")
        if uploaded_files:
            if st.button("Construir/Atualizar índice", type="primary"):
                with st.spinner("Gerando índice compartilhado..."):
                    st.session_state.retriever = build_or_update_index_from_uploads(uploaded_files)
                st.success("Índice criado a partir dos arquivos enviados.")
        
        st.divider()
        # Show indexed files found in the shared vectorstore directory
        st.header("Arquivos indexados")
        indexed = read_indexed_files()
        if indexed:
            for fname in indexed:
                st.markdown(f"- `{fname}`")
        else:
            st.markdown("_Nenhum arquivo indexado ainda._")

        st.header("Agente")
        if st.button("Criar/Recriar agente"):
            if st.session_state.retriever is None:
                st.warning("Crie o índice antes de iniciar o agente.")
            else:
                llm = build_llm(temperature=0)
                retriever = st.session_state.retriever
                retriever.search_kwargs["k"] = 5
                history_file = get_history_file_path()
                st.session_state.agent = build_agent(retriever, llm, history_file=history_file)
                st.success("Agente pronto para colaborar.")

    # Chat area
    st.subheader("Espaço de discussão. Para chamar o agente, escreva @colaborai na mensagem.")
    for msg in st.session_state.messages:
        author = msg.get("user", "Participante") if msg["role"] == "user" else "Assistente"
        with st.chat_message("user" if msg["role"] == "user" else "assistant"):
            st.markdown(f"**{author}**: {msg['content']}")

    if prompt := st.chat_input(f"{st.session_state.selected_user} diz: "):
        user_msg = {"user": st.session_state.selected_user, "role": "user", "content": prompt}
        st.session_state.messages.append(user_msg)
        append_history_to_file(user_msg)
        with st.chat_message("user"):
            st.markdown(f"**{st.session_state.selected_user}**: {prompt}")
        if "@colaborai" in prompt.lower():
            if st.session_state.agent is None:
                with st.chat_message("assistant"):
                    st.warning("Crie o agente na barra lateral antes de fazer perguntas.")
            else:
                with st.chat_message("assistant"):
                    with st.spinner("Pensando..."):
                        result = st.session_state.agent.invoke({
                            "messages": [
                                {"type": "human", "content": prompt.replace("@colaborai", "").strip()}
                            ]
                        })
                        content = result["messages"][-1].content
                        st.markdown(content)
                        assistant_msg = {"role": "assistant", "content": content}
                        st.session_state.messages.append(assistant_msg)
                        append_history_to_file(assistant_msg)


if __name__ == "__main__":
    main()
