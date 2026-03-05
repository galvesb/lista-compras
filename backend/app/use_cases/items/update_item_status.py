"""
UpdateItemStatusUC — fluxo mais complexo do sistema.

Responsabilidades:
- Validar permissão (membro da lista)
- Validar que o item pertence à lista
- Executar atualização atômica com optimistic locking
- Tratar conflito de versão (409)
- Limpar dados de check ao desmarcar
"""
from app.domain.entities.list_item import ListItem
from app.domain.exceptions.conflict import ConflictError
from app.domain.exceptions.forbidden import ForbiddenError
from app.domain.exceptions.not_found import NotFoundError
from app.domain.value_objects.item_status import ItemStatus
from app.ports.repositories.item_repository import ItemRepository
from app.ports.repositories.member_repository import MemberRepository


class UpdateItemStatusUC:
    def __init__(self, item_repo: ItemRepository, member_repo: MemberRepository) -> None:
        self._item_repo = item_repo
        self._member_repo = member_repo

    async def execute(
        self,
        list_id: str,
        item_id: str,
        expected_version: int,
        new_status: ItemStatus | None,
        price: float | None,
        current_user_id: str,
    ) -> ListItem:
        # 1. Verify membership
        membership = await self._member_repo.find(list_id, current_user_id)
        if not membership:
            raise ForbiddenError("User is not a member of this list")

        # 2. Verify item exists and belongs to this list
        item = await self._item_repo.find_by_id(item_id)
        if not item or item.list_id != list_id:
            raise NotFoundError("ListItem", item_id)

        # 3. Determine mutation intent
        is_checking = new_status == ItemStatus.CHECKED
        is_unchecking = new_status in (ItemStatus.PENDING, ItemStatus.UNAVAILABLE) and item.status == ItemStatus.CHECKED

        # 4. Atomic update with version guard
        updated = await self._item_repo.update_with_version(
            item_id=item_id,
            expected_version=expected_version,
            status=new_status,
            price=price if is_checking else None,
            clear_price=is_unchecking,
            checked_by_user_id=current_user_id if is_checking else None,
            clear_checked_by=is_unchecking,
        )

        if updated is None:
            # Version mismatch — fetch current version for client to retry
            current = await self._item_repo.find_by_id(item_id)
            current_version = current.version if current else expected_version
            raise ConflictError("ListItem", current_version)

        return updated
