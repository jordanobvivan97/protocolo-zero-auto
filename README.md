# Agente do Protocolo Zero

Pesquisa, escreve, confere e publica sozinho os carrosséis do O Sobrevivente - Protocolo Zero no Instagram e na Página do Facebook (sem hashtags), seguindo a Fundação.

## Como funciona

1. **Toda noite, 20h47 (Claude, tarefa agendada, modo lote):** procura alerta oficial das últimas 24h; se não houver, escreve o post de amanhã pelo calendário da Fundação, confere cada número na fonte oficial aberta na hora, roda o validador, renderiza, olha todas as imagens e abre um PR.
2. **Todo dia, 11h43 (Claude, tarefa agendada, modo vigia):** só procura alerta oficial. Se houver um relevante, prepara o "Alerta explicado" para as 19h40 do mesmo dia e abre um PR.
3. **Você aprova:** abre o PR no app do GitHub, olha as lâminas e as fontes, confere as pendências marcadas e faz merge. Sem merge, nada sai.
4. **Nos horários (GitHub Actions):** `scripts/publicar.py` roda o validador de novo e publica pela API oficial do Instagram.
5. **Todo dia, 07h23:** `scripts/metricas.py` grava alcance, salvamentos, envios e seguidores em `metricas/`.

Botão de emergência: crie um arquivo chamado `PAUSADO` na raiz do repositório (pelo app do GitHub mesmo) e nada é publicado até você apagá-lo.

## O que o validador barra

Número sem fonte oficial, conta errada, blog ou loja como fonte, fonte não citada na legenda, falta da frase da Defesa Civil, medo vendido, governo escondendo, armas, saque, compra por pânico, dose de remédio, diagnóstico, "como médico", cenário sem rótulo de hipotético, CTA de isca ou link que ainda não existe, travessão, formato igual ao do post anterior, gancho repetido dos 2 últimos, pauta repetida em 30 dias, protocolo com número repetido, portão de originalidade com algum "não". Matéria de imprensa só entra com pendência, e aí o post exige PR mesmo no modo direto.

Limite conhecido: número escrito por extenso não é conferido. A regra de escrita do agente é usar algarismos.

## Separação do Promessa

Repositório público (o Instagram baixa as imagens pelo jsDelivr, como no Promessa), por isso aqui só ficam as regras editoriais (`REGRAS.md`): persona completa, monetização e riscos ficam apenas no documento Fundação do projeto do Claude. App próprio na Meta, fora do portfólio do Promessa; horários, identidade visual e nome de commit próprios. Segredos só nos Secrets do GitHub, nunca no código.

O que continua visível: quem abrir o perfil do GitHub jordanobvivan97 vê os dois repositórios lado a lado. Se um dia isso pesar, a saída é mover este repositório para outra conta do GitHub.

## Configuração (uma vez)

### 1. Meta
1. App "Protocolo Zero Agente" (ID 973666135364075), criado em 07/11/2026, com o caso de uso "Gerenciar mensagens e conteúdo no Instagram" e as permissões `instagram_business_basic`, `instagram_business_content_publish` e `instagram_business_manage_insights`.
2. Portfólio empresarial **próprio** do Protocolo Zero (nunca o do Promessa), com o app, a conta do Instagram e a Página do Facebook adicionados como ativos.
3. No portfólio, Usuários do sistema: criar um usuário do sistema (Administrador), atribuir a ele o app, a conta do Instagram e a Página com controle total, e gerar o token com as permissões do app mais `pages_show_list`, `pages_read_engagement` e `pages_manage_posts`. Token de usuário do sistema não expira.
4. IG_USER_ID e FB_PAGE_ID: o ID da conta do Instagram e o ID da Página, que aparecem no portfólio (Contas do Instagram e Páginas).

### 2. GitHub (repositório público `protocolo-zero-auto`)
1. Settings, Secrets and variables, Actions, New repository secret: `IG_TOKEN`, `IG_USER_ID` e `FB_PAGE_ID`.
2. Settings, Actions, General: "Read and write permissions" e "Allow GitHub Actions to create and approve pull requests" (feito em 07/11/2026).

### 3. Teste só de leitura
Actions, "Testar conexao (so leitura)", Run workflow. O resultado vai para `metricas/teste-conexao.json` (sem segredos). Precisa mostrar o username da conta, `pagina_token_ok: true`, `instagram_ligado_a_pagina_confere: true` e `jsdelivr_responde: true`.

Você nunca precisa me passar esses tokens: eles vão direto para os Secrets do GitHub.

## Estrutura

```
REGRAS.md                recorte editorial da Fundação (a fonte de verdade é o documento do projeto)
GERAR.md                 roteiro que o Claude segue em cada execução
marca.json               calendário das 4 semanas, horários, modo de aprovação, isca/guia/link ativos
fontes_permitidas.json   domínios e perfis oficiais aceitos como fonte de número
pautas/banco.json        as 36 pautas da Fundação
fila/AAAA-MM-DD/NN/      posts aprovados esperando o horário (post.json, slides, roteiro.md)
publicados/              o que já foi ao ar, com link
exemplos/                post de referência, fora da fila
metricas/                posts.csv, conta.csv, resumo.json
scripts/                 render, validar, publicar, metricas, testar_conexao
```

## Depois da primeira semana

Para dispensar a aprovação, troque `"modo_aprovacao": "pr"` por `"direto"` em `marca.json`. Mesmo assim, post com fonte de imprensa pendente continua indo por PR. Se quiser que algum formato sempre passe por você (por exemplo `saude` e `alerta`), liste-o em `pr_sempre`.

Quando a isca "Kit 72h" ou o guia estiverem no ar, mude `isca_ativa`, `guia_ativo` ou `link_bio_ativo` para `true`; antes disso o validador recusa CTA que aponte para eles.

## Fase 2 (Reels)

Cada post já sai com `roteiro.md`. Para publicar um Reel pelo agente: grave, coloque `video.mp4` (e opcionalmente `capa.jpg`) na pasta do post e mude `"tipo"` para `"reel"`. O publicador só solta Reel quando o vídeo existe. Voz sintética e montagem automática ficam para quando os carrosséis estiverem validados.
