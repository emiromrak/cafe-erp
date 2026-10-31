"""Gerçek PostgreSQL oturumlarıyla personel, rol ve işlem sorumluluğu sınamaları."""
import uuid
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient
from sqlalchemy import text

from test_tabs import TabFixture
from app.main import app
from app import auth

PASSWORD = '583027461902'
ENCODED = auth.hash_password(PASSWORD)


class AuthTests(TabFixture):
    def account(self, role, username=None):
        username = username or role
        token = uuid.uuid4().hex
        with self.engine.begin() as conn:
            account = dict(conn.execute(text('''INSERT INTO staff_accounts(username,name,role,password_hash)
                VALUES (:name,:name,:role,:hash) RETURNING id,username,name,role,is_active,version'''),
                {'name':username,'role':role,'hash':ENCODED}).mappings().one())
            conn.execute(text("""INSERT INTO staff_sessions(token_hash,staff_id,expires_at)
                VALUES (:hash,:id,now()+interval '12 hours')"""), {'hash':auth.token_hash(token),'id':account['id']})
        client = TestClient(app, headers={'X-CafeERP-Request':'1'})
        client.cookies.set(auth.COOKIE,token)
        self.addCleanup(client.close)
        return client, account, token

    def login(self, client, username, password=PASSWORD):
        return client.post('/api/auth/login', json={'username':username,'password':password})

    def test_anonymous_expired_and_inactive_sessions_are_denied(self):
        self.client.cookies.clear()
        for url in ('/api/tables','/api/tabs','/api/kitchen/items','/api/inventory/materials','/api/ai/sales-summary','/api/auth/staff'):
            self.assertEqual(self.client.get(url).status_code,401,url)
        self.assertEqual(self.client.post('/api/tabs',json={'table_id':'t1'},headers={'Idempotency-Key':'unauthorized'}).status_code,401)
        self.assertEqual(self.client.get('/').status_code,200)
        client, account, token = self.account('waiter')
        with self.engine.begin() as conn:
            conn.execute(text("UPDATE staff_sessions SET expires_at=now()-interval '1 second' WHERE staff_id=:id"),account)
        self.assertEqual(client.get('/api/auth/me').status_code,401)
        with self.engine.begin() as conn:
            conn.execute(text("UPDATE staff_sessions SET expires_at=now()+interval '1 hour' WHERE staff_id=:id"),account)
            conn.execute(text('UPDATE staff_accounts SET is_active=false WHERE id=:id'),account)
        self.assertEqual(client.get('/api/auth/me').status_code,401)

    def test_login_sets_private_cookie_hashes_token_and_logout_revokes_it(self):
        client, account, previous = self.account('cashier')
        response = self.login(client,'cashier')
        self.assertEqual(response.status_code,200,response.text)
        cookie = response.headers['set-cookie']
        self.assertIn('HttpOnly',cookie)
        self.assertIn('SameSite=strict',cookie)
        self.assertEqual(response.headers['cache-control'],'no-store')
        self.assertNotIn('password',response.text)
        self.assertNotIn('token',response.text)
        with self.engine.connect() as conn:
            tokens = conn.execute(text('SELECT token_hash FROM staff_sessions WHERE staff_id=:id'),account).scalars().all()
            self.assertEqual(len(tokens),1)
            self.assertNotEqual(tokens[0],auth.token_hash(previous))
        self.assertEqual(client.get('/api/auth/me').json()['id'],account['id'])
        self.assertEqual(client.post('/api/auth/logout').status_code,200)
        self.assertEqual(client.get('/api/auth/me').status_code,401)
        client.cookies.set(auth.COOKIE,previous)
        self.assertEqual(client.get('/api/auth/me').status_code,401)

    def test_failed_logins_are_committed_and_throttled(self):
        client, _, _ = self.account('waiter')
        for _ in range(5):
            bad = self.login(client,'waiter','wrong-password')
            self.assertEqual(bad.status_code,401)
        self.assertEqual(self.login(client,'waiter').status_code,429)
        self.assertEqual(self.login(client,'missing','wrong-password').json()['detail'],bad.json()['detail'])
        with self.engine.connect() as conn:
            self.assertEqual(conn.execute(text("SELECT count(*) FROM login_attempts WHERE username='waiter' AND NOT success")).scalar_one(),5)
        with self.engine.begin() as conn:
            conn.execute(text("UPDATE login_attempts SET attempted_at=now()-interval '16 minutes'"))
        self.assertEqual(self.login(client,'waiter').status_code,200)

    def test_global_login_limit_blocks_username_spraying(self):
        with self.engine.begin() as conn:
            conn.execute(text("INSERT INTO login_attempts(username) SELECT 'unknown-'||n FROM generate_series(1,60) n"))
        self.assertEqual(self.login(self.client,'another-name').status_code,429)
        client,_,_=self.account('waiter')
        with self.engine.begin() as conn:
            conn.execute(text('DELETE FROM login_attempts'))
            conn.execute(text("""INSERT INTO login_attempts(username,attempted_at)
                SELECT 'waiter',now()-interval '2 minutes' FROM generate_series(1,4)"""))
            conn.execute(text("INSERT INTO login_attempts(username,success) SELECT 'other-'||n,true FROM generate_series(1,59) n"))
        # Hesabın eski başarısız denemeleri son bir dakikanın genel sayacına eklenmez.
        self.assertEqual(self.login(client,'waiter').status_code,200)
        self.assertEqual(self.login(client,'another-name').status_code,429)

    def test_invalid_password_is_not_reflected_in_validation_response(self):
        password='abc'
        response=self.client.post('/api/auth/staff',json={'username':'shortstaff','name':'Test','role':'waiter','password':password})
        self.assertEqual(response.status_code,422)
        self.assertNotIn(password,response.text)

    def test_write_header_origin_and_cors_are_enforced(self):
        response = self.client.post('/api/auth/logout',headers={'X-CafeERP-Request':''})
        self.assertEqual(response.status_code,403)
        for path, body in [('/api/auth/login',{'username':'testadmin','password':PASSWORD}),('/api/tabs',{'table_id':'t1'})]:
            response = self.client.post(path,json=body,headers={'Origin':'https://untrusted.example','Idempotency-Key':uuid.uuid4().hex})
            self.assertEqual(response.status_code,403,response.text)
        allowed = self.client.options('/api/auth/login',headers={'Origin':'http://localhost:3000',
            'Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'X-CafeERP-Request,Content-Type'})
        self.assertEqual(allowed.status_code,200)
        self.assertEqual(allowed.headers['access-control-allow-origin'],'http://localhost:3000')
        # Docker arayüzü 3000'i kullanırken Next geliştirme sunucusu 3001'e geçebilir.
        for origin in ('http://localhost:3001','http://127.0.0.1:3001'):
            allowed = self.client.options('/api/auth/login',headers={'Origin':origin,
                'Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'X-CafeERP-Request,Content-Type'})
            self.assertEqual(allowed.status_code,200)
            self.assertEqual(allowed.headers['access-control-allow-origin'],origin)
            self.assertEqual(self.client.post('/api/auth/logout',headers={'Origin':origin}).status_code,200)
        for origin in ('http://localhost:3002','http://localhost.evil.example:3001','null'):
            self.assertEqual(self.client.post('/api/auth/logout',headers={'Origin':origin}).status_code,403)
        denied = self.client.options('/api/auth/login',headers={'Origin':'https://untrusted.example','Access-Control-Request-Method':'POST'})
        self.assertEqual(denied.status_code,400)

    def test_role_matrix_protects_api_even_without_ui(self):
        for role in ('waiter','cashier','kitchen'):
            client, _, _ = self.account(role)
            for path in ('/api/categories','/api/products','/api/tables','/api/kitchen/items'):
                self.assertEqual(client.get(path).status_code,200,(role,path))
            for path in ('/api/inventory/materials','/api/inventory/movements','/api/recipes/tea','/api/ai/sales-summary','/api/auth/staff'):
                self.assertEqual(client.get(path).status_code,403,(role,path))
            self.assertEqual(client.get('/api/tabs').status_code,403 if role=='kitchen' else 200)
            body = {'expected_version':0,'amount_cents':100,'method':'cash'}
            response = client.post('/api/tabs/999999/payments',json=body,headers={'Idempotency-Key':uuid.uuid4().hex})
            self.assertEqual(response.status_code,404 if role=='cashier' else 403)
            response = client.patch('/api/tabs/999999/items/1/status',json={'expected_version':0,'status':'preparing'},headers={'Idempotency-Key':uuid.uuid4().hex})
            self.assertEqual(response.status_code,404 if role=='kitchen' else 403)
            response = client.post('/api/tabs',json={'table_id':'t1'},headers={'Idempotency-Key':uuid.uuid4().hex})
            self.assertEqual(response.status_code,403 if role=='kitchen' else 200)
            if response.status_code==200:
                tab=response.json()
                client.post(f"/api/tabs/{tab['id']}/cancel",json={'expected_version':0,'reason':'Rol testi'},headers={'Idempotency-Key':uuid.uuid4().hex})

    def test_waiter_kitchen_cashier_flow_preserves_actor_and_single_replay(self):
        waiter, w, _ = self.account('waiter')
        kitchen, k, _ = self.account('kitchen')
        cashier, c, _ = self.account('cashier')
        self.client = waiter
        tab = self.add(self.open())
        tab = self.send(f"/api/tabs/{tab['id']}/submit",{'expected_version':tab['version']})
        self.client = kitchen
        for status in ('preparing','ready'):
            tab = self.send(f"/api/tabs/{tab['id']}/items/{tab['items'][0]['id']}/status",{'expected_version':tab['version'],'status':status},method='patch')
        self.client = cashier
        path=f"/api/tabs/{tab['id']}/payments"
        body={'expected_version':tab['version'],'method':'cash','amount_cents':5070}
        paid = self.send(path,body,'pay-actor')
        self.assertEqual(self.send(path,body,'pay-actor'),paid)
        self.client = waiter
        self.send('/api/tabs',{'table_id':'t2'},'pay-actor',expected=409)
        with self.engine.connect() as conn:
            actors = conn.execute(text('SELECT actor_id FROM staff_audit ORDER BY id')).scalars().all()
            self.assertEqual(actors,[w['id']]*3+[k['id']]*2+[c['id']])
            self.assertEqual(conn.execute(text('SELECT count(*) FROM tab_payments')).scalar_one(),1)
        # Aynı tarayıcıda başka personel giriş yaptıysa eski ekran yazamaz.
        response = cashier.post('/api/tabs',json={'table_id':'t2'},headers={'Idempotency-Key':'stale-browser','X-CafeERP-Actor':str(w['id'])})
        self.assertEqual(response.status_code,401)

    def test_create_update_revoke_reset_and_last_admin_guard(self):
        response = self.client.post('/api/auth/staff',json={'username':'newstaff','name':'Yeni personel','role':'waiter','password':PASSWORD})
        self.assertEqual(response.status_code,201,response.text)
        account=response.json()
        self.assertNotIn('password_hash',account)
        self.assertEqual(self.client.post('/api/auth/staff',json={'username':'newstaff','name':'Tekrar','role':'waiter','password':PASSWORD}).status_code,409)
        client=TestClient(app,headers={'X-CafeERP-Request':'1'})
        self.addCleanup(client.close)
        self.assertEqual(self.login(client,'newstaff').status_code,200)
        body={'name':'Güncel','role':'cashier','is_active':True,'expected_version':0,'password':'739185026401'}
        changed=self.client.patch(f"/api/auth/staff/{account['id']}",json=body)
        self.assertEqual(changed.status_code,200,changed.text)
        self.assertEqual(client.get('/api/auth/me').status_code,401)
        self.assertEqual(self.client.patch(f"/api/auth/staff/{account['id']}",json=body).status_code,409)
        self.assertEqual(self.login(client,'newstaff').status_code,401)
        self.assertEqual(self.login(client,'newstaff','739185026401').json()['role'],'cashier')
        admin=self.client.get('/api/auth/me').json()
        body={'name':admin['name'],'role':'waiter','is_active':True,'expected_version':admin['version']}
        self.assertEqual(self.client.patch(f"/api/auth/staff/{admin['id']}",json=body).status_code,409)

    def test_deactivation_revokes_all_devices_and_blocks_login(self):
        client, account, token = self.account('waiter')
        second=TestClient(app,headers={'X-CafeERP-Request':'1'})
        self.addCleanup(second.close)
        self.assertEqual(self.login(second,'waiter').status_code,200)
        body={'name':'Pasif','role':'waiter','is_active':False,'expected_version':0}
        self.assertEqual(self.client.patch(f"/api/auth/staff/{account['id']}",json=body).status_code,200)
        for device in (client,second):
            self.assertEqual(device.get('/api/tables').status_code,401)
        self.assertEqual(self.login(client,'waiter').status_code,401)

    def test_concurrent_admin_changes_keep_an_active_admin(self):
        first,a,_=self.account('admin','firstadmin')
        second,b,_=self.account('admin','secondadmin')
        # Otomatik fixture yöneticisi bu senaryoda pasif olmalı.
        with self.engine.begin() as conn:
            conn.execute(text("UPDATE staff_accounts SET is_active=false WHERE username='testadmin'"))
        def demote(args):
            client,account=args
            return client.patch(f"/api/auth/staff/{account['id']}",json={'name':account['name'],
                'role':'waiter','is_active':True,'expected_version':0}).status_code
        with ThreadPoolExecutor(2) as executor:
            statuses=list(executor.map(demote,[(first,a),(second,b)]))
        self.assertEqual(sorted(statuses),[200,409])
        with self.engine.connect() as conn:
            self.assertEqual(conn.execute(text("SELECT count(*) FROM staff_accounts WHERE role='admin' AND is_active")).scalar_one(),1)

    def test_bootstrap_never_promotes_legacy_pins_or_overwrites_accounts(self):
        with self.engine.begin() as conn:
            conn.execute(text('DELETE FROM staff_sessions'))
            conn.execute(text('DELETE FROM staff_accounts'))
            conn.execute(text("INSERT INTO staff VALUES ('legacy','Eski','Yönetici','1234')"))
        account=auth.create_first_admin(self.engine,'owner','İşletme sahibi',PASSWORD)
        self.assertEqual(account['role'],'admin')
        with self.assertRaises(ValueError):
            auth.create_first_admin(self.engine,'second','İkinci',PASSWORD)
        with self.engine.connect() as conn:
            self.assertEqual(conn.execute(text('SELECT count(*) FROM staff_accounts')).scalar_one(),1)
            encoded=conn.execute(text('SELECT password_hash FROM staff_accounts')).scalar_one()
            self.assertNotIn(PASSWORD,encoded)
            self.assertTrue(auth.verify_password(PASSWORD,encoded))

    def test_failed_business_command_has_no_audit_or_idempotency_record(self):
        waiter,_,_=self.account('waiter')
        response=waiter.post('/api/tabs',json={'table_id':'missing'},headers={'Idempotency-Key':'failed-command'})
        self.assertEqual(response.status_code,404)
        with self.engine.connect() as conn:
            self.assertEqual(conn.execute(text('SELECT count(*) FROM staff_audit')).scalar_one(),0)
            self.assertEqual(conn.execute(text('SELECT count(*) FROM api_requests')).scalar_one(),0)

    def test_four_character_password_create_reset_and_login(self):
        for password in ('123','1'*129,'abcd','12a4','12 4','12-4','１２３４','١٢٣٤','1234\n'):
            response=self.client.post('/api/auth/staff',json={'username':'shortstaff','name':'Kasiyer','role':'cashier','password':password})
            self.assertEqual(response.status_code,422)
            with self.assertRaises(ValueError):
                auth.hash_password(password)
        response=self.client.post('/api/auth/staff',json={'username':'shortstaff','name':'Kasiyer','role':'cashier','password':'4826'})
        self.assertEqual(response.status_code,201,response.text)
        account=response.json()
        client=TestClient(app,headers={'X-CafeERP-Request':'1','Origin':'http://localhost:3001'})
        self.addCleanup(client.close)
        self.assertEqual(self.login(client,'shortstaff','4826').status_code,200)
        body={'name':'Kasiyer','role':'cashier','is_active':True,'expected_version':0,'password':'0037'}
        self.assertEqual(self.client.patch(f"/api/auth/staff/{account['id']}",json=body).status_code,200)
        self.assertEqual(client.get('/api/auth/me').status_code,401)
        self.assertEqual(self.login(client,'shortstaff','0037').status_code,200)
        rejected=self.client.patch(f"/api/auth/staff/{account['id']}",json={**body,'expected_version':1,'password':'12a4'})
        self.assertEqual(rejected.status_code,422)
        self.assertEqual(client.get('/api/auth/me').status_code,200)

    def test_legacy_password_can_login_until_admin_sets_numeric_password(self):
        client,account,_=self.account('cashier')
        legacy='Eski-parola-2026!'
        encoded=auth.hash_password(legacy,enforce_policy=False)
        with self.engine.begin() as conn:
            conn.execute(text('UPDATE staff_accounts SET password_hash=:hash WHERE id=:id'),{'hash':encoded,'id':account['id']})
        self.assertEqual(self.login(client,'cashier',legacy).status_code,200)
        with self.assertRaises(ValueError):
            auth.hash_password(legacy)
        body={'name':'Kasiyer','role':'cashier','is_active':True,'expected_version':0,'password':'0073'}
        self.assertEqual(self.client.patch(f"/api/auth/staff/{account['id']}",json=body).status_code,200)
        self.assertEqual(client.get('/api/auth/me').status_code,401)
        self.assertEqual(self.login(client,'cashier',legacy).status_code,401)
        self.assertEqual(self.login(client,'cashier','0073').status_code,200)

    def test_switch_list_requires_session_and_only_returns_active_basic_fields(self):
        client,account,_=self.account('cashier')
        _,inactive,_=self.account('waiter')
        with self.engine.begin() as conn:
            conn.execute(text('UPDATE staff_accounts SET is_active=false WHERE id=:id'),inactive)
        response=client.get('/api/auth/switchable-staff')
        self.assertEqual(response.status_code,200)
        self.assertIn(account['id'],[entry['id'] for entry in response.json()])
        self.assertNotIn(inactive['id'],[entry['id'] for entry in response.json()])
        for entry in response.json():
            self.assertEqual(set(entry),{'id','username','name','role'})
        client.cookies.clear()
        self.assertEqual(client.get('/api/auth/switchable-staff').status_code,401)

    def test_fast_switch_failure_preserves_session_success_rotates_and_attributes_writes(self):
        first,a,old_token=self.account('cashier','cashierone')
        second,b,_=self.account('cashier','cashiertwo')
        self.assertEqual(self.login(first,'cashiertwo','wrong-password').status_code,401)
        self.assertEqual(first.get('/api/auth/me').json()['id'],a['id'])
        self.assertEqual(self.login(first,'cashiertwo').status_code,200)
        self.assertEqual(first.get('/api/auth/me').json()['id'],b['id'])
        self.assertEqual(second.get('/api/auth/me').status_code,200)
        # Eski cookie tekrar kullanılamaz ve önceki personele bağlı yazma kabul edilmez.
        with self.engine.connect() as conn:
            self.assertIsNone(conn.execute(text('SELECT 1 FROM staff_sessions WHERE token_hash=:token'),{'token':auth.token_hash(old_token)}).first())
        headers={'Idempotency-Key':'stale-actor','X-CafeERP-Actor':str(a['id'])}
        self.assertEqual(first.post('/api/tabs',json={'table_id':'t1'},headers=headers).status_code,401)
        self.client=first
        self.open(key='new-actor')
        with self.engine.connect() as conn:
            self.assertEqual(conn.execute(text('SELECT actor_id FROM staff_audit WHERE request_key=:key'),{'key':'new-actor'}).scalar_one(),b['id'])
