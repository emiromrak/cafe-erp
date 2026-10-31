import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createCommand, sendCommand, request, ApiError, advanceSession } from '../lib/api.mjs';
import { savePending, readPending, removePending } from '../lib/command-store.mjs';

test('İki sekmenin bekleyen işlemleri birbirini ezmez', () => {
  const data = new Map();
  const store = { get length(){return data.size;}, key:i=>[...data.keys()][i],
    getItem:k=>data.get(k)||null, setItem:(k,v)=>data.set(k,v), removeItem:k=>data.delete(k) };
  const payment = createCommand('/tabs/1/payments',{amount_cents:100});
  const kitchen = createCommand('/tabs/2/items/3/status',{status:'ready'});
  savePending(store,payment); savePending(store,kitchen);
  assert.equal(store.length,2);
  assert.deepEqual(readPending(store),payment);
  removePending(store,payment);
  assert.deepEqual(readPending(store),kitchen);
  removePending(store,kitchen);
  assert.equal(readPending(store),null);
});

test('Yanıtı kaybolan ödeme aynı anahtar ve gövdeyle yeniden gönderilir', async () => {
  const command = createCommand('/tabs/7/payments', {expected_version:4,amount_cents:5070,method:'cash'});
  const calls = [];
  const transport = async (url, options) => {
    calls.push([url, options.headers.get('Idempotency-Key'), options.body]);
    if (calls.length === 1) throw new TypeError('connection lost');
    return Response.json({status:'paid'});
  };
  await assert.rejects(sendCommand(command, transport), e => e instanceof ApiError && e.status === 0);
  assert.deepEqual(await sendCommand(JSON.parse(JSON.stringify(command)), transport), {status:'paid'});
  assert.deepEqual(calls[0], calls[1]);
  assert.equal(calls[0][1], command.key);
});
test('Sürüm uyuşmazlığı otomatik olarak yeni işlem üretmez', async () => {
  let calls = 0;
  await assert.rejects(sendCommand(createCommand('/tabs/7/items',{expected_version:0,product_id:'tea',quantity:1}), async () => {
    calls++; return Response.json({detail:'Adisyon değişmiş.'}, {status:409});
  }), e => e.status === 409 && e.message === 'Adisyon değişmiş.');
  assert.equal(calls, 1);
});
test('Bozuk başarılı yanıtın sonucu belirsizdir', async () => {
  await assert.rejects(request('/tabs',{},async()=>new Response('bad')), e=>e.status===0);
});

test('Yazmalar güvenlik başlığı ve işlemi başlatan personel ile gönderilir', async () => {
  const command = {...createCommand('/tabs',{table_id:'t1'}),actorId:7};
  await sendCommand(command,async(url,options)=>{
    assert.equal(options.headers.get('X-CafeERP-Request'),'1');
    assert.equal(options.headers.get('X-CafeERP-Actor'),'7');
    assert.equal(options.headers.get('Idempotency-Key'),command.key);
    assert.equal(JSON.parse(options.body).actorId,undefined);
    return Response.json({id:1});
  });
});

test('Oturum hatası otomatik yeni ödeme veya tekrar isteği üretmez', async () => {
  let calls=0;
  await assert.rejects(sendCommand(createCommand('/tabs/1/payments',{amount_cents:100}),async()=>{
    calls++; return Response.json({detail:'Giriş gerekli.'},{status:401});
  }),err=>err.status===401);
  assert.equal(calls,1);
});

test('Önceki personelden geciken 401 yeni oturumu kapatmaz', async () => {
  const previousWindow=globalThis.window;
  const events=[];
  globalThis.window={dispatchEvent:event=>events.push(event.type)};
  try {
    let finish;
    const pending=request('/tabs',{},()=>new Promise(resolve=>{finish=resolve;}));
    const rejected=assert.rejects(pending,err=>err.status===401);
    advanceSession();
    finish(Response.json({detail:'Eski oturum.'},{status:401}));
    await rejected;
    assert.deepEqual(events,[]);
    await assert.rejects(request('/tabs',{},async()=>Response.json({detail:'Oturum bitti.'},{status:401})),err=>err.status===401);
    assert.deepEqual(events,['cafeerp-session-ended']);
  } finally {
    if(previousWindow===undefined)delete globalThis.window;
    else globalThis.window=previousWindow;
  }
});
