import re
import unicodedata
from dataclasses import dataclass

from app.infra.banco import PROJETO_PADRAO_NOME, PROJETO_PADRAO_SLUG
from app.repositories.repositorio_projetos import RepositorioProjetos

PADRAO_SEPARADORES = re.compile(r"[^a-z0-9]+")
PALAVRAS_GENERICAS_ARQUIVO = {
    "doc",
    "docs",
    "documentacao",
    "documentation",
    "manual",
    "readme",
    "guia",
    "guide",
    "arquitetura",
    "architecture",
    "tecnico",
    "tecnica",
    "technical",
}


class ErroProjetoInvalido(ValueError):
    pass


@dataclass(frozen=True)
class SugestaoProjeto:
    projeto_existente: object | None
    nome_sugerido: str | None
    slug_sugerido: str | None
    criterio: str


class ServicoProjetos:
    def __init__(self, repositorio: RepositorioProjetos):
        self._repositorio = repositorio

    def listar_projetos(self, limite: int = 100):
        return self._repositorio.listar_projetos(limite=limite)

    def buscar_por_id(self, projeto_id: int):
        return self._repositorio.buscar_projeto_por_id(projeto_id)

    def criar_projeto(self, nome: str, descricao: str | None = None):
        nome_normalizado = self._normalizar_nome(nome)
        slug = self._slugificar(nome_normalizado)
        projeto_existente = self._repositorio.buscar_projeto_por_slug(slug)
        if projeto_existente is not None:
            return projeto_existente
        return self._repositorio.criar_projeto(
            nome=nome_normalizado,
            slug=slug,
            descricao=descricao.strip() if descricao else None,
        )

    def resolver_projeto_upload(
        self,
        projeto_id: int | None,
        novo_projeto_nome: str | None,
    ):
        if projeto_id is not None and novo_projeto_nome:
            raise ErroProjetoInvalido(
                "Informe apenas um projeto existente ou um novo projeto."
            )

        if projeto_id is not None:
            projeto = self._repositorio.buscar_projeto_por_id(projeto_id)
            if projeto is None:
                raise ErroProjetoInvalido("Projeto informado nao foi encontrado.")
            return projeto

        if novo_projeto_nome:
            return self.criar_projeto(novo_projeto_nome)

        raise ErroProjetoInvalido("Projeto deve ser informado para a ingestao.")

    def sugerir_projeto(
        self,
        nome_arquivo: str,
        conteudo_texto: str | None = None,
    ) -> SugestaoProjeto:
        projetos = self._repositorio.listar_projetos(limite=200)
        if not projetos:
            nome_sugerido = self._derivar_nome_projeto(nome_arquivo, conteudo_texto)
            return SugestaoProjeto(
                projeto_existente=None,
                nome_sugerido=nome_sugerido,
                slug_sugerido=self._slugificar(nome_sugerido) if nome_sugerido else None,
                criterio="nome_arquivo",
            )

        melhor_projeto = None
        melhor_pontuacao = 0.0
        termos_arquivo = set(self._tokenizar_base_arquivo(nome_arquivo))
        termos_conteudo = set(self._tokenizar_texto(conteudo_texto or ""))

        for projeto in projetos:
            termos_projeto = set(self._tokenizar_texto(f"{projeto.nome} {projeto.slug}"))
            pontuacao = 0.0
            if termos_arquivo:
                pontuacao += len(termos_arquivo & termos_projeto) * 2
                if projeto.slug in self._slugificar(nome_arquivo):
                    pontuacao += 3
            if termos_conteudo:
                pontuacao += len(termos_conteudo & termos_projeto)
            if pontuacao > melhor_pontuacao:
                melhor_projeto = projeto
                melhor_pontuacao = pontuacao

        if melhor_projeto is not None and melhor_pontuacao > 0:
            return SugestaoProjeto(
                projeto_existente=melhor_projeto,
                nome_sugerido=melhor_projeto.nome,
                slug_sugerido=melhor_projeto.slug,
                criterio="projeto_existente",
            )

        nome_sugerido = self._derivar_nome_projeto(nome_arquivo, conteudo_texto)
        return SugestaoProjeto(
            projeto_existente=None,
            nome_sugerido=nome_sugerido,
            slug_sugerido=self._slugificar(nome_sugerido) if nome_sugerido else None,
            criterio="nome_arquivo",
        )

    def obter_ou_criar_projeto_padrao(self):
        projeto = self._repositorio.buscar_projeto_por_slug(PROJETO_PADRAO_SLUG)
        if projeto is not None:
            return projeto
        return self._repositorio.criar_projeto(
            nome=PROJETO_PADRAO_NOME,
            slug=PROJETO_PADRAO_SLUG,
        )

    @classmethod
    def _normalizar_nome(cls, nome: str) -> str:
        nome = " ".join(nome.strip().split())
        if len(nome) < 2:
            raise ErroProjetoInvalido("Nome do projeto deve ter pelo menos 2 caracteres.")
        return nome

    @classmethod
    def _slugificar(cls, texto: str) -> str:
        texto_normalizado = unicodedata.normalize("NFKD", texto)
        texto_ascii = texto_normalizado.encode("ascii", "ignore").decode("ascii")
        slug = PADRAO_SEPARADORES.sub("-", texto_ascii.lower()).strip("-")
        if len(slug) < 2:
            raise ErroProjetoInvalido("Nao foi possivel gerar slug valido para o projeto.")
        return slug

    @classmethod
    def _tokenizar_base_arquivo(cls, nome_arquivo: str) -> list[str]:
        base = nome_arquivo.rsplit(".", maxsplit=1)[0]
        tokens = cls._tokenizar_texto(base)
        return [token for token in tokens if token not in PALAVRAS_GENERICAS_ARQUIVO]

    @classmethod
    def _tokenizar_texto(cls, texto: str) -> list[str]:
        texto_normalizado = unicodedata.normalize("NFKD", texto)
        texto_ascii = texto_normalizado.encode("ascii", "ignore").decode("ascii")
        return [token for token in PADRAO_SEPARADORES.split(texto_ascii.lower()) if len(token) >= 3]

    @classmethod
    def _derivar_nome_projeto(
        cls,
        nome_arquivo: str,
        conteudo_texto: str | None = None,
    ) -> str:
        tokens = cls._tokenizar_base_arquivo(nome_arquivo)
        if not tokens and conteudo_texto:
            tokens = cls._tokenizar_texto(conteudo_texto)[:3]
        if not tokens:
            return PROJETO_PADRAO_NOME
        return " ".join(token.capitalize() for token in tokens[:3])
