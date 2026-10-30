"""Adisyon kalemleri, işlem geçmişi ve tek seferlik ödeme kayıtları."""
from alembic import op

revision = '002_tabs_payments'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade():
    """Geçmiş satışları değiştirmeden yeni işlem tablolarını ekler."""
    op.execute("ALTER TABLE open_tabs ADD COLUMN version BIGINT NOT NULL DEFAULT 0 CHECK (version >= 0)")
    op.execute("ALTER TABLE open_tabs ADD COLUMN status TEXT NOT NULL DEFAULT 'open'")
    op.execute("UPDATE open_tabs SET status = 'closed' WHERE closed_at IS NOT NULL")
    op.execute("""ALTER TABLE open_tabs ADD CONSTRAINT tab_closure_state CHECK (
        (status = 'open' AND closed_at IS NULL) OR
        (status IN ('paid', 'cancelled', 'closed') AND closed_at IS NOT NULL))""")
    op.execute("""CREATE TABLE tab_items (
        id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        tab_id BIGINT NOT NULL REFERENCES open_tabs(id),
        product_id TEXT NOT NULL REFERENCES products(id),
        product_name TEXT NOT NULL,
        quantity INTEGER NOT NULL CHECK (quantity BETWEEN 1 AND 10000),
        unit_price_cents BIGINT NOT NULL CHECK (unit_price_cents BETWEEN 0 AND 999999999999),
        status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','sent','preparing','ready','cancelled')),
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        CHECK (quantity::numeric * unit_price_cents <= 999999999999)
    )""")
    op.execute('CREATE INDEX tab_items_tab ON tab_items(tab_id, id)')
    op.execute("""CREATE TABLE tab_payments (
        id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        tab_id BIGINT NOT NULL UNIQUE REFERENCES open_tabs(id),
        order_id TEXT NOT NULL UNIQUE REFERENCES orders(order_id),
        amount_cents BIGINT NOT NULL CHECK (amount_cents BETWEEN 1 AND 999999999999),
        method TEXT NOT NULL CHECK (method IN ('cash','card')),
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""")
    op.execute("""CREATE TABLE tab_events (
        id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        tab_id BIGINT NOT NULL REFERENCES open_tabs(id),
        event_type TEXT NOT NULL,
        data JSONB NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""")
    op.execute('CREATE INDEX tab_events_tab ON tab_events(tab_id, id)')
    op.execute("""CREATE TABLE api_requests (
        key VARCHAR(128) PRIMARY KEY,
        request_hash TEXT NOT NULL,
        response JSONB NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""")


def downgrade():
    """Ödeme geçmişinin yanlışlıkla silinmesini önler."""
    raise RuntimeError('Veri kaybını önlemek için otomatik geri alma desteklenmiyor.')
