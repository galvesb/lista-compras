from app.domain.exceptions.forbidden import ForbiddenError
from app.domain.exceptions.not_found import NotFoundError
from app.ports.repositories.list_repository import ListRepository


class DeleteListUC:
    """
    Use Case: excluir uma lista via soft delete.

    Camada de domínio — não conhece HTTP, WebSocket ou banco de dados.
    A autorização é feita em dois níveis:
      1. require_list_owner (infra): verifica membership + role no banco
      2. owner_id check (aqui): defense-in-depth, previne IDOR se o
         dependency de infra for contornado
    """

    def __init__(self, list_repo: ListRepository) -> None:
        self._list_repo = list_repo

    async def execute(self, list_id: str, current_user_id: str) -> None:
        lst = await self._list_repo.find_by_id(list_id)
        if not lst:
            raise NotFoundError("ShoppingList", list_id)

        # Defense-in-depth: valida ownership diretamente no domínio
        if lst.owner_id != current_user_id:
            raise ForbiddenError("Only the list owner can delete it")

        deleted = await self._list_repo.soft_delete(list_id)
        if not deleted:
            # Proteção contra race condition (outra requisição deletou primeiro)
            raise NotFoundError("ShoppingList", list_id)
