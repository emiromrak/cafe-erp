import { test } from 'node:test';
import assert from 'node:assert/strict';
import { formatQuantity, parseQuantity, recipePayload } from '../lib/inventory.mjs';
import { createCommand, sendCommand } from '../lib/api.mjs';
import { readPending, savePending, removePending } from '../lib/command-store.mjs';

test('Stok miktarı virgülden ve SQL üst sınırından hassasiyet kaybetmeden taşınır',()=>{
  assert.equal(parseQuantity(' 0001,234567 '),'1.234567');
  assert.equal(parseQuantity('99999999999999.999999'),'99999999999999.999999');
  assert.equal(parseQuantity('0,000001'),'0.000001');
  assert.equal(formatQuantity('99999999999999.999999'),'99.999.999.999.999,999999');
  assert.equal(formatQuantity('-1000.120000'),'-1.000,12');
});

test('Geçersiz miktar sessiz yuvarlama veya birim dönüşümü yapılmadan reddedilir',()=>{
  for(const input of ['','0','0.000000','-1','1e3','Infinity','NaN','1.0000001','100000000000000','1.234,56','1,2,3']) {
    assert.throws(()=>parseQuantity(input),undefined,input);
  }
});

test('Reçete gövdesi sunucu sürümünü ve kesin miktarları korur',()=>{
  assert.deepEqual(recipePayload(7,[{material_id:'leaf',quantity:'3,000001'}],' Gramaj güncellendi '),{
    expected_version:7,reason:'Gramaj güncellendi',lines:[{material_id:'leaf',quantity:'3.000001'}]
  });
  for(const lines of [[],[{material_id:'',quantity:'1'}],[{material_id:'leaf',quantity:'1'},{material_id:'leaf',quantity:'2'}]]) {
    assert.throws(()=>recipePayload(7,lines,'Test'));
  }
  assert.throws(()=>recipePayload(7,[{material_id:'leaf',quantity:'1'}],' '));
});

test('Yanıtı kaybolan reçete PUT isteği yenileme sonrası aynı anahtar ve personelle sürdürülür',async()=>{
  const data=new Map();
  const storage={get length(){return data.size;},key:i=>[...data.keys()][i],getItem:key=>data.get(key)||null,
    setItem:(key,value)=>data.set(key,value),removeItem:key=>data.delete(key)};
  const command={...createCommand('/recipes/tea',recipePayload(2,[{material_id:'leaf',quantity:'0.000001'}],'Test'),'PUT'),actorId:4};
  const calls=[];
  const transport=async(url,options)=>{
    calls.push([url,options.method,options.headers.get('Idempotency-Key'),options.headers.get('X-CafeERP-Actor'),options.body]);
    if(calls.length===1)throw new Error('Yanıt kayboldu');
    return Response.json({product_id:'tea',version:3});
  };
  savePending(storage,command);
  await assert.rejects(sendCommand(command,transport),err=>err.status===0);
  const restored=readPending(storage);
  assert.equal(restored.method,'PUT');
  assert.equal(restored.body.lines[0].quantity,'0.000001');
  assert.equal((await sendCommand(restored,transport)).version,3);
  assert.deepEqual(calls[0],calls[1]);
  removePending(storage,restored);
  assert.equal(readPending(storage),null);
});
