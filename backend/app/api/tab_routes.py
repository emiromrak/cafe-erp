"""Adisyon REST sözleşmesi; tüm yazmalarda tekrar anahtarı zorunludur."""
from typing import Annotated, Literal

from fastapi import APIRouter, Header, Path, Query
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from sqlalchemy import text

from app.ai import decision_engine
from app import tab_service

router = APIRouter(prefix='/api', tags=['Adisyon ve ödeme'])
Key = Annotated[str, Header(alias='Idempotency-Key', min_length=1, max_length=128, pattern=r'^[A-Za-z0-9_.:-]+$')]
Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
PositiveId = Annotated[int, Path(gt=0, le=9223372036854775807)]
Quantity = Annotated[int, Field(strict=True, ge=1, le=10000)]


class Request(BaseModel):
    """Yanlış alanların sessizce yok sayılmasını engeller."""
    model_config = ConfigDict(extra='forbid')


class OpenTab(Request):
    """Açılacak masanın kimliği."""
    table_id: Identifier


class Versioned(Request):
    """Eski ekranın güncel adisyonu ezmesini engelleyen sürüm."""
    expected_version: Annotated[int, Field(strict=True, ge=0, le=9223372036854775806)]


class AddItem(Versioned):
    """Fiyat istemciden alınmaz; ürün kaydından okunur."""
    product_id: Identifier
    quantity: Quantity


class ChangeQuantity(Versioned):
    """Taslak kalemin yeni miktarı."""
    quantity: Quantity


class ItemStatus(Versioned):
    """Mutfaktaki ardışık hazırlık adımları."""
    status: Literal['preparing', 'ready']


class Cancel(Versioned):
    """İptal gerekçesi işlem geçmişinde korunur."""
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class Payment(Versioned):
    """Harici cihazda alınan tam ödemenin uygulama kaydı."""
    amount_cents: Annotated[int, Field(strict=True, ge=1, le=tab_service.MAX_CENTS)]
    method: Literal['cash', 'card']


def command(key, operation, body, tab_id=None, item_id=None):
    """Doğrulanmış gövdeyi ortak atomik işlem servisine aktarır."""
    return tab_service.execute(decision_engine._engine(), key, operation, body.model_dump(), tab_id, item_id)


@router.post('/tabs', summary='Masa için adisyon aç')
def open_tab(body: OpenTab, key: Key):
    return command(key, 'open', body)


@router.get('/tabs', summary='Açık adisyonları listele')
def list_tabs(table_id: Annotated[str | None, Query(max_length=200)] = None):
    with decision_engine._engine().connect() as conn:
        return [dict(r) for r in conn.execute(text('''SELECT * FROM open_tabs
            WHERE closed_at IS NULL AND (CAST(:table AS text) IS NULL OR table_id=:table)
            ORDER BY id'''), {'table': table_id}).mappings()]


@router.get('/kitchen/items', summary='Açık adisyonlardaki mutfak kalemleri')
def kitchen_items():
    with decision_engine._engine().connect() as conn:
        return [dict(r) for r in conn.execute(text('''SELECT i.*, t.table_id, t.version,
            d.name AS table_name FROM tab_items i JOIN open_tabs t ON t.id=i.tab_id
            JOIN dining_tables d ON d.id=t.table_id
            WHERE t.closed_at IS NULL AND i.status IN ('sent','preparing','ready')
            ORDER BY i.id''')).mappings()]


@router.get('/tabs/{tab_id}', summary='Adisyon, kalemler ve güncel toplam')
def get_tab(tab_id: PositiveId):
    return tab_service.read_tab(decision_engine._engine(), tab_id)


@router.get('/tabs/{tab_id}/events', summary='Adisyon işlem geçmişi')
def tab_events(tab_id: PositiveId):
    with decision_engine._engine().connect() as conn:
        if tab_service.row(conn, 'SELECT id FROM open_tabs WHERE id=:id', id=tab_id) is None:
            tab_service.fail('Adisyon bulunamadı.', 404)
        return [dict(r) for r in conn.execute(text(
            'SELECT * FROM tab_events WHERE tab_id=:id ORDER BY id'), {'id': tab_id}).mappings()]


@router.post('/tabs/{tab_id}/items', summary='Adisyona ürün ekle')
def add_item(tab_id: PositiveId, body: AddItem, key: Key):
    return command(key, 'add_item', body, tab_id)


@router.patch('/tabs/{tab_id}/items/{item_id}', summary='Taslak kalem miktarını değiştir')
def change_quantity(tab_id: PositiveId, item_id: PositiveId, body: ChangeQuantity, key: Key):
    return command(key, 'quantity', body, tab_id, item_id)


@router.post('/tabs/{tab_id}/items/{item_id}/cancel', summary='Gerekçeli kalem iptali')
def cancel_item(tab_id: PositiveId, item_id: PositiveId, body: Cancel, key: Key):
    return command(key, 'cancel_item', body, tab_id, item_id)


@router.post('/tabs/{tab_id}/submit', summary='Taslak kalemleri mutfağa gönder')
def submit(tab_id: PositiveId, body: Versioned, key: Key):
    return command(key, 'submit', body, tab_id)


@router.patch('/tabs/{tab_id}/items/{item_id}/status', summary='Hazırlık durumunu ilerlet')
def item_status(tab_id: PositiveId, item_id: PositiveId, body: ItemStatus, key: Key):
    return command(key, 'item_status', body, tab_id, item_id)


@router.post('/tabs/{tab_id}/payments', summary='Tam ödeme kaydet ve adisyonu kapat')
def pay(tab_id: PositiveId, body: Payment, key: Key):
    return command(key, 'pay', body, tab_id)


@router.post('/tabs/{tab_id}/cancel', summary='Gerekçeli adisyon iptali')
def cancel_tab(tab_id: PositiveId, body: Cancel, key: Key):
    return command(key, 'cancel_tab', body, tab_id)
