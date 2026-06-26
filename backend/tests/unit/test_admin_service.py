from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from app.schemas.admin import ConversationListItem
from app.services.admin_service import AdminService


def _item(name):
    return ConversationListItem(
        conversation_id=uuid4(),
        started_at=datetime(2026, 6, 26, tzinfo=timezone.utc),
        channel="api",
        status="open",
        assigned_to_human=False,
        lead_id=uuid4(),
        lead_name=name,
        lead_city="Natal",
        average_energy_bill=Decimal("450.00"),
        lead_score=72,
        lead_temperature="warm",
    )


class _Repo:
    def __init__(self, items, total):
        self._items = items
        self._total = total
        self.calls = []

    def list_with_lead(self, limit, offset):
        self.calls.append((limit, offset))
        return self._items

    def count_all(self):
        return self._total


def _service(items, total):
    svc = AdminService(None)
    svc.conversation_repository = _Repo(items, total)
    return svc


def test_lists_items_with_total():
    svc = _service([_item("Ana"), _item("Bia")], total=2)
    res = svc.list_conversations(limit=50, offset=0)
    assert res.total == 2
    assert [i.lead_name for i in res.items] == ["Ana", "Bia"]
    assert res.limit == 50 and res.offset == 0


def test_clamps_limit_and_offset():
    svc = _service([], total=0)
    svc.list_conversations(limit=9999, offset=-5)
    # repo received clamped values: limit<=100, offset>=0
    assert svc.conversation_repository.calls == [(100, 0)]


def test_minimum_limit_is_one():
    svc = _service([], total=0)
    svc.list_conversations(limit=0, offset=0)
    assert svc.conversation_repository.calls == [(1, 0)]
