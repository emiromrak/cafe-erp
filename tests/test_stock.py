"""Stok bakiyesi, reçete sürümü, iptal ve eşzamanlı tüketim için regresyon testleri."""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from unittest.mock import patch
import json
import tempfile
from pathlib import Path
import sys

from fastapi import HTTPException
from sqlalchemy import text

from test_tabs import TabFixture, ROOT
from app import stock_service, tab_service

sys.path.insert(0,str(ROOT / 'scripts'))
from import_recipes import import_recipes


class StockTests(TabFixture):
    def balance(self):
        with self.engine.connect() as conn:
            return conn.execute(text("SELECT current_stock FROM raw_materials WHERE id='leaf'")).scalar_one()

    def submitted(self, table='t1'):
        tab = self.add(self.open(table))
        return self.send(f"/api/tabs/{tab['id']}/submit",{'expected_version':tab['version']})

    def prepare(self, tab, key=None):
        return self.send(f"/api/tabs/{tab['id']}/items/{tab['items'][0]['id']}/status",
            {'expected_version':tab['version'],'status':'preparing'},key,method='patch')

    def test_preparation_consumes_once_and_cancel_marks_waste_without_second_deduction(self):
        tab = self.submitted()
        self.assertEqual(self.balance(),Decimal('100000'))
        prepared = self.prepare(tab,'prepare-1')
        self.assertEqual(self.prepare(tab,'prepare-1'),prepared)
        self.assertEqual(self.balance(),Decimal('99994'))
        prepared = self.send(f"/api/tabs/{tab['id']}/items/{tab['items'][0]['id']}/cancel",
            {'expected_version':prepared['version'],'reason':'Müşteri ayrıldı'})
        self.assertEqual(self.balance(),Decimal('99994'))
        movements=self.client.get('/api/inventory/movements').json()
        self.assertEqual(len(movements),2)
        self.assertEqual(movements[-1]['quantity'],'-6.000000')
        self.assertEqual(movements[-1]['disposition'],'waste')
        self.assertEqual(movements[-1]['unit'],'gram')

    def test_cancel_before_preparation_does_not_consume(self):
        tab=self.submitted()
        self.send(f"/api/tabs/{tab['id']}/cancel",{'expected_version':tab['version'],'reason':'Vazgeçildi'})
        self.assertEqual(self.balance(),Decimal('100000'))
        self.assertEqual(len(self.client.get('/api/inventory/movements').json()),1)

    def test_payment_and_ready_do_not_consume_twice(self):
        tab=self.ready(self.add(self.open()))
        self.assertEqual(self.balance(),Decimal('99994'))
        self.send(f"/api/tabs/{tab['id']}/payments",{'expected_version':tab['version'],'method':'cash','amount_cents':5070})
        self.assertEqual(self.balance(),Decimal('99994'))

    def test_shortage_rolls_back_all_ingredients_status_event_and_key(self):
        self.send('/api/inventory/materials/leaf/movements',{'kind':'waste','quantity':'99998','unit':'gram','reason':'Test sayımı'})
        with self.engine.begin() as conn:
            conn.execute(text("INSERT INTO raw_materials VALUES ('aaa','İlk hammadde','Çay','gram',100,1,1)"))
            conn.execute(text("INSERT INTO recipe_lines VALUES ('tea','aaa',1)"))
        tab=self.submitted()
        with self.engine.connect() as conn:
            before=conn.execute(text('SELECT COUNT(*) FROM tab_events')).scalar()
        self.send(f"/api/tabs/{tab['id']}/items/{tab['items'][0]['id']}/status",
                  {'expected_version':tab['version'],'status':'preparing'},'shortage',method='patch',expected=409)
        self.assertEqual(self.balance(),Decimal('2'))
        self.assertEqual(self.client.get(f"/api/tabs/{tab['id']}").json(),tab)
        with self.engine.connect() as conn:
            self.assertEqual(conn.execute(text("SELECT current_stock FROM raw_materials WHERE id='aaa'")).scalar(),Decimal(100))
            self.assertEqual(conn.execute(text('SELECT COUNT(*) FROM item_materials')).scalar(),0)
            self.assertEqual(conn.execute(text('SELECT COUNT(*) FROM tab_events')).scalar(),before)
            self.assertEqual(conn.execute(text("SELECT COUNT(*) FROM api_requests WHERE key='shortage'")).scalar(),0)

    def test_recipe_version_changes_preserve_consumption_snapshot(self):
        tab=self.prepare(self.submitted())
        body={'expected_version':1,'reason':'Gramaj değişti','lines':[{'material_id':'leaf','quantity':'1.250001'}]}
        recipe=self.send('/api/recipes/tea',body,'recipe-1',method='put')
        self.assertEqual(recipe['version'],2)
        self.assertEqual(recipe,self.send('/api/recipes/tea',body,'recipe-1',method='put'))
        self.send('/api/recipes/tea',body,method='put',expected=409)
        self.prepare(self.submitted('t2'))
        self.assertEqual(self.balance(),Decimal('99991.499998'))
        with self.engine.connect() as conn:
            first=conn.execute(text('SELECT recipe_version,quantity_per_unit,quantity FROM item_materials WHERE item_id=:id'),{'id':tab['items'][0]['id']}).one()
            self.assertEqual(tuple(first),(1,Decimal('3'),Decimal('6')))
            self.assertEqual(conn.execute(text('SELECT COUNT(*) FROM recipe_history')).scalar(),1)

    def test_manual_movement_replay_validation_and_ledger_reconcile(self):
        path='/api/inventory/materials/leaf/movements'
        body={'kind':'receipt','quantity':'0.123456','unit':'gram','reason':'Tedarik'}
        result=self.send(path,body,'receipt-1')
        self.assertEqual(result,self.send(path,body,'receipt-1'))
        self.assertEqual(result['current_stock'],'100000.123456')
        for kind in ('return','waste','staff','complimentary'):
            self.send(path,{**body,'kind':kind})
        for qty in ('NaN','Infinity','0','-1','0.0000001','100000000000000'):
            self.send(path,{**body,'quantity':qty},expected=422)
        self.send(path,{**body,'unit':'kg'},expected=422)
        self.send('/api/recipes/tea',{'expected_version':1,'reason':'Boş','lines':[]},method='put',expected=422)
        with self.engine.connect() as conn:
            total=conn.execute(text("SELECT SUM(quantity) FROM stock_movements WHERE material_id='leaf'")).scalar()
        self.assertEqual(self.balance(),total)

    def test_recipe_missing_blocks_preparation_and_duplicate_material_is_rejected(self):
        with self.engine.begin() as conn:
            conn.execute(text("DELETE FROM recipe_lines WHERE product_id='tea'"))
        tab=self.submitted()
        self.send(f"/api/tabs/{tab['id']}/items/{tab['items'][0]['id']}/status",
                  {'expected_version':tab['version'],'status':'preparing'},method='patch',expected=409)
        body={'expected_version':1,'reason':'Tekrar','lines':[{'material_id':'leaf','quantity':'1'}]*2}
        self.send('/api/recipes/tea',body,method='put',expected=422)

    def test_concurrent_last_stock_can_only_be_consumed_once(self):
        self.send('/api/inventory/materials/leaf/movements',{'kind':'waste','quantity':'99994','unit':'gram','reason':'Test sayımı'})
        tabs=[self.submitted('t1'),self.submitted('t2')]
        barrier=Barrier(2)
        def prepare(tab):
            barrier.wait(timeout=10)
            try:
                return tab_service.execute(self.engine,str(tab['id']),'item_status',
                    {'expected_version':tab['version'],'status':'preparing'},tab['id'],tab['items'][0]['id'])
            except HTTPException as exc:
                return exc.status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(prepare,tabs))
        self.assertEqual(sum(isinstance(r,dict) for r in results),1)
        self.assertIn(409,results)
        self.assertEqual(self.balance(),Decimal(0))
        self.assertTrue(self.client.get('/api/inventory/materials').json()[0]['is_critical'])

    def test_recipe_import_is_atomic_and_preserves_existing_recipes(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'recipes.json'
            source.write_text(json.dumps({'recipes':{'tea':[{'rm_id':'leaf','qty':99}],
                'free':[{'rm_id':'leaf','qty':55}]}}),encoding='utf-8')
            self.assertEqual(import_recipes(source,self.engine),{'imported':0,'preserved':2})
            with self.engine.begin() as conn:
                conn.execute(text("DELETE FROM recipe_lines WHERE product_id='free'"))
                conn.execute(text("DELETE FROM product_recipes WHERE product_id='free'"))
            source.write_text(json.dumps({'recipes':{'free':[{'rm_id':'missing','qty':1}]}}),encoding='utf-8')
            with self.assertRaises(HTTPException):
                import_recipes(source,self.engine)
            self.assertEqual(self.client.get('/api/recipes/free').json()['version'],0)
            source.write_text(json.dumps({'recipes':{'free':[{'rm_id':'leaf','qty':1.25}]}}),encoding='utf-8')
            self.assertEqual(import_recipes(source,self.engine),{'imported':1,'preserved':0})
            self.assertEqual(self.client.get('/api/recipes/free').json()['lines'][0]['quantity'],'1.250000')

    def test_forecast_mix_comes_from_sql_recipes_and_sales_share(self):
        with self.engine.begin() as conn:
            conn.execute(text("""INSERT INTO products VALUES
                ('prod_latte','c','Latte',100,'hot'),('prod_americano','c','Americano',90,'hot')"""))
            conn.execute(text("INSERT INTO product_recipes VALUES ('prod_latte',1,now()),('prod_americano',1,now())"))
            conn.execute(text("INSERT INTO recipe_lines VALUES ('prod_latte','leaf',7),('prod_americano','leaf',2)"))
            conn.execute(text("""INSERT INTO order_items(order_id,product_id,quantity,unit_price)
                VALUES ('old','prod_latte',3,100),('old','prod_americano',1,90)"""))
            mix,warnings=stock_service.forecast_recipe_mix(conn)
        self.assertEqual(sum(line['quantity'] for line in mix['predicted_hot_coffee']),Decimal('5.75'))
        self.assertFalse(any(w.get('group')=='predicted_hot_coffee' for w in warnings))
