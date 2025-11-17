# Chat Colaborativo RAG - Sistema de Discussão Acadêmica

Sistema de chat colaborativo para discussão de artigos científicos com assistente inteligente baseado em RAG (Retrieval Augmented Generation).

## 📋 Descrição

Este projeto foi desenvolvido para um trabalho de faculdade sobre **Sistemas Colaborativos**. Simula um ambiente de chat onde estudantes podem discutir sobre 1 a 5 artigos acadêmicos em PDF, com suporte de um assistente IA que acessa o conteúdo dos documentos para responder perguntas e gerar exercícios de fixação.

## 🎯 Funcionalidades

### 1. **Chat Colaborativo Multi-Usuário**
- 5 participantes pré-configurados: Artur, Pedro, João, Rebeca e Lucas
- Mensagens atribuídas a cada participante
- Histórico persistente compartilhado entre todos

### 2. **Sistema RAG (Retrieval Augmented Generation)**
- Upload de múltiplos PDFs (1-5 artigos científicos)
- Indexação automática com embeddings locais
- Busca semântica inteligente no conteúdo dos artigos
- Citações automáticas (fonte + página)

### 3. **Assistente IA com 3 Ferramentas Especializadas**

#### 🔍 **retriever_tool**
- Busca semântica no conteúdo dos artigos
- Suporte a filtros por documento específico
- Retorna trechos relevantes com citações

#### 📜 **conversation_history_tool**
- Acessa histórico recente da conversa
- Entende contexto das discussões
- Identifica participantes ativos

#### 📝 **fixation_exercise_tool**
- Gera exercícios de fixação personalizados
- Baseado no conteúdo dos artigos E na discussão do grupo
- Cria 2-3 questões por participante
- Inclui gabarito completo com explicações
- Varia tipos de questões: compreensão, análise, aplicação, síntese

### 4. **Invocação do Assistente**
- Use `@colaborai` em qualquer mensagem para chamar o assistente
- Processamento automático com acesso às ferramentas
- Respostas contextualizadas e citadas

## 🚀 Como Usar

### Pré-requisitos

- Python 3.11 ou superior
- Chave de API do OpenRouter (gratuita para alguns modelos)

### Instalação

1. Clone o repositório:
```bash
git clone <url-do-repositorio>
cd rag-chat-colab
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Configure a chave da API:

Crie um arquivo `.env` na raiz do projeto:
```env
OPENROUTER_API_KEY=sua_chave_aqui
```

Obtenha sua chave gratuita em: https://openrouter.ai/keys

### Executando a Aplicação

```bash
streamlit run app.py
```

A aplicação será aberta automaticamente no navegador em `http://localhost:8501`

## 📖 Guia de Uso

### 1. Upload de Artigos

1. Na barra lateral, clique em "Enviar PDF(s)"
2. Selecione 1 a 5 artigos científicos em PDF
3. Clique em "Construir/Atualizar índice"
4. Aguarde a indexação (pode levar alguns minutos)

### 2. Iniciar o Agente

1. Na barra lateral, clique em "Criar/Recriar agente"
2. O assistente estará pronto para uso

### 3. Participar da Discussão

1. Selecione seu nome no dropdown "Quem está falando agora?"
2. Digite sua mensagem no chat
3. Para chamar o assistente, inclua `@colaborai` na mensagem

### 4. Exemplos de Uso

**Pergunta sobre conteúdo:**
```
@colaborai Qual é a metodologia utilizada no artigo sobre machine learning?
```

**Busca em artigo específico:**
```
@colaborai source: artigo1.pdf quais foram os principais resultados?
```

**Gerar exercícios:**
```
@colaborai Crie exercícios de fixação sobre os conceitos discutidos
```

**Exercícios sobre tópico específico:**
```
@colaborai Gere exercícios focando na metodologia dos artigos
```

## 🏗️ Arquitetura

### Componentes Principais

```
rag-chat-colab/
├── app.py                  # Interface Streamlit
├── agent_rag.py            # Motor RAG com ferramentas
├── agent.py                # Agente simples (teste)
├── requirements.txt        # Dependências
├── .env                    # Configurações (não versionado)
└── vdb/                    # Banco vetorial e histórico
    ├── chroma.sqlite3      # ChromaDB
    ├── conversation_history.txt  # Histórico
    └── indexed_files.txt   # Registro de arquivos
```

### Tecnologias Utilizadas

- **LangChain**: Framework para aplicações LLM
- **LangGraph**: Orquestração de agentes com grafos
- **ChromaDB**: Banco de dados vetorial
- **Sentence Transformers**: Embeddings locais (all-MiniLM-L6-v2)
- **Streamlit**: Interface web
- **OpenRouter**: Gateway para LLMs (Nvidia Nemotron gratuito)
- **PyPDF**: Processamento de PDFs

### Fluxo de Dados

1. **Upload** → PDFs são divididos em chunks de 1000 caracteres
2. **Embedding** → Chunks são vetorizados localmente
3. **Indexação** → Vetores armazenados no ChromaDB
4. **Discussão** → Mensagens salvas em histórico compartilhado
5. **Invocação** → `@colaborai` ativa o agente
6. **Processamento** → Agente decide quais ferramentas usar
7. **Resposta** → Resposta contextualizada com citações

## 🔧 Configurações Avançadas

### Variáveis de Ambiente (opcionais)

```env
# Diretório do banco vetorial
RAG_VDB_DIR=./vdb

# Arquivo de histórico
RAG_HISTORY_FILE=./vdb/conversation_history.txt
```

### Personalização do LLM

Edite `agent_rag.py` para usar outro modelo:

```python
def build_llm(model: str = "seu-modelo-aqui", temperature: float = 0):
    llm = ChatOpenAI(
        model=model,
        api_key=os.environ.get("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
        temperature=temperature
    )
    return llm
```

### Ajustar Número de Resultados

Em `app.py`, linha 187:
```python
retriever.search_kwargs["k"] = 5  # Altere para mais ou menos resultados
```

## 📊 Trabalho Acadêmico

### Tema: Sistemas Colaborativos

Este projeto demonstra conceitos de:
- **Colaboração assíncrona**: Múltiplos usuários, histórico compartilhado
- **Inteligência coletiva**: Discussões enriquecidas por IA
- **Gestão do conhecimento**: Indexação e recuperação de informações
- **Ferramentas colaborativas**: Chat, assistente virtual, geração de exercícios

### Cenário de Uso

Grupo de estudantes prepara-se para uma avaliação:
1. Fazem upload dos artigos obrigatórios da disciplina
2. Discutem conceitos principais no chat
3. Tiram dúvidas com o assistente `@colaborai`
4. Geram exercícios de fixação automaticamente
5. Praticam com as questões personalizadas

## 🐛 Troubleshooting

### Erro: "Crie o índice antes de iniciar o agente"
**Solução**: Faça upload de PDFs e clique em "Construir/Atualizar índice"

### Erro: "OpenRouter API key not found"
**Solução**: Configure a variável `OPENROUTER_API_KEY` no arquivo `.env`

### ChromaDB não inicializa
**Solução**: Delete a pasta `vdb/` e reconstrua o índice

### Streamlit não abre no navegador
**Solução**: Acesse manualmente `http://localhost:8501`

## 📝 Notas de Desenvolvimento

### Melhorias Implementadas nas Tools

#### retriever_tool
- Busca semântica com fuzzy matching
- Filtros por fonte específica
- Citações automáticas formatadas

#### conversation_history_tool
- Limite configurável de mensagens
- Formato estruturado: `role::user::content`
- Suporte a contexto conversacional

#### fixation_exercise_tool (versão melhorada)
- **Estratégia tripla de busca**: tópico + discussão + conceitos gerais
- **Extração inteligente de keywords**: análise de frequência
- **Diversidade de fontes**: prioriza diferentes artigos
- **Personalização**: considera participação individual
- **Instruções detalhadas**: 5 tipos de questões + formato estruturado
- **Gabarito completo**: respostas educativas com citações

## 👥 Participantes do Projeto

- Sistema desenvolvido para trabalho acadêmico
- Simulação de 5 estudantes colaborando

## 📄 Licença

Projeto acadêmico - uso educacional

## 🔗 Links Úteis

- [OpenRouter](https://openrouter.ai/) - API Gateway para LLMs
- [LangChain Docs](https://python.langchain.com/) - Documentação do framework
- [Streamlit Docs](https://docs.streamlit.io/) - Documentação da interface
- [ChromaDB](https://www.trychroma.com/) - Banco vetorial

---

**Desenvolvido para a disciplina de Sistemas Colaborativos** 🎓
