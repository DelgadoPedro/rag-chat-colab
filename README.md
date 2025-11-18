# Sistema de Discussão Acadêmica

Trabalho desenvolvido para a disciplina: SSC0723 - Sistemas Colaborativos: Fundamentos e Aplicações (2025)

Alunos:
Artur De Vlieger Lima - 13671574
João Pedro Mori Machado - 13671831
Lucas Issao Omati - 13673090
Pedro Augusto Monteiro Delgado - 13672766
Rebeca Vieira Carvalho - 12543530

## Descrição do Cenário Escolhido

Para o desenvolvimento da nossa aplicação, o cenário imaginado foi criar um Sistema de Discussão para auxiliar grupos de estudo focados em um tópico específico. Nosso sistema tem a premissa de ser um ambiente de chat no qual os membros podem conversar e compartilhar documentos sobre o assunto escolhido. Nesse contexto, atua o *colaborai*, um agente LLM com RAG que acompanha ativamente a conversa do grupo, auxiliando os membros na discussão e no aprendizado do tópico. A seguir, detalharemos as ferramentas e funcionalidades que ele oferece.

### Funcionalidades

### 1. **Chat Colaborativo Multi-Usuário**
5 participantes pré-configurados: Artur, Pedro, João, Rebeca e Lucas. Mensagens atribuídas a cada participante e histórico persistente compartilhado entre todos

### 2. **Sistema RAG (Retrieval Augmented Generation)**
Upload de múltiplos PDFs (1 a 5), com indexação automática com embeddings locais e busca semântica no conteúdo dos artigos

### 3. **Assistente IA com 3 Ferramentas Especializadas**

**retriever_tool**: Realiza busca semântica no conteúdo dos artigos e retorna trechos relevantes com citações

**conversation_history_tool**: Acessa histórico recente da conversa e possibilita entendimento do contexto das discussões

**fixation_exercise_tool**: Gera exercícios de fixação para cada participante, baseados no conteúdo dos artigos e na discussão do grupo

### 4. **Invocação do Assistente**
Use `@colaborai` em qualquer mensagem para chamar o assistente, que realiza o processamento automático com acesso às ferramentas

## Diagramas

### Grafo de funcionalidades

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

### Diagrama de decisão

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

### Arquitetura do Sistema

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

## 3Cs

Confira a análise dos 3C (Comunicação, Colaboração e Coordenação) [aqui](cenario_colaborativo_3c.md).

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


