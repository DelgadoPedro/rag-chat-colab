# Cenário Colaborativo e Abordagem dos 3C

## Contexto

O sistema foi desenvolvido para um cenário acadêmico de estudo colaborativo, no qual um grupo de estudantes trabalha em conjunto para preparar-se para uma avaliação sobre um tema específico. O sistema simula um ambiente de 5 participantes pré-configurados.

### Fluxo de Trabalho Colaborativo

1. **Preparação Inicial**
   - O grupo faz upload de 1 a 5 artigos científicos em PDF relacionados ao tema de estudo.
   - O sistema indexa automaticamente os documentos em um banco vetorial compartilhado.

2. **Discussão Colaborativa**
   - Cada participante pode enviar mensagens no chat, identificando-se através de um seletor.
   - As mensagens são atribuídas ao participante ativo e salvas em um histórico compartilhado.

3. **Assistência Inteligente**
   - Quando necessário, qualquer participante pode chamar o assistente `@colaborai`.
   - O assistente acessa o conteúdo dos artigos indexados para responder perguntas.

4. **Geração de Exercícios**
   - O sistema gera questões personalizadas para cada participante, após solicitação.
   - Os exercícios são baseados tanto no conteúdo dos artigos quanto no histórico da discussão.

## Abordagem dos 3C

O sistema implementa os **3C (Comunicação, Coordenação e Cooperação)** da teoria de sistemas colaborativos de forma integrada e complementar. Cada componente trabalha em conjunto para criar uma experiência colaborativa eficaz.

### Comunicação

A Comunicação é facilitada pelo chat colaborativo, que permite a troca de mensagens identificadas entre os participantes, com o histórico da conversa sendo persistido para garantir o contexto completo da discussão. O assistente `@colaborai` atua como um canal de comunicação multimodal, acessível por qualquer participante para fornecer respostas contextualizadas e citadas (fonte + página) com base no histórico e nos artigos indexados.

### Coordenação

A Coordenação é alcançada através de mecanismos que organizam e sincronizam as atividades. O índice vetorial compartilhado (`vdb/`) funciona como uma única fonte de verdade para os documentos, garantindo que todos os participantes acessem o mesmo conjunto de informações e prevenindo conflitos. A coordenação também é gerenciada pelo roteamento inteligente do grafo LangGraph, que utiliza a função `should_continue()` para decidir qual ferramenta ou executor deve ser acionado, garantindo o processamento eficiente e ordenado.

### Cooperação

A Cooperação é promovida pela forma como as contribuições individuais beneficiam todo o grupo. O upload de artigos científicos por qualquer membro resulta na agregação desse conhecimento ao índice compartilhado, beneficiando todos os participantes. O assistente `@colaborai` apoia a cooperação ao gerar exercícios personalizados que sintetizam o conteúdo dos artigos e o histórico da discussão, transformando o trabalho em um ciclo ativo de reforço cognitivo. O histórico persistente preserva a memória coletiva do grupo, sustentando a cooperação ao longo do tempo.







