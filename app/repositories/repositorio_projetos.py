from app.infra.modelos_orm import ProjetoORM


class RepositorioProjetos:
    def __init__(self, sessao):
        self.sessao = sessao

    def listar_projetos(self, limite: int = 100) -> list[ProjetoORM]:
        return (
            self.sessao.query(ProjetoORM)
            .order_by(ProjetoORM.nome.asc(), ProjetoORM.id.asc())
            .limit(limite)
            .all()
        )

    def buscar_projeto_por_id(self, projeto_id: int) -> ProjetoORM | None:
        return self.sessao.get(ProjetoORM, projeto_id)

    def buscar_projeto_por_slug(self, slug: str) -> ProjetoORM | None:
        return (
            self.sessao.query(ProjetoORM)
            .filter(ProjetoORM.slug == slug)
            .first()
        )

    def criar_projeto(
        self,
        nome: str,
        slug: str,
        descricao: str | None = None,
    ) -> ProjetoORM:
        projeto = ProjetoORM(nome=nome, slug=slug, descricao=descricao)
        self.sessao.add(projeto)
        self.sessao.commit()
        self.sessao.refresh(projeto)
        return projeto
