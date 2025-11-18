# Cenário Colaborativo e Abordagem dos 3C

## Contexto

O sistema foi desenvolvido para um cenário acadêmico de estudo colaborativo, onde um grupo de estudantes trabalha em conjunto para preparar-se para uma avaliação sobre um tema específico (ex: MLOps, Machine Learning, Sistemas Distribuídos, etc.). O sistema simula um ambiente de **5 participantes** pré-configurados:

### Fluxo de Trabalho Colaborativo

1. **Preparação Inicial**
   - O grupo faz upload de 1 a 5 artigos científicos em PDF relacionados ao tema de estudo
   - O sistema indexa automaticamente os documentos em um banco vetorial compartilhado

2. **Discussão Colaborativa**
   - Cada participante pode enviar mensagens no chat, identificando-se através de um seletor
   - As mensagens são atribuídas ao participante ativo e salvas em um histórico compartilhado

3. **Assistência Inteligente**
   - Quando necessário, qualquer participante pode chamar o assistente `@colaborai`
   - O assistente acessa o conteúdo dos artigos indexados para responder perguntas

4. **Geração de Exercícios**
   - O sistema gera questões personalizadas para cada participante, após solicitação
   - Os exercícios são baseados tanto no conteúdo dos artigos quanto no histórico da discussão

## Abordagem dos 3C

O sistema implementa os **3C (Comunicação, Coordenação e Cooperação)** da teoria de sistemas colaborativos de forma integrada e complementar. Cada componente trabalha em conjunto para criar uma experiência colaborativa eficaz.

### Comunicação

O sistema facilita a comunicação através de múltiplos canais integrados. O chat colaborativo permite que cada participante envie mensagens identificadas com seu nome, criando um fluxo de conversa natural e sequencial. O histórico de todas as mensagens é persistido em `conversation_history.txt`, garantindo que o contexto completo da discussão esteja sempre disponível. Além disso, o assistente `@colaborai` pode ser invocado por qualquer participante, acessando tanto o histórico de conversa quanto o conteúdo dos artigos indexados para fornecer respostas contextualizadas com citações precisas (fonte + página), criando uma comunicação multimodal que combina texto, documentos e referências estruturadas.

A comunicação no sistema também é persistente e compartilhada. Todos os participantes acessam o mesmo índice vetorial de documentos, garantindo que todos "falam a mesma língua" em termos de conhecimento base. O formato estruturado do histórico (`role::user::content`) permite que tanto novos participantes quanto o assistente IA entendam o contexto completo das discussões anteriores. Quando o assistente responde, ele não apenas fornece informações, mas também cita suas fontes, permitindo que os participantes verifiquem e validem as informações, criando uma comunicação baseada em fatos e não apenas em opiniões.

### Coordenação

A coordenação no sistema é garantida através de mecanismos que organizam e sincronizam as atividades dos participantes. O índice vetorial compartilhado (`vdb/`) serve como uma única fonte de verdade, evitando conflitos de versão e garantindo que todos os participantes acessem exatamente os mesmos documentos indexados. O sistema de registro em `indexed_files.txt` previne indexação duplicada e permite que todos saibam quais recursos estão disponíveis. Além disso, o gerenciamento de estado de sessão através de `session_id` único coordena a criação e reutilização de componentes como agentes e retrievers, evitando inicializações desnecessárias e garantindo eficiência.

A coordenação também ocorre através do roteamento inteligente do grafo LangGraph, onde a função `should_continue()` decide qual ferramenta usar em cada momento, evitando uso desnecessário de recursos. Cada nó executor (`retriever_executor`, `history_executor`, `exercise_executor`) tem responsabilidade específica e retorna ao `llm_processor` após execução, garantindo processamento ordenado. O histórico de conversa serve como memória compartilhada que coordena o contexto temporal, permitindo que participantes entendam a sequência de eventos e façam referências a mensagens anteriores, evitando repetição de perguntas e facilitando a continuidade da discussão.

### Cooperação

A cooperação é promovida através de mecanismos que fazem com que as contribuições individuais beneficiem todo o grupo. Cada participante pode fazer upload de artigos científicos, e todo esse conhecimento é agregado em um índice compartilhado, fazendo com que todos se beneficiem dos documentos que cada um adiciona. Quando um participante faz uma pergunta ou compartilha uma interpretação, essa informação fica disponível para todo o grupo através do histórico persistente. O assistente `@colaborai` atua como um membro colaborativo do grupo, não apenas respondendo perguntas, mas também gerando recursos como exercícios personalizados que sintetizam tanto o conteúdo dos artigos quanto o histórico de discussão do grupo.

A cooperação também se manifesta na geração de exercícios, onde o sistema combina múltiplas fontes de informação para criar recursos de aprendizado. Os exercícios são gerados baseados no conteúdo objetivo dos artigos, no histórico de discussão que reflete os entendimentos do grupo, e na participação individual de cada membro. Embora cada participante receba exercícios personalizados, todos têm acesso ao mesmo gabarito completo, permitindo aprendizado individual e coletivo simultaneamente. O histórico preserva todo o trabalho colaborativo, permitindo que novos participantes entendam o contexto e que o grupo continue seu trabalho entre sessões, criando uma memória coletiva que sustenta a cooperação ao longo do tempo.





