import { test } from 'node:test';
import assert from 'node:assert/strict';
import { canCancelItem, canCancelTab } from '../lib/cancellation.mjs';

test('Garson ve kasiyer yalnızca hazırlanmamış mutfak kalemini iptal edebilir',()=>{
  for(const role of ['waiter','cashier']){
    assert.equal(canCancelItem(role,'sent'),true);
    for(const status of ['preparing','ready','draft','cancelled'])assert.equal(canCancelItem(role,status),false);
  }
  for(const role of ['kitchen','admin']){
    assert.equal(canCancelItem(role,'preparing'),true);
    assert.equal(canCancelItem(role,'ready'),true);
  }
});

test('Hazırlanmış kalem varken tüm adisyon iptaliyle kısıt aşılamaz',()=>{
  for(const role of ['waiter','cashier']){
    assert.equal(canCancelTab(role,[{status:'draft'},{status:'sent'}]),true);
    assert.equal(canCancelTab(role,[{status:'sent'},{status:'preparing'}]),false);
    assert.equal(canCancelTab(role,[{status:'ready'}]),false);
    assert.equal(canCancelTab(role,[{status:'cancelled'}]),true);
  }
  assert.equal(canCancelTab('kitchen',[{status:'sent'}]),false);
  assert.equal(canCancelTab('admin',[{status:'ready'}]),true);
});
