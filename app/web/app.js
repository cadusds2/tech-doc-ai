const selecionar = (seletor) => document.querySelector(seletor);

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
  formularioChat: selecionar("#formulario-chat"),
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
    const detalhe = dados.detail || dados.mensagem || "Falha ao consultar a API.";
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
  const arquivo = elementos.arquivoDocumento.files[0];
  if (!arquivo) {
    atualizarMensagem(elementos.mensagemIngestao, "Selecione um arquivo antes de enviar.", "erro");
    return;
  }

  const dadosFormulario = new FormData();
  dadosFormulario.append("arquivo", arquivo);
  atualizarMensagem(elementos.mensagemIngestao, "Enviando documento para ingestão...");

  try {
    const dados = await requisitarJson("/documentos/ingestao", {
      method: "POST",
      body: dadosFormulario,
    });
    elementos.documentoIdAtual.textContent = dados.documento_id;
    elementos.campoDocumentoId.value = dados.documento_id;
    elementos.saidaIngestao.textContent = formatarJson(dados);
    atualizarMensagem(elementos.mensagemIngestao, "Documento enviado com sucesso.", "sucesso");
  } catch (erro) {
    elementos.saidaIngestao.textContent = "";
    atualizarMensagem(elementos.mensagemIngestao, `Erro na ingestão: ${erro.message}`, "erro");
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
      body: JSON.stringify({ pergunta, limite_fontes: limiteFontes }),
    });
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
elementos.formularioChat.addEventListener("submit", perguntarAoChat);
