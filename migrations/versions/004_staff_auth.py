"""Personel hesapları, iptal edilebilir oturumlar ve işlem sorumluluğu."""
from alembic import op

revision = '004_staff_auth'
down_revision = '003_inventory'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('''CREATE TABLE staff_accounts (
        id BIGSERIAL PRIMARY KEY,
        username TEXT NOT NULL UNIQUE CHECK (username ~ '^[a-z0-9_.-]{3,50}$'),
        name TEXT NOT NULL CHECK (length(name) BETWEEN 1 AND 100),
        role TEXT NOT NULL CHECK (role IN ('admin','cashier','waiter','kitchen')),
        password_hash TEXT NOT NULL,
        is_active BOOLEAN NOT NULL DEFAULT true,
        version BIGINT NOT NULL DEFAULT 0,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )''')
    op.execute('''CREATE TABLE staff_sessions (
        token_hash TEXT PRIMARY KEY,
        staff_id BIGINT NOT NULL REFERENCES staff_accounts(id),
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        expires_at TIMESTAMPTZ NOT NULL
    )''')
    op.execute('CREATE INDEX ON staff_sessions(staff_id)')
    op.execute('''CREATE TABLE login_attempts (
        id BIGSERIAL PRIMARY KEY,
        username TEXT NOT NULL,
        success BOOLEAN NOT NULL DEFAULT false,
        attempted_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )''')
    op.execute('CREATE INDEX ON login_attempts(attempted_at)')
    op.execute('CREATE INDEX ON login_attempts(username,attempted_at)')
    op.execute('''CREATE TABLE staff_audit (
        id BIGSERIAL PRIMARY KEY,
        actor_id BIGINT REFERENCES staff_accounts(id),
        action TEXT NOT NULL,
        resource TEXT NOT NULL,
        request_key TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )''')


def downgrade():
    raise RuntimeError('Personel ve işlem geçmişi otomatik silinmez; kontrollü geri dönüş gerekir.')
