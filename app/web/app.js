const selecionar = (seletor) => document.querySelector(seletor);
const CHAVE_CONVERSA_CHAT = "tech-doc-ai-conversation-id";

const elementos = {
  botaoVerificarSaude: selecionar("#botao-verificar-saude"),
  mensagemSaude: selecionar("#mensagem-saude"),
  saidaSaude: selecionar("#saida-saude"),
  formularioIngestao: selecionar("#formulario-ingestao"),
  arquivoDocumento: selecionar("#arquivo-documento"),
  mensagemIngestao: selecionar("#mensagem-ingestao"),
  documentoIdAtual: selecionar("#documento-id-atual"),
  saidaIngestao: selecionar("#saida-ingestao"),
  formularioStatusDocumento: selecionar("#formulario-status-documento"),
  campoDocumentoId: selecionar("#campo-documento-id"),
  mensagemStatusDocumento: selecionar("#mensagem-status-documento"),
  saidaStatusDocumento: selecionar("#saida-status-documento"),
  formularioExclusaoDocumento: selecionar("#formulario-exclusao-documento"),
  campoDocumentoIdExclusao: selecionar("#campo-documento-id-exclusao"),
  mensagemExclusaoDocumento: selecionar("#mensagem-exclusao-documento"),
  saidaExclusaoDocumento: selecionar("#saida-exclusao-documento"),
  formularioChat: selecionar("#formulario-chat"),
  botaoNovaConversa: selecionar("#botao-nova-conversa"),
  campoPergunta: selecionar("#campo-pergunta"),
  campoLimiteFontes: selecionar("#campo-limite-fontes"),
  mensagemChat: selecionar("#mensagem-chat"),
  respostaChat: selecionar("#resposta-chat"),
  fontesChat: selecionar("#fontes-chat"),
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

function iniciarNovaConversa() {
  window.sessionStorage.setItem(CHAVE_CONVERSA_CHAT, gerarConversationId());
  elementos.respostaChat.textContent = "Sem resposta ainda.";
  elementos.fontesChat.textContent = "Nenhuma fonte retornada.";
  atualizarMensagem(elementos.mensagemChat, "Nova conversa iniciada. O historico anterior desta aba nao sera mais reutilizado.", "sucesso");
  elementos.campoPergunta.focus();
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

async function verificarSaude() {
  elementos.botaoVerificarSaude.disabled = true;
  atualizarMensagem(elementos.mensagemSaude, "Consultando o status da API...");
  try {
    const dados = await requisitarJson("/health");
    elementos.saidaSaude.textContent = formatarJson(dados);
    atualizarMensagem(elementos.mensagemSaude, "API disponível.", "sucesso");
  } catch (erro) {
    elementos.saidaSaude.textContent = "";
    atualizarMensagem(elementos.mensagemSaude, `Erro ao consultar a API: ${erro.message}`, "erro");
  } finally {
    elementos.botaoVerificarSaude.disabled = false;
  }
}

async function enviarDocumento(evento) {
  evento.preventDefault();
  const arquivos = Array.from(elementos.arquivoDocumento.files || []);
  if (arquivos.length === 0) {
    atualizarMensagem(elementos.mensagemIngestao, "Selecione ao menos um arquivo antes de enviar.", "erro");
    return;
  }

  elementos.formularioIngestao.querySelector("button[type='submit']").disabled = true;
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

    const ultimoDocumento = documentosIngeridos.at(-1);
    if (ultimoDocumento) {
      elementos.documentoIdAtual.textContent = ultimoDocumento.documento_id;
      elementos.campoDocumentoId.value = ultimoDocumento.documento_id;
      elementos.campoDocumentoIdExclusao.value = ultimoDocumento.documento_id;
    }

    elementos.saidaIngestao.textContent = formatarJson({
      total_arquivos: arquivos.length,
      documentos_ingeridos: documentosIngeridos,
      falhas,
    });

    if (falhas.length === 0) {
      atualizarMensagem(
        elementos.mensagemIngestao,
        `${documentosIngeridos.length} arquivo(s) enviado(s) com sucesso.`,
        "sucesso",
      );
      elementos.formularioIngestao.reset();
      return;
    }

    if (documentosIngeridos.length > 0) {
      atualizarMensagem(
        elementos.mensagemIngestao,
        `${documentosIngeridos.length} arquivo(s) enviado(s) com sucesso e ${falhas.length} falha(s) detectada(s).`,
        "erro",
      );
      return;
    }

    atualizarMensagem(
      elementos.mensagemIngestao,
      `Nenhum arquivo foi enviado com sucesso. ${falhas.length} falha(s) detectada(s).`,
      "erro",
    );
  } finally {
    elementos.formularioIngestao.querySelector("button[type='submit']").disabled = false;
  }
}

async function atualizarStatusDocumento(evento) {
  evento.preventDefault();
  const documentoId = elementos.campoDocumentoId.value.trim();
  if (!documentoId) {
    atualizarMensagem(elementos.mensagemStatusDocumento, "Informe o ID do documento.", "erro");
    return;
  }

  atualizarMensagem(elementos.mensagemStatusDocumento, "Consultando o status do documento...");
  try {
    const dados = await requisitarJson(`/documentos/${documentoId}`);
    elementos.saidaStatusDocumento.textContent = formatarJson(dados);
    atualizarMensagem(
      elementos.mensagemStatusDocumento,
      `Status atual: ${dados.status_processamento}.`,
      "sucesso",
    );
  } catch (erro) {
    elementos.saidaStatusDocumento.textContent = "";
    atualizarMensagem(elementos.mensagemStatusDocumento, `Erro ao consultar documento: ${erro.message}`, "erro");
  }
}

async function excluirDocumento(evento) {
  evento.preventDefault();
  const documentoId = elementos.campoDocumentoIdExclusao.value.trim();
  if (!documentoId) {
    atualizarMensagem(elementos.mensagemExclusaoDocumento, "Informe o ID do documento.", "erro");
    return;
  }

  const confirmouExclusao = window.confirm(`Confirma a exclusão do documento ${documentoId}?`);
  if (!confirmouExclusao) {
    atualizarMensagem(elementos.mensagemExclusaoDocumento, "Exclusão cancelada.");
    return;
  }

  atualizarMensagem(elementos.mensagemExclusaoDocumento, "Excluindo documento...");
  try {
    const dados = await requisitarJson(`/documentos/${documentoId}`, { method: "DELETE" });
    elementos.saidaExclusaoDocumento.textContent = formatarJson(dados);
    if (elementos.documentoIdAtual.textContent === documentoId) {
      elementos.documentoIdAtual.textContent = "não informado";
    }
    if (elementos.campoDocumentoId.value === documentoId) {
      elementos.campoDocumentoId.value = "";
      elementos.saidaStatusDocumento.textContent = "";
    }
    atualizarMensagem(elementos.mensagemExclusaoDocumento, dados.mensagem, "sucesso");
  } catch (erro) {
    elementos.saidaExclusaoDocumento.textContent = "";
    atualizarMensagem(elementos.mensagemExclusaoDocumento, `Erro ao excluir documento: ${erro.message}`, "erro");
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
  elementos.fontesChat.replaceChildren();
  if (!fontes || fontes.length === 0) {
    elementos.fontesChat.textContent = "Nenhuma fonte retornada.";
    return;
  }

  fontes.forEach((fonte) => {
    const titulo = fonte.titulo_contexto || fonte.secao || fonte.nome_arquivo;
    const pagina = fonte.pagina ? `Página ${fonte.pagina}` : "Página não informada";
    const artigo = document.createElement("article");
    artigo.classList.add("fonte");

    adicionarParagrafo(artigo, `${titulo} — ${fonte.nome_arquivo}`, "Fonte:");
    adicionarParagrafo(artigo, `Documento ${fonte.documento_id}, trecho ${fonte.trecho_id}, ${pagina}`);
    adicionarParagrafo(artigo, Number(fonte.pontuacao_similaridade).toFixed(4), "Pontuação:");
    if (fonte.caminho_hierarquico) {
      adicionarParagrafo(artigo, fonte.caminho_hierarquico, "Caminho:");
    }
    adicionarParagrafo(artigo, fonte.conteudo);
    elementos.fontesChat.appendChild(artigo);
  });
}

async function perguntarAoChat(evento) {
  evento.preventDefault();
  const pergunta = elementos.campoPergunta.value.trim();
  const limiteFontes = Number(elementos.campoLimiteFontes.value || 4);
  if (pergunta.length < 3) {
    atualizarMensagem(elementos.mensagemChat, "Digite uma pergunta com pelo menos três caracteres.", "erro");
    return;
  }

  atualizarMensagem(elementos.mensagemChat, "Consultando o chat...");
  elementos.respostaChat.textContent = "Aguardando resposta...";
  elementos.fontesChat.textContent = "Aguardando fontes...";

  try {
    const dados = await requisitarJson("/chat/perguntar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        pergunta,
        limite_fontes: limiteFontes,
        conversation_id: obterConversationIdAtual(),
      }),
    });
    if (dados.conversation_id) {
      window.sessionStorage.setItem(CHAVE_CONVERSA_CHAT, dados.conversation_id);
    }
    elementos.respostaChat.textContent = dados.resposta;
    montarFontes(dados.fontes);
    atualizarMensagem(elementos.mensagemChat, "Resposta recebida com sucesso.", "sucesso");
  } catch (erro) {
    elementos.respostaChat.textContent = "Sem resposta.";
    elementos.fontesChat.textContent = "Nenhuma fonte retornada.";
    atualizarMensagem(elementos.mensagemChat, `Erro ao perguntar ao chat: ${erro.message}`, "erro");
  }
}

elementos.botaoVerificarSaude.addEventListener("click", verificarSaude);
elementos.formularioIngestao.addEventListener("submit", enviarDocumento);
elementos.formularioStatusDocumento.addEventListener("submit", atualizarStatusDocumento);
elementos.formularioExclusaoDocumento.addEventListener("submit", excluirDocumento);
elementos.formularioChat.addEventListener("submit", perguntarAoChat);
elementos.botaoNovaConversa.addEventListener("click", iniciarNovaConversa);
