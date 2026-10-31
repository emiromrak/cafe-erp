'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { AlertTriangle, LoaderCircle, Plus, RefreshCw, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Modal } from '@/components/ui/dialog';
import { RecipeEditor } from '@/components/recipe-editor';
import { createCommand, request } from '@/lib/api.mjs';
import { formatQuantity, parseQuantity } from '@/lib/inventory.mjs';
import type { InventoryCommand, Material, Movement } from '@/lib/inventory-types';
import type { Product } from '@/lib/types';

const kinds:Record<string,string>={opening:'Açılış',receipt:'Stok girişi',return:'Depoya iade',waste:'Zayiat',staff:'Personel tüketimi',complimentary:'İkram',consume:'Üretim tüketimi'};

export function InventoryPanel({locked,busy,hasPending,revision,recipeRevision,onCommand,commandError}:{locked:boolean;busy:boolean;hasPending:boolean;revision:number;recipeRevision:number;onCommand:(command:InventoryCommand)=>Promise<boolean>;commandError:string}) {
  const [view,setView] = useState<'stock'|'ledger'|'recipes'>('stock');
  const [materials,setMaterials] = useState<Material[]>([]);
  const [products,setProducts] = useState<Product[]>([]);
  const [loading,setLoading] = useState(true);
  const [error,setError] = useState('');
  const [formError,setFormError] = useState('');
  const [search,setSearch] = useState('');
  const [critical,setCritical] = useState(false);
  const [movementOpen,setMovementOpen] = useState(false);
  const [materialId,setMaterialId] = useState('');
  const [kind,setKind] = useState('receipt');
  const [quantity,setQuantity] = useState('');
  const [reason,setReason] = useState('');
  const [productId,setProductId] = useState('');
  const [ledgerFilter,setLedgerFilter] = useState('');
  const [movements,setMovements] = useState<Movement[]>([]);
  const [ledgerLoading,setLedgerLoading] = useState(false);
  const [ledgerError,setLedgerError] = useState('');
  const [more,setMore] = useState(false);
  const alive = useRef(true);
  const reading = useRef(false);
  const ledgerEpoch = useRef(0);
  const formGate = useRef(false);

  const load = useCallback(async()=>{
    if(reading.current)return;
    reading.current=true;
    try {
      const [items,menu]=await Promise.all([request('/inventory/materials'),request('/products')]);
      if(alive.current){setMaterials(items);setProducts(menu);setError('');}
    } catch(err) {if(alive.current)setError(err instanceof Error?err.message:'Stok okunamadı.');}
    finally {reading.current=false;if(alive.current)setLoading(false);}
  },[]);

  useEffect(()=>{
    alive.current=true;void load();
    const timer=setInterval(()=>void load(),5000);
    return ()=>{alive.current=false;clearInterval(timer);ledgerEpoch.current++;};
  },[load]);
  useEffect(()=>{void load();},[load,revision]);
  // Sonucu belirsiz yazmada modalı kapat; ortak tekrar kontrolü erişilebilir kalsın.
  useEffect(()=>{if(hasPending&&!busy)setMovementOpen(false);},[hasPending,busy]);

  const loadLedger = useCallback(async(before?:number)=>{
    const generation=++ledgerEpoch.current;
    setLedgerLoading(true);setLedgerError('');
    const query=new URLSearchParams({order:'desc',limit:'50'});
    if(ledgerFilter)query.set('material_id',ledgerFilter);
    if(before)query.set('before_id',String(before));
    try {
      const page:Movement[]=await request(`/inventory/movements?${query}`);
      if(alive.current&&generation===ledgerEpoch.current){
        setMovements(previous=>before?[...previous,...page.filter(item=>!previous.some(old=>old.id===item.id))]:page);
        setMore(page.length===50);
      }
    } catch(err){if(alive.current&&generation===ledgerEpoch.current)setLedgerError(err instanceof Error?err.message:'Hareketler okunamadı.');}
    finally{if(alive.current&&generation===ledgerEpoch.current)setLedgerLoading(false);}
  },[ledgerFilter]);
  useEffect(()=>{
    if(view==='ledger'){setMovements([]);setMore(false);void loadLedger();}
    return ()=>{ledgerEpoch.current++;};
  },[view,loadLedger,revision]);

  const disabled=locked||loading||!!error;
  const material=materials.find(item=>item.id===materialId);
  const shown=materials.filter(item=>(!critical||item.is_critical)&&item.name.toLocaleLowerCase('tr').includes(search.toLocaleLowerCase('tr')));
  function openMovement(id='') {setMaterialId(id);setKind('receipt');setQuantity('');setReason('');setFormError('');setMovementOpen(true);}

  return <>
    <div className="page-heading"><div><h1>Stok ve reçeteler.</h1><p>Gerçek stok bakiyelerini takip edin, malzeme hareketlerini ve ürün reçetelerini yönetin.</p></div>
      <Button disabled={disabled} onClick={()=>openMovement()}><Plus size={17}/>Hareket ekle</Button></div>
    {error && <div className="alert error" role="alert"><span>{error}</span><Button variant="outline" onClick={()=>void load()}>Yeniden dene</Button></div>}
    <div className="inventory-toolbar"><div className="tabs">{([['stock','Hammaddeler'],['ledger','Hareket defteri'],['recipes','Reçeteler']] as const).map(([value,label])=><button key={value} disabled={busy} className={view===value?'selected':''} onClick={()=>setView(value)}>{label}</button>)}</div>
      <span className="inventory-critical"><AlertTriangle size={15}/>{materials.filter(item=>item.is_critical).length} kritik hammadde</span></div>
    {view==='stock' && <>
      <div className="inventory-filters"><div className="search"><Search size={18}/><input aria-label="Hammadde ara" placeholder="Hammadde ara…" value={search} onChange={e=>setSearch(e.target.value)}/></div>
        <label className="inventory-check"><input type="checkbox" checked={critical} onChange={e=>setCritical(e.target.checked)}/>Yalnızca kritik stoklar</label></div>
      {loading?<div className="empty"><LoaderCircle className="animate-spin"/>Stok yükleniyor…</div>:<div className="inventory-table-wrap"><table className="inventory-table"><thead><tr><th>Hammadde</th><th>Mevcut stok</th><th>Kritik eşik</th><th>Durum</th><th>İşlem</th></tr></thead><tbody>
        {shown.map(item=><tr key={item.id}><td><strong>{item.name}</strong><small>{item.category}</small></td><td>{formatQuantity(item.current_stock)} {item.unit}</td><td>{formatQuantity(item.min_alert)} {item.unit}</td><td><span className={`status ${item.is_critical?'status-sent':'status-ready'}`}>{item.is_critical?'Kritik':'Normal'}</span></td><td><Button variant="outline" disabled={disabled} onClick={()=>openMovement(item.id)}>Hareket ekle</Button></td></tr>)}
        {!shown.length && <tr><td colSpan={5}>Filtreye uygun hammadde bulunamadı.</td></tr>}
      </tbody></table></div>}
    </>}
    {view==='ledger' && <>
      <div className="inventory-filters"><label className="inventory-label">Hammadde<select value={ledgerFilter} onChange={e=>setLedgerFilter(e.target.value)}><option value="">Tüm hammaddeler</option>{materials.map(item=><option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
        <Button variant="outline" disabled={ledgerLoading} onClick={()=>void loadLedger()}><RefreshCw size={15}/>Yenile</Button></div>
      <p className="inventory-help">En yeni hareketler önce gösterilir. Depoya iade stoğu artırır; üretimden sonra iptal edilen tüketim zayiat olarak işaretlenir.</p>
      {ledgerError && <div className="alert error" role="alert">{ledgerError}</div>}
      <div className="inventory-table-wrap"><table className="inventory-table"><thead><tr><th>Tarih</th><th>Hammadde / işlem</th><th>Hareket</th><th>İşlem sonrası bakiye</th><th>Gerekçe</th></tr></thead><tbody>{movements.map(item=><tr key={item.id}>
        <td>{new Date(item.created_at).toLocaleString('tr-TR',{timeZone:'Europe/Istanbul'})}<small>#{item.id}{item.item_id?` · Kalem #${item.item_id}`:''}</small></td>
        <td><strong>{item.material_name}</strong><small>{kinds[item.kind]||item.kind}{item.disposition==='waste'?' · Üretim iptali / zayiat':''}</small></td>
        <td>{!item.quantity.startsWith('-')?'+':''}{formatQuantity(item.quantity)} {item.unit}</td><td>{formatQuantity(item.balance_after)} {item.unit}</td><td>{item.reason}</td></tr>)}
        {!movements.length&&!ledgerLoading && <tr><td colSpan={5}>Hareket bulunamadı.</td></tr>}
      </tbody></table></div>
      <div className="inventory-pagination"><span>{movements.length} hareket gösteriliyor</span>{ledgerLoading?<LoaderCircle className="animate-spin" size={20}/>:more?<Button variant="outline" onClick={()=>void loadLedger(movements.at(-1)?.id)}>Daha eski hareketler</Button>:null}</div>
    </>}
    {view==='recipes' && <>
      <label className="inventory-label recipe-product">Ürün<select value={productId} disabled={busy} onChange={e=>setProductId(e.target.value)}><option value="">Reçetesini düzenleyeceğiniz ürünü seçin</option>{products.map(item=><option value={item.id} key={item.id}>{item.name}</option>)}</select></label>
      {productId?<RecipeEditor key={productId} productId={productId} materials={materials} locked={disabled} revision={recipeRevision} onCommand={onCommand} commandError={commandError}/>:<div className="empty">Bir ürün seçerek reçetesini görüntüleyin veya oluşturun.</div>}
    </>}
    <Modal open={movementOpen} onOpenChange={open=>{if(!busy)setMovementOpen(open);}} title="Stok hareketi ekle" description="Miktarı hammaddenin kayıtlı biriminde girin.">
      {(formError||commandError) && <div className="alert error" role="alert">{commandError||formError}</div>}
      <form className="inventory-movement-form" onSubmit={async e=>{
        e.preventDefault();if(disabled||formGate.current||!material)return;setFormError('');
        try {
          const amount=parseQuantity(quantity);
          if(!reason.trim())throw new Error('Hareket gerekçesini yazın.');
          formGate.current=true;
          const saved=await onCommand(createCommand(`/inventory/materials/${encodeURIComponent(material.id)}/movements`,{kind,quantity:amount,unit:material.unit,reason:reason.trim()}));
          if(saved){setMovementOpen(false);setQuantity('');setReason('');}
          else setFormError('İşlem tamamlanamadı. Ekrandaki uyarıyı ve varsa bekleyen işlem kaydını kontrol edin.');
        } catch(err){setFormError(err instanceof Error?err.message:'Hareket doğrulanamadı.');}
        finally{formGate.current=false;}
      }}><fieldset disabled={disabled}>
        <label className="inventory-label">Hammadde<select value={materialId} required onChange={e=>setMaterialId(e.target.value)}><option value="">Hammadde seçin</option>{materials.map(item=><option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
        <label className="inventory-label">İşlem türü<select value={kind} onChange={e=>setKind(e.target.value)}>{['receipt','return','waste','staff','complimentary'].map(value=><option key={value} value={value}>{kinds[value]}</option>)}</select></label>
        <label className="inventory-label">Miktar {material?`(${material.unit})`:''}<input inputMode="decimal" required maxLength={40} value={quantity} onChange={e=>setQuantity(e.target.value)}/></label>
        <p className="inventory-help">{kind==='receipt'||kind==='return'?'Stok bu miktar kadar artırılır.':'Stok bu miktar kadar azaltılır.'} Birim: {material?.unit||'Hammadde seçin'}. En fazla 6 ondalık basamak.</p>
        <label className="inventory-label">Gerekçe<textarea required maxLength={500} value={reason} onChange={e=>setReason(e.target.value)}/></label>
        <Button className="w-full" disabled={!material||!quantity||!reason.trim()}>Hareketi kaydet</Button>
      </fieldset></form>
    </Modal>
  </>;
}
