# Instruções do agente (lote diário e vigia de alertas)

Roteiro que o Claude segue nas tarefas agendadas. Ele pesquisa, escreve, confere e renderiza; quem publica é o GitHub Actions (`scripts/publicar.py`). A confiança é o produto: na dúvida entre publicar e não publicar, não publica e explica no resumo.

Há dois modos de execução, definidos pelo prompt da tarefa:
- **Lote** (toda noite): faz o passo 1 (alertas) e, se nenhum alerta furar a fila, monta o post de amanhã.
- **Vigia** (meio-dia): faz só o passo 1. Sem alerta relevante, termina em uma linha, sem commit.

## 0. Ler o estado

1. `REGRAS.md` inteiro: tese, para quem, o que o canal nunca diz, formatos, identidade, portão. Se a ferramenta Projects estiver disponível, leia também o documento "Fundação" do projeto, que é a fonte de verdade (persona completa e funil); se algo divergir, vale a Fundação e você avisa no resumo.
2. `marca.json`: calendário, horários permitidos, modo de aprovação, se isca, guia e link da bio já existem.
3. `pautas/banco.json` e as pastas `fila/` e `publicados/`: qual o último número de protocolo, os últimos formatos e tipos de gancho, as pautas já usadas.
4. `metricas/resumo.json`, se existir. Só tire conclusão de formato com 15 ou mais posts dele (regra da Fundação); abaixo disso, diga "amostra pequena" e não mude nada por causa do número.

## 1. Modo pico: alerta oficial

Procure na web (busca padrão; estendida se vier pouco) comunicados das últimas 24 horas:
- Inmet: aviso vermelho ou laranja que pegue SC, PR ou RS.
- Defesa Civil Nacional ou estadual (SC, PR, RS): orientação à população, alerta de evento, comunicado que viralizou.
- Cemaden: alerta de risco hidrológico ou geológico no Sul.

É relevante quando muda o que uma família do Sul deveria fazer nos próximos dias, ou quando um comunicado oficial está gerando confusão (gente achando que é catástrofe). Não é relevante: aviso amarelo isolado, notícia velha requentada, boato sem órgão por trás.

Se for relevante e ainda não houver post sobre ele em `fila/` ou `publicados/`:
1. Abra a fonte primária (site ou perfil oficial). Portal de notícia não basta. Se a fonte primária não abrir, use a matéria como `imprensa_citando_oficial` com `pendencia` dizendo exatamente o que Jordano precisa conferir e onde, e destaque isso no resumo.
2. Confira a validade do alerta. Se ele já tiver acabado no horário de publicação, não escreva "alerta ativo": ou o post vira "o que esse alerta ensinou" com o período no passado, ou não sai.
3. O Alerta explicado fura a fila: formato `alerta`, carrossel de 4 a 6 lâminas (o que é, o que não é, o que fazer agora, onde acompanhar) + `roteiro.md` do Reel de 20 a 30s. Horário `07:40` do dia seguinte quando sair do lote noturno; `19:40` do mesmo dia quando sair da vigia do meio-dia. O post que estava previsto para aquele dia é empurrado para o próximo dia do calendário.
4. Entregue conforme `modo_aprovacao` (no modo pr, branch `lote-AAAA-MM-DD-alerta`) e avise no resumo final com a palavra ALERTA na primeira linha.

## 2. Escolher os posts de amanhã (modo lote)

- Data de amanhã no fuso America/Sao_Paulo. Ache a semana em `marca.json` > `calendario`. Se amanhã não está em `dias`, não há post: termine dizendo isso. Depois de 04/12, use `volume_padrao_depois`.
- Quantidade e horários: `posts_por_dia` e `horarios` da semana (sem `horarios`, use `horario_padrao`). Na semana 1 são 3 posts por dia: 07:50, 12:20 e 19:40. Cada post vai numa pasta própria (`fila/AAAA-MM-DD/01`, `02`, `03`), todos no mesmo PR.
- No mesmo dia, nada de formato repetido em posts seguidos (o último post de hoje conta para o primeiro de amanhã) e nada de tipo de gancho repetido entre os 2 anteriores; o validador confere pela ordem de data e horário.
- Pauta: a próxima ainda não usada da lista da semana. Se a próxima repetir o formato do post anterior, pegue a seguinte da lista que não repita. Lista da semana esgotada e `pautas_extras_permitidas` true: escolha do banco uma pauta **sem semana definida** (as marcadas para as semanas 2 a 4 ficam reservadas); se o banco livre acabar, crie pauta nova no `pautas/banco.json` com o próximo id e `"origem": "agente"`, dentro do foco da semana, e avise no resumo. Fora desse caso, escolha do banco a pauta de maior aderência ao foco da semana, sem repetir 30 dias.
- Semana 1 segue os 3 posts-âncora da Fundação nesta ordem: Post 1 (Alerta explicado, carimbo PROTOCOLO 000, cobre as pautas Z01 e Z02), Post 2 (Protocolo 001, kit 72h, Z03), Post 3 (Protocolo 002, quanta água, Z04). O texto-base está em `REGRAS.md`, mas **todo número dele é reconferido na fonte** antes de usar; se a fonte disser outra coisa, vale a fonte, e isso vai como alerta no resumo.
- Número do protocolo: o maior já usado + 1, com 3 dígitos.
- Horário: os da semana, salvo Alerta (passo 1). Alerta que fura a fila ocupa o horário mais cedo livre e empurra o post comum daquele horário para o próximo dia.

## 3. Pesquisar e conferir (antes de escrever uma linha)

- Todo número que vai aparecer (quantidade, prazo, telefone que não seja 190/192/193/199/180/188/136, porcentagem, contagem de pessoas) vem de uma página aberta **nesta execução**. Nunca da memória, nunca só da Fundação, nunca de blog ou loja.
- Ordem de preferência: página oficial (`pagina_oficial`) > perfil oficial do órgão (`perfil_oficial`) > matéria citando o órgão (`imprensa_citando_oficial`, com pendência). Os domínios aceitos estão em `fontes_permitidas.json`; para incluir um órgão oficial novo, edite esse arquivo no mesmo PR e diga no resumo.
- Fontes divergem: mostre a faixa e quem diz o quê. Não escolha um número sozinho para parecer mais simples.
- Órgão estrangeiro entra para comparação e sempre nomeado como estrangeiro ("FEMA, agência de emergências dos EUA").
- Contas feitas pelo post (tabela, total da família) vão em `derivados` com a conta escrita; o validador refaz cada uma.
- Contagem interna do próprio post ("3 decisões", "7 categorias") vai em `numeros_proprios` com a justificativa.
- Use algarismos para toda quantidade. Número por extenso escapa do validador.

## 4. Escrever

Voz: grave, calma, ritmo de briefing suave. Informa, não assusta. A persona é o responsável pela casa que viu o alerta e ficou sem saber se era sério; ela quer sentir "minha família está coberta" e tem medo de exagerar e de gastar demais.

- Gancho (lâmina 1): pode ser cinematográfico, mas a promessa tem que ser cumprida até a lâmina 2 com algo concreto. Tipos (`gancho_tipo`), nunca repetindo os 2 últimos: `divergencia` (cada órgão diz uma coisa), `ordem` (a ordem certa das ações), `erro_comum` (o que quase todo mundo faz errado), `dado_oficial` (um número oficial que surpreende), `cenario` (e se... hipotético), `comunicado` (o que o órgão disse, de verdade), `inventario` (item por item), `primeiros_minutos` (os primeiros N minutos). Nada de carta, de confissão em primeira pessoa ou de cena emocional em terceira pessoa: são estruturas do Promessa e não podem ser reaproveitadas.
- Corpo: uma ideia por lâmina; frases curtas; nada de travessão; nada de "basicamente", "sinceramente" e afins. Destaque em laranja com `**palavra**`, no máximo um trecho por lâmina.
- O canal nunca diz: "o fim está próximo", que o governo esconde algo, nada de armas, defesa armada ou saque, nada de compra por pânico. O validador recusa, mas não escreva para ele recusar.
- Cenário "E se...?": `"hipotetico": true` (o render põe o rótulo CENÁRIO HIPOTÉTICO em todas as lâminas) e a legenda diz que é hipotético.
- Saúde: educativo. Sem dose, sem nome de remédio com quantidade, sem diagnóstico, sem "como médico" ou "sou estudante de medicina". Diga quando procurar atendimento (192, SAMU) e escreva na legenda que o conteúdo é educativo e não substitui atendimento.
- CTA único, pelo funil da pauta: alcance pede para seguir ("Siga para receber o Protocolo 00X"); salvamento pede para salvar ou mandar para quem mora junto; conversão aponta para a isca ou o guia **só se** `isca_ativa`/`guia_ativo` forem true, senão vira salvar. "Link na bio" só com `link_bio_ativo` true.
- Legenda: 3 a 6 linhas curtas; depois o parágrafo `Fontes:` com cada órgão citado; depois a frase `Em emergência real, siga a Defesa Civil da sua cidade.`; no máximo 5 hashtags. Afiliado: `"afiliado": true` e `#publi` na legenda.
- Imagem: só a arte do render (ficha, carimbo, tabela). Nunca foto de desastre, nunca imagem gerada apresentada como registro real.

Formato por tipo nesta fase (Reels automáticos ficam para a fase 2):
- `protocolo` e `calculadora`: carrossel de 6 a 10 lâminas.
- `cenario`, `alerta` e `saude`: carrossel de 4 a 7 lâminas.
- Todo post leva também `roteiro.md` com o Reel equivalente, para Jordano gravar se quiser.

## 5. Produzir e conferir

Crie `fila/AAAA-MM-DD/01/post.json` no formato do exemplo abaixo e o `roteiro.md`. Depois:

```
python scripts/validar.py fila/AAAA-MM-DD
python scripts/render.py fila/AAAA-MM-DD/01
```

Abra **todas** as imagens com a ferramenta Read e confira: texto inteiro visível, nada cortado, legível no celular, sem erro de português, destaque laranja no lugar certo. Corrija e renderize de novo.

Antes de entregar, responda ao portão de originalidade com honestidade (o campo `portao` do post.json). Se alguma resposta for "não", reescreva; não marque `true` para passar no validador.

Esquema do post.json (campos obrigatórios em negrito na prática: todos, salvo os opcionais indicados):

```json
{
  "id": "2026-11-09-01",
  "pauta_id": "Z04",
  "formato": "calculadora",
  "tipo": "carrossel",
  "horario": "19:40",
  "protocolo": "002",
  "gancho_tipo": "divergencia",
  "hipotetico": false,
  "slides": [
    {"layout": "capa", "titulo": "...", "subtitulo": "..."},
    {"layout": "texto", "etiqueta": "...", "contador": "...", "titulo": "...", "texto": "..."},
    {"layout": "ficha", "etiqueta": "...", "titulo": "...", "itens": ["...", "..."], "marcados": [0], "nota": "opcional"},
    {"layout": "tabela", "titulo": "...", "colunas": ["..."], "linhas": [["..."]], "larguras": [1, 1], "colunas_destaque": [1], "nota": "opcional"},
    {"layout": "fechamento", "titulo": "opcional", "texto": "opcional", "cta": "Uma frase só."}
  ],
  "legenda": "...\n\nFontes: ...\n\nEm emergência real, siga a Defesa Civil da sua cidade.\n\n#...",
  "fontes": [
    {"orgao": "Nome do órgão", "url": "https://...", "conferencia": "pagina_oficial", "afirmacao": "o que a fonte diz, nas suas palavras", "numeros": ["2", "72"], "consultado_em": "AAAA-MM-DD", "pendencia": "só para imprensa_citando_oficial"}
  ],
  "derivados": [{"valor": "24", "conta": "4*2*3"}],
  "numeros_proprios": {"3": "três decisões do roteiro, contagem interna"},
  "portao": {"ideia_nova": true, "formato_diferente_do_ultimo": true, "gancho_diferente_dos_2_ultimos": true, "concreto_ate_lamina_2": true, "especifico_do_tema": true, "numeros_com_fonte": true, "sem_ficcao_como_fato": true, "assinaria_com_meu_nome": true},
  "roteiro_reel": "roteiro.md"
}
```

O render coloca sozinho o carimbo PROTOCOLO 00X, o rodapé, a numeração das lâminas, o rótulo de cenário hipotético, o fecho fixo e a frase da Defesa Civil. Não repita esses textos nos slides.

Modelo do `roteiro.md`:

```
PROTOCOLO 00X · <título>
Formato: Reel 30 a 45s · Funil: <alcance|salvamento|conversão>

TEXTO NA TELA (0 a 3s): <gancho em caixa alta>

DIREÇÃO VISUAL: <cena a cena; estética de dossiê; nada de foto real de vítima ou desastre>

NARRAÇÃO:
<texto falado, frases curtas, números em algarismo>

FECHO: Protocolo arquivado. Sua família está um passo à frente.
CTA: <um só>
LEGENDA: igual à do carrossel.
```

## 6. Entregar

- `modo_aprovacao: "pr"`: a partir da main atualizada, crie a branch `lote-AAAA-MM-DD`, grave `fila/AAAA-MM-DD/RESUMO.md` e dê `git push origin lote-AAAA-MM-DD`. O workflow abre o PR. Sem merge até o horário, nada sai.
- `modo_aprovacao: "direto"`: commit direto na main, inclusive post com fonte pendente; só formatos listados em `pr_sempre` vão por PR. Alerta explicado segue o mesmo modo. Grave o `RESUMO.md` mesmo assim: é onde Jordano vê as pendências para conferir depois que o post sair.
- `RESUMO.md` traz: horário, formato, pauta, gancho, primeira frase da capa; a lista de fontes com o tipo de conferência; e, em forma de checklist, cada pendência que Jordano precisa conferir antes do merge.

Termine com um resumo de 3 linhas para Jordano: o que vai sair e quando (um item por post); qualquer número da Fundação que a fonte não confirmou; e qualquer alerta (pendência de fonte, pauta acabando, erro que exigiu reescrita, falha de push). Português do Brasil, sem travessão.
