const selecionar = (seletor) => document.querySelector(seletor);
const CHAVE_CONVERSA_CHAT = "tech-doc-ai-conversation-id";
const INTERVALO_ATUALIZACAO_DOCUMENTOS_MS = 4000;
const STATUS_EM_PROCESSAMENTO = new Set(["recebido", "texto_extraido", "trechos_gerados"]);

const estadoInterface = {
  documentos: [],
  projetos: [],
  documentoSelecionadoId: null,
  mensagensChat: [],
  projetoChatId: "",
  temporizadorDocumentos: null,
};

const elementos = {
  botaoVerificarSaude: selecionar("#botao-verificar-saude"),
  mensagemSaude: selecionar("#mensagem-saude"),
  saidaSaude: selecionar("#saida-saude"),
  formularioIngestao: selecionar("#formulario-ingestao"),
  arquivoDocumento: selecionar("#arquivo-documento"),
  campoProjetoIngestao: selecionar("#campo-projeto-ingestao"),
  campoNovoProjeto: selecionar("#campo-novo-projeto"),
  mensagemSugestaoProjeto: selecionar("#mensagem-sugestao-projeto"),
  mensagemIngestao: selecionar("#mensagem-ingestao"),
  saidaIngestao: selecionar("#saida-ingestao"),
  botaoAtualizarDocumentos: selecionar("#botao-atualizar-documentos"),
  filtroProjetoDocumentos: selecionar("#filtro-projeto-documentos"),
  mensagemDocumentos: selecionar("#mensagem-documentos"),
  listaDocumentos: selecionar("#lista-documentos"),
  formularioChat: selecionar("#formulario-chat"),
  botaoNovaConversa: selecionar("#botao-nova-conversa"),
  botaoPerguntar: selecionar("#botao-perguntar"),
  campoProjetoChat: selecionar("#campo-projeto-chat"),
  campoPergunta: selecionar("#campo-pergunta"),
  campoLimiteFontes: selecionar("#campo-limite-fontes"),
  mensagemChat: selecionar("#mensagem-chat"),
  timelineChat: selecionar("#timeline-chat"),
};

function atualizarMensagem(elemento, texto, tipo = "neutra") {
  elemento.textContent = texto;
  elemento.classList.remove("neutra", "sucesso", "erro");
  elemento.classList.add(tipo);
}

function formatarJson(dados) {
  return JSON.stringify(dados, null, 2);
}

function gerarConversationId() {
  if (window.crypto?.randomUUID) {
    return window.crypto.randomUUID();
  }
  return `conv-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function obterConversationIdAtual() {
  const conversationIdSalvo = window.sessionStorage.getItem(CHAVE_CONVERSA_CHAT);
  if (conversationIdSalvo) {
    return conversationIdSalvo;
  }
  const novoConversationId = gerarConversationId();
  window.sessionStorage.setItem(CHAVE_CONVERSA_CHAT, novoConversationId);
  return novoConversationId;
}

function reiniciarConversationId() {
  window.sessionStorage.setItem(CHAVE_CONVERSA_CHAT, gerarConversationId());
}

function formatarData(valor) {
  if (!valor) {
    return "agora";
  }
  try {
    return new Intl.DateTimeFormat("pt-BR", {
      dateStyle: "short",
      timeStyle: "short",
    }).format(new Date(valor));
  } catch (_erro) {
    return valor;
  }
}

function formatarTamanho(bytes) {
  if (!Number.isFinite(bytes)) {
    return "tamanho nao informado";
  }
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatarStatus(status) {
  return status.replaceAll("_", " ");
}

async function lerRespostaJson(resposta) {
  const conteudo = await resposta.text();
  if (!conteudo) {
    return {};
  }
  try {
    return JSON.parse(conteudo);
  } catch (_erro) {
    return { mensagem: conteudo };
  }
}

async function requisitarJson(url, opcoes = {}) {
  const resposta = await fetch(url, opcoes);
  const dados = await lerRespostaJson(resposta);
  if (!resposta.ok) {
    const detalhe = dados.detalhe || dados.detail || dados.mensagem || "Falha ao consultar a API.";
    throw new Error(Array.isArray(detalhe) ? formatarJson(detalhe) : detalhe);
  }
  return dados;
}

function criarOpcaoProjeto(projeto, selecionado = false) {
  const opcao = document.createElement("option");
  opcao.value = String(projeto.id);
  opcao.textContent = projeto.nome;
  opcao.selected = selecionado;
  return opcao;
}

function preencherSeletorProjetos(select, opcoes = {}) {
  const {
    placeholder = "Selecione um projeto",
    incluirOpcaoTodos = false,
    valorTodos = "",
    rotuloTodos = "Todos os projetos",
    valorSelecionado = "",
  } = opcoes;
  select.replaceChildren();

  if (incluirOpcaoTodos) {
    const opcaoTodos = document.createElement("option");
    opcaoTodos.value = valorTodos;
    opcaoTodos.textContent = rotuloTodos;
    select.appendChild(opcaoTodos);
  } else {
    const placeholderOption = document.createElement("option");
    placeholderOption.value = "";
    placeholderOption.textContent = placeholder;
    select.appendChild(placeholderOption);
  }

  estadoInterface.projetos.forEach((projeto) => {
    select.appendChild(
      criarOpcaoProjeto(projeto, String(projeto.id) === String(valorSelecionado)),
    );
  });

  if (valorSelecionado) {
    select.value = String(valorSelecionado);
  }
}

async function carregarProjetos() {
  const projetos = await requisitarJson("/projetos?limite=200");
  estadoInterface.projetos = projetos;

  preencherSeletorProjetos(elementos.campoProjetoIngestao, {
    placeholder: "Selecione um projeto existente",
    valorSelecionado: elementos.campoProjetoIngestao.value,
  });
  preencherSeletorProjetos(elementos.filtroProjetoDocumentos, {
    incluirOpcaoTodos: true,
    valorSelecionado: elementos.filtroProjetoDocumentos.value,
  });
  preencherSeletorProjetos(elementos.campoProjetoChat, {
    placeholder: "Selecione o projeto do chat",
    valorSelecionado: estadoInterface.projetoChatId,
  });

  if (!estadoInterface.projetoChatId && projetos.length > 0) {
    estadoInterface.projetoChatId = String(projetos[0].id);
    elementos.campoProjetoChat.value = estadoInterface.projetoChatId;
  }
}

async function verificarSaude() {
  elementos.botaoVerificarSaude.disabled = true;
  atualizarMensagem(elementos.mensagemSaude, "Consultando o status da API...");
  try {
    const dados = await requisitarJson("/health");
    elementos.saidaSaude.textContent = formatarJson(dados);
    atualizarMensagem(elementos.mensagemSaude, "API disponivel.", "sucesso");
  } catch (erro) {
    elementos.saidaSaude.textContent = "";
    atualizarMensagem(elementos.mensagemSaude, `Erro ao consultar a API: ${erro.message}`, "erro");
  } finally {
    elementos.botaoVerificarSaude.disabled = false;
  }
}

async function sugerirProjetoParaArquivos() {
  const arquivo = elementos.arquivoDocumento.files?.[0];
  if (!arquivo) {
    atualizarMensagem(
      elementos.mensagemSugestaoProjeto,
      "Selecione um arquivo para receber uma sugestao de projeto.",
    );
    return;
  }

  try {
    const sugestao = await requisitarJson(
      `/projetos/sugestao?nome_arquivo=${encodeURIComponent(arquivo.name)}`,
    );
    if (sugestao.projeto_existente) {
      elementos.campoProjetoIngestao.value = String(sugestao.projeto_existente.id);
      elementos.campoNovoProjeto.value = "";
      atualizarMensagem(
        elementos.mensagemSugestaoProjeto,
        `Sugestao aplicada: usar o projeto existente "${sugestao.projeto_existente.nome}".`,
        "sucesso",
      );
      return;
    }

    if (sugestao.nome_sugerido) {
      elementos.campoProjetoIngestao.value = "";
      elementos.campoNovoProjeto.value = sugestao.nome_sugerido;
      atualizarMensagem(
        elementos.mensagemSugestaoProjeto,
        `Sugestao aplicada: criar o projeto "${sugestao.nome_sugerido}".`,
        "sucesso",
      );
      return;
    }

    atualizarMensagem(
      elementos.mensagemSugestaoProjeto,
      "Nao foi possivel sugerir um projeto automaticamente.",
    );
  } catch (erro) {
    atualizarMensagem(
      elementos.mensagemSugestaoProjeto,
      `Erro ao sugerir projeto: ${erro.message}`,
      "erro",
    );
  }
}

function montarCorpoUpload(projetoId, novoProjetoNome) {
  return {
    projeto_id: projetoId ? Number(projetoId) : null,
    novo_projeto_nome: novoProjetoNome || null,
  };
}

async function enviarDocumento(evento) {
  evento.preventDefault();
  const arquivos = Array.from(elementos.arquivoDocumento.files || []);
  if (arquivos.length === 0) {
    atualizarMensagem(elementos.mensagemIngestao, "Selecione ao menos um arquivo antes de enviar.", "erro");
    return;
  }

  const projetoId = elementos.campoProjetoIngestao.value.trim();
  const novoProjetoNome = elementos.campoNovoProjeto.value.trim();
  if (!projetoId && !novoProjetoNome) {
    atualizarMensagem(
      elementos.mensagemIngestao,
      "Selecione um projeto existente ou informe um novo projeto para a ingestao.",
      "erro",
    );
    return;
  }

  const botaoSubmit = elementos.formularioIngestao.querySelector("button[type='submit']");
  botaoSubmit.disabled = true;
  atualizarMensagem(
    elementos.mensagemIngestao,
    `Enviando ${arquivos.length} arquivo(s) para ingestao...`,
  );

  const documentosIngeridos = [];
  const falhas = [];

  try {
    for (const arquivo of arquivos) {
      const dadosFormulario = new FormData();
      dadosFormulario.append("arquivo", arquivo);
      if (projetoId) {
        dadosFormulario.append("projeto_id", projetoId);
      }
      if (!projetoId && novoProjetoNome) {
        dadosFormulario.append("novo_projeto_nome", novoProjetoNome);
      }

      try {
        const dados = await requisitarJson("/documentos/ingestao", {
          method: "POST",
          body: dadosFormulario,
        });
        documentosIngeridos.push(dados);
      } catch (erro) {
        falhas.push({
          nome_arquivo: arquivo.name,
          erro: erro.message,
        });
      }
    }

    elementos.saidaIngestao.textContent = formatarJson({
      total_arquivos: arquivos.length,
      documentos_ingeridos: documentosIngeridos,
      falhas,
    });

    if (documentosIngeridos.length > 0) {
      const projetoUsado = documentosIngeridos[0].projeto;
      await carregarProjetos();
      if (projetoUsado?.id) {
        elementos.filtroProjetoDocumentos.value = String(projetoUsado.id);
        estadoInterface.projetoChatId = String(projetoUsado.id);
        elementos.campoProjetoChat.value = estadoInterface.projetoChatId;
      }
    }

    await atualizarListaDocumentos({ selecionarPrimeiro: true });

    if (falhas.length === 0) {
      atualizarMensagem(
        elementos.mensagemIngestao,
        `${documentosIngeridos.length} arquivo(s) enviado(s) com sucesso.`,
        "sucesso",
      );
    } else if (documentosIngeridos.length > 0) {
      atualizarMensagem(
        elementos.mensagemIngestao,
        `${documentosIngeridos.length} arquivo(s) enviado(s) com sucesso e ${falhas.length} falha(s) detectada(s).`,
        "erro",
      );
    } else {
      atualizarMensagem(
        elementos.mensagemIngestao,
        `Nenhum arquivo foi enviado com sucesso. ${falhas.length} falha(s) detectada(s).`,
        "erro",
      );
    }

    elementos.formularioIngestao.reset();
    atualizarMensagem(
      elementos.mensagemSugestaoProjeto,
      "Selecione um arquivo para receber uma sugestao de projeto.",
    );
  } finally {
    botaoSubmit.disabled = false;
  }
}

function existeDocumentoEmProcessamento(documentos) {
  return documentos.some((documento) => STATUS_EM_PROCESSAMENTO.has(documento.status_processamento));
}

function ajustarPollingDocumentos() {
  if (estadoInterface.temporizadorDocumentos) {
    window.clearInterval(estadoInterface.temporizadorDocumentos);
    estadoInterface.temporizadorDocumentos = null;
  }

  if (!existeDocumentoEmProcessamento(estadoInterface.documentos)) {
    return;
  }

  estadoInterface.temporizadorDocumentos = window.setInterval(() => {
    atualizarListaDocumentos({ silencioso: true });
  }, INTERVALO_ATUALIZACAO_DOCUMENTOS_MS);
}

function criarBadgeStatus(status) {
  const badge = document.createElement("span");
  badge.className = `status-badge status-${status}`;
  badge.textContent = formatarStatus(status);
  return badge;
}

function selecionarDocumento(documentoId) {
  estadoInterface.documentoSelecionadoId = documentoId;
  renderizarListaDocumentos();
}

async function excluirDocumentoPorId(documentoId, nomeArquivo) {
  const confirmouExclusao = window.confirm(
    `Confirma a exclusao do documento ${documentoId} (${nomeArquivo})?`,
  );
  if (!confirmouExclusao) {
    atualizarMensagem(elementos.mensagemDocumentos, "Exclusao cancelada.");
    return;
  }

  atualizarMensagem(elementos.mensagemDocumentos, `Excluindo ${nomeArquivo}...`);
  try {
    await requisitarJson(`/documentos/${documentoId}`, { method: "DELETE" });
    atualizarMensagem(elementos.mensagemDocumentos, `${nomeArquivo} excluido com sucesso.`, "sucesso");
    await atualizarListaDocumentos();
  } catch (erro) {
    atualizarMensagem(elementos.mensagemDocumentos, `Erro ao excluir documento: ${erro.message}`, "erro");
  }
}

function montarCardDocumento(documento) {
  const artigo = document.createElement("article");
  artigo.className = "documento-card";
  if (documento.documento_id === estadoInterface.documentoSelecionadoId) {
    artigo.classList.add("selecionado");
  }

  const principal = document.createElement("div");
  principal.className = "documento-principal";

  const topo = document.createElement("div");
  topo.className = "documento-topo";

  const titulo = document.createElement("div");
  const nome = document.createElement("h3");
  nome.className = "documento-titulo";
  nome.textContent = documento.nome_arquivo;
  const meta = document.createElement("div");
  meta.className = "documento-meta";
  meta.innerHTML = `
    <span>ID ${documento.documento_id}</span>
    <span>${documento.tipo_arquivo.toUpperCase()}</span>
    <span>${formatarTamanho(documento.tamanho_bytes)}</span>
    <span>Projeto: ${documento.projeto.nome}</span>
  `;
  titulo.append(nome, meta);
  topo.append(titulo, criarBadgeStatus(documento.status_processamento));

  const detalhes = document.createElement("div");
  detalhes.className = "documento-detalhes";
  detalhes.innerHTML = `
    <span>Criado em ${formatarData(documento.criado_em)}</span>
    <span>Atualizado em ${formatarData(documento.atualizado_em)}</span>
    <span>${documento.quantidade_caracteres} caracteres extraidos</span>
    <span>Slug do projeto: ${documento.projeto.slug}</span>
  `;

  const acoes = document.createElement("div");
  acoes.className = "documento-acoes";

  const botaoSelecionar = document.createElement("button");
  botaoSelecionar.type = "button";
  botaoSelecionar.className = "botao-secundario";
  botaoSelecionar.textContent = "Destacar";
  botaoSelecionar.addEventListener("click", () => selecionarDocumento(documento.documento_id));

  const botaoUsarNoChat = document.createElement("button");
  botaoUsarNoChat.type = "button";
  botaoUsarNoChat.className = "botao-secundario";
  botaoUsarNoChat.textContent = "Usar projeto no chat";
  botaoUsarNoChat.addEventListener("click", () => {
    const novoProjetoId = String(documento.projeto.id);
    if (estadoInterface.projetoChatId !== novoProjetoId) {
      estadoInterface.projetoChatId = novoProjetoId;
      elementos.campoProjetoChat.value = novoProjetoId;
      iniciarNovaConversa(false);
      atualizarMensagem(
        elementos.mensagemChat,
        `Projeto ativo alterado para "${documento.projeto.nome}".`,
        "sucesso",
      );
    }
  });

  acoes.append(botaoSelecionar, botaoUsarNoChat);

  if (!STATUS_EM_PROCESSAMENTO.has(documento.status_processamento)) {
    const botaoExcluir = document.createElement("button");
    botaoExcluir.type = "button";
    botaoExcluir.className = "botao-perigo";
    botaoExcluir.textContent = "Excluir";
    botaoExcluir.addEventListener("click", async () => {
      await excluirDocumentoPorId(documento.documento_id, documento.nome_arquivo);
    });
    acoes.append(botaoExcluir);
  }

  principal.append(topo, detalhes, acoes);
  artigo.appendChild(principal);

  if (documento.mensagem_erro_processamento) {
    const erro = document.createElement("p");
    erro.className = "detalhe-erro";
    erro.textContent = documento.mensagem_erro_processamento;
    artigo.appendChild(erro);
  }

  return artigo;
}

function renderizarListaDocumentos() {
  elementos.listaDocumentos.replaceChildren();

  if (estadoInterface.documentos.length === 0) {
    const vazio = document.createElement("div");
    vazio.className = "estado-vazio-chat";
    vazio.innerHTML = "<strong>Nenhum documento listado.</strong><p>Envie um arquivo para iniciar a base de consulta.</p>";
    elementos.listaDocumentos.appendChild(vazio);
    return;
  }

  const fragmento = document.createDocumentFragment();
  estadoInterface.documentos.forEach((documento) => {
    fragmento.appendChild(montarCardDocumento(documento));
  });
  elementos.listaDocumentos.appendChild(fragmento);
}

async function atualizarListaDocumentos(opcoes = {}) {
  const { silencioso = false, selecionarPrimeiro = false } = opcoes;
  if (!silencioso) {
    atualizarMensagem(elementos.mensagemDocumentos, "Atualizando lista de documentos...");
  }

  const projetoId = elementos.filtroProjetoDocumentos.value;
  const sufixoProjeto = projetoId ? `&projeto_id=${encodeURIComponent(projetoId)}` : "";

  try {
    const documentos = await requisitarJson(`/documentos?limite=50${sufixoProjeto}`);
    estadoInterface.documentos = documentos;
    if (selecionarPrimeiro) {
      estadoInterface.documentoSelecionadoId = documentos[0]?.documento_id ?? null;
    } else if (!documentos.some((documento) => documento.documento_id === estadoInterface.documentoSelecionadoId)) {
      estadoInterface.documentoSelecionadoId = documentos[0]?.documento_id ?? null;
    }

    renderizarListaDocumentos();
    ajustarPollingDocumentos();

    if (!silencioso) {
      atualizarMensagem(
        elementos.mensagemDocumentos,
        `${documentos.length} documento(s) carregado(s).`,
        "sucesso",
      );
    }
  } catch (erro) {
    if (!silencioso) {
      atualizarMensagem(elementos.mensagemDocumentos, `Erro ao carregar documentos: ${erro.message}`, "erro");
    }
  }
}

function adicionarParagrafo(destino, texto, rotulo = null) {
  const paragrafo = document.createElement("p");
  if (rotulo) {
    const destaque = document.createElement("strong");
    destaque.textContent = rotulo;
    paragrafo.append(destaque, ` ${texto}`);
  } else {
    paragrafo.textContent = texto;
  }
  destino.appendChild(paragrafo);
}

function montarFontes(fontes) {
  const detalhes = document.createElement("details");
  detalhes.className = "fontes-resposta";

  const resumo = document.createElement("summary");
  resumo.textContent = `Fontes usadas (${fontes.length})`;
  detalhes.appendChild(resumo);

  const grade = document.createElement("div");
  grade.className = "fontes-grid";

  fontes.forEach((fonte) => {
    const titulo = fonte.titulo_contexto || fonte.secao || fonte.nome_arquivo;
    const pagina = fonte.pagina ? `Pagina ${fonte.pagina}` : "Pagina nao informada";
    const artigo = document.createElement("article");
    artigo.className = "fonte-card";

    adicionarParagrafo(artigo, `${titulo} - ${fonte.nome_arquivo}`, "Fonte:");
    adicionarParagrafo(artigo, `Documento ${fonte.documento_id}, trecho ${fonte.trecho_id}, ${pagina}`);
    adicionarParagrafo(artigo, Number(fonte.pontuacao_similaridade).toFixed(4), "Pontuacao:");
    if (fonte.caminho_hierarquico) {
      adicionarParagrafo(artigo, fonte.caminho_hierarquico, "Caminho:");
    }
    adicionarParagrafo(artigo, fonte.conteudo);
    grade.appendChild(artigo);
  });

  detalhes.appendChild(grade);
  return detalhes;
}

function renderizarMensagensChat() {
  elementos.timelineChat.replaceChildren();

  if (estadoInterface.mensagensChat.length === 0) {
    const vazio = document.createElement("div");
    vazio.className = "estado-vazio-chat";
    vazio.innerHTML = "<strong>Sem mensagens ainda.</strong><p>Escolha um projeto e envie uma pergunta para iniciar a conversa.</p>";
    elementos.timelineChat.appendChild(vazio);
    return;
  }

  const fragmento = document.createDocumentFragment();
  estadoInterface.mensagensChat.forEach((mensagem) => {
    const item = document.createElement("article");
    item.className = `mensagem-chat-item ${mensagem.papel}`;

    const etiqueta = document.createElement("span");
    etiqueta.className = "etiqueta-mensagem";
    etiqueta.textContent = mensagem.papel === "usuario" ? "Pergunta" : "Resposta";

    const bolha = document.createElement("div");
    bolha.className = "bolha-chat";
    bolha.textContent = mensagem.texto;

    item.append(etiqueta, bolha);

    if (mensagem.papel === "assistente" && Array.isArray(mensagem.fontes) && mensagem.fontes.length > 0) {
      item.appendChild(montarFontes(mensagem.fontes));
    }

    fragmento.appendChild(item);
  });

  elementos.timelineChat.appendChild(fragmento);
  elementos.timelineChat.scrollTop = elementos.timelineChat.scrollHeight;
}

function iniciarNovaConversa(atualizarMensagemUsuario = true) {
  reiniciarConversationId();
  estadoInterface.mensagensChat = [];
  renderizarMensagensChat();
  if (atualizarMensagemUsuario) {
    atualizarMensagem(
      elementos.mensagemChat,
      "Nova conversa iniciada. O historico anterior desta aba nao sera mais reutilizado.",
      "sucesso",
    );
  }
  elementos.campoPergunta.focus();
}

async function perguntarAoChat(evento) {
  evento.preventDefault();
  const pergunta = elementos.campoPergunta.value.trim();
  const limiteFontes = Number(elementos.campoLimiteFontes.value || 4);
  const projetoId = elementos.campoProjetoChat.value.trim();
  if (!projetoId) {
    atualizarMensagem(elementos.mensagemChat, "Selecione um projeto antes de perguntar ao chat.", "erro");
    return;
  }
  if (pergunta.length < 3) {
    atualizarMensagem(elementos.mensagemChat, "Digite uma pergunta com pelo menos tres caracteres.", "erro");
    return;
  }

  estadoInterface.mensagensChat.push({
    papel: "usuario",
    texto: pergunta,
  });
  renderizarMensagensChat();
  elementos.campoPergunta.value = "";
  elementos.botaoPerguntar.disabled = true;
  atualizarMensagem(elementos.mensagemChat, "Buscando fontes e gerando resposta...");

  try {
    const dados = await requisitarJson("/chat/perguntar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        projeto_id: Number(projetoId),
        pergunta,
        limite_fontes: limiteFontes,
        conversation_id: obterConversationIdAtual(),
      }),
    });
    if (dados.conversation_id) {
      window.sessionStorage.setItem(CHAVE_CONVERSA_CHAT, dados.conversation_id);
    }
    estadoInterface.mensagensChat.push({
      papel: "assistente",
      texto: dados.resposta,
      fontes: dados.fontes,
    });
    renderizarMensagensChat();
    const projetoAtivo = estadoInterface.projetos.find((projeto) => String(projeto.id) === projetoId);
    atualizarMensagem(
      elementos.mensagemChat,
      `Resposta recebida com sucesso para o projeto "${projetoAtivo?.nome ?? projetoId}".`,
      "sucesso",
    );
  } catch (erro) {
    estadoInterface.mensagensChat.push({
      papel: "assistente",
      texto: `Nao foi possivel concluir a resposta desta pergunta.\n\nDetalhe: ${erro.message}`,
      fontes: [],
    });
    renderizarMensagensChat();
    atualizarMensagem(elementos.mensagemChat, `Erro ao perguntar ao chat: ${erro.message}`, "erro");
  } finally {
    elementos.botaoPerguntar.disabled = false;
  }
}

function aoTrocarProjetoChat() {
  const novoProjetoId = elementos.campoProjetoChat.value;
  if (estadoInterface.projetoChatId !== novoProjetoId) {
    estadoInterface.projetoChatId = novoProjetoId;
    iniciarNovaConversa(false);
  }
  const projetoAtivo = estadoInterface.projetos.find((projeto) => String(projeto.id) === novoProjetoId);
  if (projetoAtivo) {
    atualizarMensagem(
      elementos.mensagemChat,
      `Projeto ativo no chat: "${projetoAtivo.nome}".`,
      "sucesso",
    );
  } else {
    atualizarMensagem(
      elementos.mensagemChat,
      "Selecione um projeto para ativar a conversa contextualizada.",
    );
  }
}

async function inicializarInterface() {
  renderizarMensagensChat();
  await carregarProjetos();
  aoTrocarProjetoChat();
  await atualizarListaDocumentos({ silencioso: true });
}

elementos.botaoVerificarSaude.addEventListener("click", verificarSaude);
elementos.arquivoDocumento.addEventListener("change", () => {
  void sugerirProjetoParaArquivos();
});
elementos.formularioIngestao.addEventListener("submit", enviarDocumento);
elementos.botaoAtualizarDocumentos.addEventListener("click", () => {
  void atualizarListaDocumentos();
});
elementos.filtroProjetoDocumentos.addEventListener("change", () => {
  void atualizarListaDocumentos();
});
elementos.formularioChat.addEventListener("submit", perguntarAoChat);
elementos.botaoNovaConversa.addEventListener("click", () => iniciarNovaConversa(true));
elementos.campoProjetoChat.addEventListener("change", aoTrocarProjetoChat);

void inicializarInterface();
