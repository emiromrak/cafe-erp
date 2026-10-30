"""Kesin hassasiyetli stoklar, sürümlü reçeteler ve stok hareket defteri."""
from alembic import op

revision = '003_inventory'
down_revision = '002_tabs_payments'
branch_labels = None
depends_on = None


def upgrade():
    """Mevcut stokları açılış bakiyesiyle korur; geçmiş satışlara tüketim üretmez."""
    op.execute("""DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM raw_materials WHERE
            current_stock IS NULL OR min_alert IS NULL OR cost IS NULL OR unit IS NULL OR
            current_stock < 0 OR min_alert < 0 OR cost < 0 OR
            current_stock::text IN ('NaN','Infinity','-Infinity') OR
            min_alert::text IN ('NaN','Infinity','-Infinity') OR
            cost::text IN ('NaN','Infinity','-Infinity')) THEN
            RAISE EXCEPTION 'Geçersiz hammadde stok/eşik/maliyet/birim kaydı; önce veriyi düzeltin.';
        END IF;
    END $$""")
    for column in ('current_stock', 'min_alert', 'cost'):
        op.execute(f'ALTER TABLE raw_materials ALTER COLUMN {column} TYPE NUMERIC(20,6) USING round({column}::numeric,6)')
        op.execute(f'ALTER TABLE raw_materials ALTER COLUMN {column} SET NOT NULL')
        op.execute(f"ALTER TABLE raw_materials ADD CHECK ({column} >= 0 AND {column} < 'Infinity'::numeric)")
    op.execute('ALTER TABLE raw_materials ALTER COLUMN unit SET NOT NULL')
    op.execute("""CREATE TABLE product_recipes (
        product_id TEXT PRIMARY KEY REFERENCES products(id),
        version BIGINT NOT NULL CHECK (version > 0),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )""")
    op.execute("""CREATE TABLE recipe_lines (
        product_id TEXT NOT NULL REFERENCES product_recipes(product_id),
        material_id TEXT NOT NULL REFERENCES raw_materials(id),
        quantity NUMERIC(20,6) NOT NULL CHECK (quantity > 0 AND quantity < 'Infinity'::numeric),
        PRIMARY KEY (product_id,material_id)
    )""")
    op.execute("""CREATE TABLE recipe_history (
        product_id TEXT NOT NULL REFERENCES products(id), version BIGINT NOT NULL,
        lines JSONB NOT NULL, reason TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        PRIMARY KEY (product_id,version)
    )""")
    op.execute("""CREATE TABLE item_materials (
        item_id BIGINT NOT NULL REFERENCES tab_items(id),
        material_id TEXT NOT NULL REFERENCES raw_materials(id),
        recipe_version BIGINT NOT NULL, unit TEXT NOT NULL,
        quantity_per_unit NUMERIC(20,6) NOT NULL CHECK (quantity_per_unit > 0),
        quantity NUMERIC(20,6) NOT NULL CHECK (quantity > 0),
        disposition TEXT NOT NULL DEFAULT 'consumed' CHECK (disposition IN ('consumed','waste')),
        PRIMARY KEY (item_id,material_id)
    )""")
    op.execute("""CREATE TABLE stock_movements (
        id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        material_id TEXT NOT NULL REFERENCES raw_materials(id),
        item_id BIGINT REFERENCES tab_items(id),
        kind TEXT NOT NULL CHECK (kind IN ('opening','receipt','return','waste','staff','complimentary','consume')),
        quantity NUMERIC(20,6) NOT NULL CHECK (quantity <> 0 AND abs(quantity) < 'Infinity'::numeric),
        balance_after NUMERIC(20,6) NOT NULL CHECK (balance_after >= 0 AND balance_after < 'Infinity'::numeric),
        unit TEXT NOT NULL, reason TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        CHECK ((kind IN ('opening','receipt','return') AND quantity > 0) OR
               (kind IN ('waste','staff','complimentary','consume') AND quantity < 0)),
        CHECK ((kind='consume') = (item_id IS NOT NULL))
    )""")
    op.execute("CREATE UNIQUE INDEX one_item_consumption ON stock_movements(item_id,material_id) WHERE kind='consume'")
    op.execute('CREATE INDEX material_movements ON stock_movements(material_id,id)')
    op.execute("""INSERT INTO stock_movements(material_id,kind,quantity,balance_after,unit,reason)
        SELECT id,'opening',current_stock,current_stock,unit,'Stok motoruna geçiş açılış bakiyesi'
        FROM raw_materials WHERE current_stock > 0""")
    # Mevcut hazırlanmış açık kalemler için geçmişe dönük varsayımsal tüketim yapılmaz.
    op.execute('ALTER TABLE tab_items ADD COLUMN inventory_legacy BOOLEAN NOT NULL DEFAULT FALSE')
    op.execute("UPDATE tab_items SET inventory_legacy=TRUE WHERE status IN ('preparing','ready')")


def downgrade():
    """Hareket ve reçete geçmişinin silinmesini engeller."""
    raise RuntimeError('Veri kaybını önlemek için otomatik geri alma desteklenmiyor.')
