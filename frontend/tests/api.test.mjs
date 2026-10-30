import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createCommand, sendCommand, request, ApiError } from '../lib/api.mjs';
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
    calls.push([url, options.headers['Idempotency-Key'], options.body]);
    if (calls.length === 1) throw new TypeError('connection lost');
    return Response.json({status:'paid'});
  };
  await assert.rejects(sendCommand(command, transport), e => e instanceof ApiError && e.status === 0);
  assert.deepEqual(await sendCommand(JSON.parse(JSON.stringify(command)), transport), {status:'paid'});
  assert.deepEqual(calls[0], calls[1]);
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
