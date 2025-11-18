# Sistema de Discussão Acadêmica

Sistema de chat colaborativo para discussão de artigos científicos com assistente inteligente baseado em RAG (Retrieval Augmented Generation). Este projeto foi desenvolvido para a disciplina SSC0723 - Sistemas Colaborativos: Fundamentos e Aplicações (2025). 

## Funcionalidades

### 1. **Chat Colaborativo Multi-Usuário**
- 5 participantes pré-configurados: Artur, Pedro, João, Rebeca e Lucas
- Mensagens atribuídas a cada participante
- Histórico persistente compartilhado entre todos

### 2. **Sistema RAG (Retrieval Augmented Generation)**
- Upload de múltiplos PDFs (1-5 artigos científicos)
- Indexação automática com embeddings locais
- Busca semântica inteligente no conteúdo dos artigos

### 3. **Assistente IA com 3 Ferramentas Especializadas**

#### **retriever_tool**
- Busca semântica no conteúdo dos artigos
- Suporte a filtros por documento específico
- Retorna trechos relevantes com citações

#### **conversation_history_tool**
- Acessa histórico recente da conversa
- Entende contexto das discussões
- Identifica participantes ativos

#### **fixation_exercise_tool**
- Gera exercícios de fixação personalizados
- Baseado no conteúdo dos artigos E na discussão do grupo
- Cria 2-3 questões por participante
- Inclui gabarito completo com explicações
- Varia tipos de questões: compreensão, análise, aplicação, síntese

### 4. **Invocação do Assistente**
- Use `@colaborai` em qualquer mensagem para chamar o assistente
- Processamento automático com acesso às ferramentas
- Respostas contextualizadas e citadas

## Como Usar

### Pré-requisitos

- Python 3.11 ou superior
- Chave de API do OpenRouter

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

## Guia de Uso

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

## Arquitetura

# Diagrama Mermaid do Grafo LangGraph

## 📊 Grafo Interativo (Mermaid)

```mermaid
graph TD
    START([Início]) --> LLM[llm_processor<br/>Processador LLM Principal]
    
    LLM -->|Decisão: retriever_tool| RET[retriever_executor<br/>🔍 Busca Semântica]
    LLM -->|Decisão: conversation_history_tool| HIST[history_executor<br/>📜 Histórico de Conversa]
    LLM -->|Decisão: fixation_exercise_tool| EXE[exercise_executor<br/>📝 Geração de Exercícios]
    LLM -->|Sem tool calls| END([END<br/>Resposta Final])
    
    RET -->|Retorna resultados| LLM
    HIST -->|Retorna histórico| LLM
    EXE -->|Retorna payload JSON| LLM
    
    style LLM fill:#4A90E2,stroke:#2E5C8A,stroke-width:3px,color:#fff
    style RET fill:#50C878,stroke:#2E7D4E,stroke-width:2px,color:#fff
    style HIST fill:#FF6B6B,stroke:#C44D4D,stroke-width:2px,color:#fff
    style EXE fill:#FFA500,stroke:#CC8500,stroke-width:2px,color:#fff
    style START fill:#9B59B6,stroke:#6C3483,stroke-width:2px,color:#fff
    style END fill:#E74C3C,stroke:#C0392B,stroke-width:2px,color:#fff
```

## 🔄 Fluxo Detalhado com Estados

```mermaid
stateDiagram-v2
    [*] --> llm_processor: Mensagem do usuário
    
    llm_processor --> retriever_executor: Tool: retriever_tool
    llm_processor --> history_executor: Tool: conversation_history_tool
    llm_processor --> exercise_executor: Tool: fixation_exercise_tool
    llm_processor --> [*]: Sem tool calls (resposta final)
    
    retriever_executor --> llm_processor: Resultados da busca
    history_executor --> llm_processor: Histórico formatado
    exercise_executor --> llm_processor: Payload JSON
    
    note right of llm_processor
        • Processa mensagens
        • Adiciona contexto histórico
        • Invoca LLM com tools
        • Decide roteamento
    end note
    
    note right of retriever_executor
        • Busca semântica nos PDFs
        • Filtra por documento
        • Formata com citações
    end note
    
    note right of exercise_executor
        • Lê histórico
        • Busca trechos relevantes
        • Gera payload estruturado
    end note
```

## 📋 Sequência de Execução

```mermaid
sequenceDiagram
    participant U as Usuário
    participant LP as llm_processor
    participant RE as retriever_executor
    participant HE as history_executor
    participant EE as exercise_executor
    
    U->>LP: "@colaborai Qual é a metodologia?"
    LP->>LP: Adiciona contexto histórico
    LP->>LP: Invoca LLM com tools
    LP->>LP: LLM decide usar retriever_tool
    
    LP->>RE: Tool call: retriever_tool
    RE->>RE: Busca semântica nos PDFs
    RE->>RE: Formata resultados com citações
    RE->>LP: ToolMessage com trechos
    
    LP->>LP: Processa resultados
    LP->>LP: Gera resposta contextualizada
    LP->>U: Resposta final com citações
```

## 🎯 Caso de Uso: Geração de Exercícios

```mermaid
sequenceDiagram
    participant U as Usuário
    participant LP as llm_processor
    participant EE as exercise_executor
    participant HE as conversation_history_tool
    participant RE as retriever_tool
    
    U->>LP: "@colaborai Crie exercícios"
    LP->>LP: LLM decide usar fixation_exercise_tool
    LP->>EE: Tool call: fixation_exercise_tool
    
    EE->>HE: Lê histórico de conversa
    HE-->>EE: Histórico formatado
    
    EE->>RE: Busca trechos relevantes
    RE-->>EE: Trechos dos artigos
    
    EE->>EE: Identifica participantes
    EE->>EE: Extrai tópicos discutidos
    EE->>EE: Gera payload JSON estruturado
    EE->>LP: ToolMessage com payload
    
    LP->>LP: Processa payload
    LP->>LP: Gera exercícios formatados
    LP->>U: Exercícios personalizados + gabarito
```

## 🔀 Diagrama de Decisão

```mermaid
flowchart TD
    A[Mensagem do Usuário] --> B[llm_processor]
    B --> C{LLM analisa e decide}
    
    C -->|Precisa buscar conteúdo| D[retriever_executor]
    C -->|Precisa contexto histórico| E[history_executor]
    C -->|Precisa gerar exercícios| F[exercise_executor]
    C -->|Resposta direta| G[END]
    
    D --> H[Busca nos PDFs]
    H --> I[Formata com citações]
    I --> B
    
    E --> J[Lê conversation_history.txt]
    J --> K[Formata histórico]
    K --> B
    
    F --> L[Lê histórico]
    L --> M[Busca trechos relevantes]
    M --> N[Gera payload JSON]
    N --> B
    
    B --> O{Precisa mais tools?}
    O -->|Sim| C
    O -->|Não| G
    
    style B fill:#4A90E2,stroke:#2E5C8A,stroke-width:3px,color:#fff
    style D fill:#50C878,stroke:#2E7D4E,stroke-width:2px,color:#fff
    style E fill:#FF6B6B,stroke:#C44D4D,stroke-width:2px,color:#fff
    style F fill:#FFA500,stroke:#CC8500,stroke-width:2px,color:#fff
    style G fill:#E74C3C,stroke:#C0392B,stroke-width:2px,color:#fff
```

## 📊 Arquitetura do Sistema

```mermaid
graph LR
    subgraph "Interface Streamlit"
        UI[app.py<br/>Interface Web]
    end
    
    subgraph "Agente LangGraph"
        LP[llm_processor]
        RE[retriever_executor]
        HE[history_executor]
        EE[exercise_executor]
    end
    
    subgraph "Ferramentas"
        RT[retriever_tool]
        HT[conversation_history_tool]
        ET[fixation_exercise_tool]
    end
    
    subgraph "Armazenamento"
        VS[ChromaDB<br/>Vector Store]
        HF[conversation_history.txt]
    end
    
    UI -->|"@colaborai"| LP
    LP --> RE
    LP --> HE
    LP --> EE
    
    RE --> RT
    HE --> HT
    EE --> ET
    
    RT --> VS
    HT --> HF
    ET --> VS
    ET --> HF
    
    LP -->|Resposta| UI
    
    style LP fill:#4A90E2,stroke:#2E5C8A,stroke-width:3px,color:#fff
    style VS fill:#50C878,stroke:#2E7D4E,stroke-width:2px,color:#fff
    style HF fill:#FF6B6B,stroke:#C44D4D,stroke-width:2px,color:#fff
```

## 🎨 Legenda

- 🔵 **Azul**: Nó principal (llm_processor)
- 🟢 **Verde**: Executor de busca (retriever)
- 🔴 **Vermelho**: Executor de histórico (history)
- 🟠 **Laranja**: Executor de exercícios (exercise)
- 🟣 **Roxo**: Ponto de entrada
- ⚫ **Preto**: Ponto de saída (END)

---

**Nota**: Estes diagramas Mermaid podem ser renderizados em:
- GitHub/GitLab (Markdown)
- VS Code (com extensão Mermaid)
- Obsidian
- Notion
- Muitos outros editores Markdown modernos


## Cenário de Uso

Grupo de estudantes prepara-se para uma avaliação:
1. Fazem upload dos artigos obrigatórios da disciplina
2. Discutem conceitos principais no chat
3. Tiram dúvidas com o assistente `@colaborai`
4. Geram exercícios de fixação automaticamente
5. Praticam com as questões personalizadas

inserir vídeo
