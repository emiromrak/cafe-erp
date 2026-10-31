"""Gerçek PostgreSQL üzerinde adisyon, tahsilat ve eşzamanlılık testleri."""
import sys
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from threading import Barrier
from unittest.mock import patch
from zoneinfo import ZoneInfo

from alembic import command
from alembic.config import Config
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from app import tab_service
from app.ai import decision_engine
from app.api import catalog_routes
from app.database import get_engine
from app.main import app
from app.auth import token_hash, COOKIE


class TabFixture(unittest.TestCase):
    def setUp(self):
        self.admin = get_engine()
        self.schema = 'test_tabs_' + uuid.uuid4().hex
        self.engine = create_engine(self.admin.url, connect_args={'options': f'-csearch_path={self.schema}'})
        self.addCleanup(self.cleanup_database)
        with self.admin.begin() as conn:
            conn.execute(text(f'CREATE SCHEMA {self.schema}'))
        self.config = Config(str(ROOT / 'alembic.ini'))
        self.config.set_main_option('script_location', str(ROOT / 'migrations'))
        self.upgrade('001_initial')
        # Eski açık/kapalı adisyonlar ve satış, yeni geçişten sonra da korunmalı.
        with self.engine.begin() as conn:
            conn.execute(text("INSERT INTO categories VALUES ('c','İçecekler',1)"))
            conn.execute(text("INSERT INTO products VALUES ('tea','c','Çay',25.35,'tea'), ('free','c','İkram',0,'tea')"))
            conn.execute(text("INSERT INTO dining_tables VALUES ('t1','Masa 1','Salon'),('t2','Masa 2','Salon'),('legacy','Eski','Salon')"))
            conn.execute(text("INSERT INTO open_tabs(table_id,closed_at) VALUES ('legacy',now())"))
            conn.execute(text("INSERT INTO orders(order_id,timestamp,total_amount,payment_method) VALUES ('old','2020-01-01 08:00:00',12.50,'Nakit')"))
        self.upgrade('head')
        with self.engine.begin() as conn:
            conn.execute(text("""INSERT INTO raw_materials
                (id,name,category,unit,current_stock,min_alert,cost)
                VALUES ('leaf','Çay yaprağı','Çay','gram',100000,10,1)"""))
            conn.execute(text("""INSERT INTO stock_movements(material_id,kind,quantity,balance_after,unit,reason)
                VALUES ('leaf','opening',100000,100000,'gram','Test açılışı')"""))
            conn.execute(text("INSERT INTO product_recipes(product_id,version) VALUES ('tea',1),('free',1)"))
            conn.execute(text("INSERT INTO recipe_lines VALUES ('tea','leaf',3),('free','leaf',3)"))
        for module in (decision_engine, catalog_routes):
            patcher = patch.object(module, '_engine', return_value=self.engine)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.client = TestClient(app)
        self.client.headers['X-CafeERP-Request'] = '1'
        token = uuid.uuid4().hex
        with self.engine.begin() as conn:
            account_id = conn.execute(text("""INSERT INTO staff_accounts(username,name,role,password_hash)
                VALUES ('testadmin','Test yöneticisi','admin','unusable') RETURNING id""")).scalar_one()
            conn.execute(text("""INSERT INTO staff_sessions(token_hash,staff_id,expires_at)
                VALUES (:token,:id,now()+interval '12 hours')"""), {'token':token_hash(token),'id':account_id})
        self.client.cookies.set(COOKIE, token)
        self.addCleanup(self.client.close)

    def upgrade(self, revision):
        with self.engine.begin() as conn:
            self.config.attributes['connection'] = conn
            command.upgrade(self.config, revision)

    def cleanup_database(self):
        self.engine.dispose()
        with self.admin.begin() as conn:
            conn.execute(text(f'DROP SCHEMA IF EXISTS {self.schema} CASCADE'))
        self.admin.dispose()

    def send(self, path, body, key=None, method='post', expected=200):
        response = getattr(self.client, method)(path, json=body, headers={'Idempotency-Key': key or uuid.uuid4().hex})
        self.assertEqual(response.status_code, expected, response.text)
        return response.json()

    def open(self, table='t1', key=None):
        return self.send('/api/tabs', {'table_id': table}, key)

    def add(self, tab, quantity=2, key=None):
        return self.send(f"/api/tabs/{tab['id']}/items", {'expected_version': tab['version'], 'product_id': 'tea', 'quantity': quantity}, key)

    def ready(self, tab):
        tab = self.send(f"/api/tabs/{tab['id']}/submit", {'expected_version': tab['version']})
        for item in tab['items']:
            if item['status'] == 'cancelled':
                continue
            for status in ('preparing', 'ready'):
                tab = self.send(f"/api/tabs/{tab['id']}/items/{item['id']}/status",
                                {'expected_version': tab['version'], 'status': status}, method='patch')
        return tab

class TabTests(TabFixture):
    def test_migration_preserves_legacy_data_and_is_repeatable(self):
        self.upgrade('head')
        with self.engine.connect() as conn:
            self.assertEqual(conn.execute(text('SELECT version_num FROM alembic_version')).scalar(), '004_staff_auth')
            self.assertEqual(conn.execute(text('SELECT status FROM open_tabs')).scalar(), 'closed')
            self.assertEqual(str(conn.execute(text('SELECT total_amount FROM orders')).scalar()), '12.50')

    def test_full_payment_reconciles_snapshot_report_and_table(self):
        tab = self.add(self.open())
        self.assertEqual(tab['total_cents'], 5070)
        with self.engine.begin() as conn:
            conn.execute(text("UPDATE products SET price=99,name='Yeni ad' WHERE id='tea'"))
        tab = self.ready(tab)
        self.assertEqual(tab['items'][0]['product_name'], 'Çay')
        self.assertEqual(len(self.client.get('/api/kitchen/items').json()), 1)
        body = {'expected_version': tab['version'], 'amount_cents': 5070, 'method': 'card'}
        url = f"/api/tabs/{tab['id']}/payments"
        paid = self.send(url, body, 'payment-1')
        self.assertEqual(paid, self.send(url, body, 'payment-1'))
        self.send(url, body, 'payment-2', expected=409)
        self.assertEqual(paid['status'], 'paid')
        self.assertEqual(paid['payment']['amount_cents'], 5070)
        self.assertEqual(self.client.get(f"/api/tabs/{tab['id']}").json(), paid)
        self.assertEqual(self.client.get('/api/kitchen/items').json(), [])
        self.assertEqual(self.client.get('/api/tabs').json(), [])
        tables = {t['id']: t['status'] for t in self.client.get('/api/tables').json()}
        self.assertEqual(tables['t1'], 'empty')
        day = datetime.now(ZoneInfo('Europe/Istanbul')).strftime('%Y-%m-%d')
        report = self.client.get('/api/ai/sales-summary', params={'date': day}).json()
        self.assertEqual(report['stats']['total_orders'], 1)
        self.assertEqual(report['stats']['total_revenue'], 50.70)
        self.assertEqual(report['stats']['card_revenue'], 50.70)
        self.assertEqual(report['top_items'][0]['total_qty'], 2)
        self.assertEqual(report['top_items'][0]['product_rev'], 50.70)
        events = self.client.get(f"/api/tabs/{tab['id']}/events").json()
        self.assertEqual([e['event_type'] for e in events], ['opened','add_item','submit','item_status','item_status','pay'])
        self.assertEqual(events[1]['data']['item_id'], paid['items'][0]['id'])
        self.assertEqual(events[1]['data']['unit_price_cents'], 2535)
        self.assertEqual(events[2]['data']['item_ids'], [paid['items'][0]['id']])
        self.assertNotEqual(self.open()['id'], tab['id'])

    def test_idempotency_replay_conflict_and_version_guard(self):
        tab = self.open(key='open-1')
        self.assertEqual(self.open(key='open-1'), tab)
        self.send('/api/tabs', {'table_id': 't2'}, 'open-1', expected=409)
        self.send('/api/tabs', {'table_id': 't1'}, expected=409)
        added = self.add(tab, key='item-1')
        self.assertEqual(self.add(tab, key='item-1'), added)
        self.send(f"/api/tabs/{tab['id']}/items", {'expected_version': 0, 'product_id':'tea','quantity':3}, 'item-1', expected=409)
        self.send(f"/api/tabs/{tab['id']}/items", {'expected_version':0,'product_id':'tea','quantity':2}, expected=409)
        self.assertEqual(len(self.client.get(f"/api/tabs/{tab['id']}").json()['items']), 1)

    def test_quantity_cancellation_and_empty_tab_closure(self):
        tab = self.add(self.open())
        item = tab['items'][0]['id']
        url = f"/api/tabs/{tab['id']}"
        tab = self.send(f'{url}/items/{item}', {'expected_version':tab['version'],'quantity':3}, method='patch')
        self.assertEqual(tab['total_cents'], 7605)
        tab = self.send(f'{url}/items/{item}/cancel', {'expected_version':tab['version'],'reason':'Yanlış ürün'})
        self.assertEqual(tab['total_cents'], 0)
        self.send(f'{url}/payments', {'expected_version':tab['version'],'amount_cents':1,'method':'cash'}, expected=409)
        cancelled = self.send(f'{url}/cancel', {'expected_version':tab['version'],'reason':'Müşteri ayrıldı'})
        self.assertEqual(cancelled['status'], 'cancelled')
        self.send(f'{url}/items', {'expected_version':cancelled['version'],'product_id':'tea','quantity':1}, expected=409)
        events = self.client.get(f'{url}/events').json()
        self.assertEqual(events[-2]['data']['reason'], 'Yanlış ürün')
        self.assertEqual(events[-1]['data']['reason'], 'Müşteri ayrıldı')
        with self.engine.connect() as conn:
            self.assertEqual(conn.execute(text('SELECT COUNT(*) FROM tab_payments')).scalar(), 0)
            self.assertEqual(conn.execute(text('SELECT COUNT(*) FROM orders')).scalar(), 1)

    def test_invalid_transitions_and_amount_do_not_mutate(self):
        tab = self.add(self.open())
        base = f"/api/tabs/{tab['id']}"
        item = tab['items'][0]['id']
        self.send(f'{base}/items/{item}/status', {'expected_version':1,'status':'ready'}, method='patch', expected=409)
        self.send(f'{base}/payments', {'expected_version':1,'amount_cents':5070,'method':'cash'}, expected=409)
        tab = self.send(f'{base}/submit', {'expected_version':1})
        self.send(f'{base}/items/{item}', {'expected_version':2,'quantity':3}, method='patch', expected=409)
        self.send(f'{base}/submit', {'expected_version':2}, expected=409)
        for state in ('preparing','ready'):
            tab = self.send(f'{base}/items/{item}/status', {'expected_version':tab['version'],'status':state}, method='patch')
        self.send(f'{base}/payments', {'expected_version':tab['version'],'amount_cents':5071,'method':'cash'}, expected=409)
        self.assertEqual(self.client.get(base).json(), tab)
        paid = self.send(f'{base}/payments', {'expected_version':tab['version'],'amount_cents':5070,'method':'cash'})
        self.assertEqual(paid['payment']['method'], 'cash')

    def test_validation_missing_records_and_cross_tab_item(self):
        self.assertEqual(self.client.post('/api/tabs', json={'table_id':'t1'}).status_code, 422)
        self.send('/api/tabs', {'table_id':'missing'}, expected=404)
        tab = self.open()
        base = f"/api/tabs/{tab['id']}"
        for quantity in (0,-1,1.5,True,'2',10001):
            self.send(f'{base}/items', {'expected_version':0,'product_id':'tea','quantity':quantity}, expected=422)
        self.send(f'{base}/items', {'expected_version':0,'product_id':'tea','quantity':1,'unit_price_cents':1}, expected=422)
        self.send(f'{base}/items', {'expected_version':0,'product_id':'missing','quantity':1}, expected=404)
        self.send(f'{base}/cancel', {'expected_version':0,'reason':'  '}, expected=422)
        other = self.add(self.open('t2'))
        self.send(f"{base}/items/{other['items'][0]['id']}/cancel", {'expected_version':0,'reason':'Hata'}, expected=404)
        self.assertEqual(self.client.get('/api/tabs/999999').status_code, 404)
        self.assertEqual(self.client.get('/api/tabs/999999/events').status_code, 404)
        self.assertEqual(self.client.get('/api/tabs/999999999999999999999999').status_code, 422)

    def test_total_limit_rolls_back_item_and_request(self):
        with self.engine.begin() as conn:
            conn.execute(text("UPDATE products SET price=9999999999.99 WHERE id='tea'"))
        tab = self.add(self.open(), quantity=1)
        body = {'expected_version':tab['version'],'product_id':'tea','quantity':1}
        self.send(f"/api/tabs/{tab['id']}/items", body, 'too-large', expected=422)
        current = self.client.get(f"/api/tabs/{tab['id']}").json()
        self.assertEqual(current, tab)
        with self.engine.connect() as conn:
            self.assertEqual(conn.execute(text("SELECT COUNT(*) FROM api_requests WHERE key='too-large'")).scalar(), 0)

    def test_payment_failure_rolls_back_sale_payment_event_and_closure(self):
        tab = self.ready(self.add(self.open()))
        original = tab_service.record_event
        def fail_payment(conn, tab_id, kind, data):
            if kind == 'pay':
                raise RuntimeError('Ödeme kayıt hatası')
            return original(conn, tab_id, kind, data)
        payload = {'expected_version':tab['version'],'amount_cents':5070,'method':'cash'}
        with patch.object(tab_service, 'record_event', side_effect=fail_payment):
            with self.assertRaisesRegex(RuntimeError, 'Ödeme kayıt hatası'):
                tab_service.execute(self.engine, 'retry-payment', 'pay', payload, tab['id'])
        self.assertEqual(self.client.get(f"/api/tabs/{tab['id']}").json(), tab)
        with self.engine.connect() as conn:
            self.assertEqual(conn.execute(text('SELECT COUNT(*) FROM orders')).scalar(), 1)
            self.assertEqual(conn.execute(text('SELECT COUNT(*) FROM order_items')).scalar(), 0)
            self.assertEqual(conn.execute(text('SELECT COUNT(*) FROM tab_payments')).scalar(), 0)
        result = self.send(f"/api/tabs/{tab['id']}/payments", payload, 'retry-payment')
        self.assertEqual(result['status'], 'paid')

    def race(self, jobs):
        """İki bağımsız bağlantıdan aynı anda başlayan işlemleri yarıştırır."""
        barrier = Barrier(len(jobs))
        def run(args):
            barrier.wait(timeout=10)
            try:
                return tab_service.execute(self.engine, *args)
            except HTTPException as exc:
                return exc.status_code
        with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
            return list(pool.map(run, jobs))

    def test_concurrent_open_and_add_are_serialized(self):
        result = self.race([('o1','open',{'table_id':'t1'}), ('o2','open',{'table_id':'t1'})])
        self.assertEqual(sum(isinstance(r, dict) for r in result), 1)
        self.assertIn(409, result)
        tab = next(r for r in result if isinstance(r, dict))
        body = {'expected_version':0,'product_id':'tea','quantity':1}
        added = self.race([('a1','add_item',body,tab['id']), ('a2','add_item',body,tab['id'])])
        self.assertEqual(sum(isinstance(r, dict) for r in added), 1)
        self.assertIn(409, added)
        self.assertEqual(len(self.client.get(f"/api/tabs/{tab['id']}").json()['items']), 1)

    def test_concurrent_same_key_and_payment_record_once(self):
        result = self.race([('same-open','open',{'table_id':'t1'})] * 2)
        self.assertEqual(result[0], result[1])
        tab = self.ready(self.add(result[0]))
        body = {'expected_version':tab['version'],'amount_cents':5070,'method':'cash'}
        result = self.race([('same-pay','pay',body,tab['id'])] * 2)
        self.assertEqual(result[0], result[1])
        with self.engine.connect() as conn:
            self.assertEqual(conn.execute(text('SELECT COUNT(*) FROM tab_payments')).scalar(), 1)
            self.assertEqual(conn.execute(text('SELECT COUNT(*) FROM orders')).scalar(), 2)

    def test_concurrent_different_payments_and_edit_vs_payment(self):
        tab = self.ready(self.add(self.open()))
        body = {'expected_version':tab['version'],'amount_cents':5070,'method':'card'}
        result = self.race([('p1','pay',body,tab['id']), ('p2','pay',body,tab['id'])])
        self.assertEqual(sum(isinstance(r, dict) for r in result), 1)
        self.assertIn(409, result)
        tab = self.ready(self.add(self.open('t2')))
        body['expected_version'] = tab['version']
        edit = {'expected_version':tab['version'],'product_id':'tea','quantity':1}
        result = self.race([('p3','pay',body,tab['id']), ('edit','add_item',edit,tab['id'])])
        self.assertEqual(sum(isinstance(r, dict) for r in result), 1)
        self.assertIn(409, result)
        current = self.client.get(f"/api/tabs/{tab['id']}").json()
        self.assertTrue((current['status']=='paid' and len(current['items'])==1) or
                        (current['status']=='open' and current['payment'] is None and len(current['items'])==2))


if __name__ == '__main__':
    unittest.main()
