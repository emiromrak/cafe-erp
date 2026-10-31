'use client';

import '@/components/inventory.css';

import { useCallback, useEffect, useRef, useState } from 'react';
import { Armchair, ArrowLeft, ArrowRight, Banknote, Check, CheckCheck, ChefHat, Coffee, CreditCard, Grid2X2, LoaderCircle, Minus, Plus, Search, Send, Soup, Trash2, Wifi, WifiOff, X } from 'lucide-react';
import { AuthGate } from '@/components/auth-gate';
import { roleNames, type Staff } from '@/lib/staff';
import { InventoryPanel } from '@/components/inventory-panel';
import { StaffPanel } from '@/components/staff-panel';
import { Button } from '@/components/ui/button';
import { Modal } from '@/components/ui/dialog';
import { ApiError, createCommand, request, sendCommand } from '@/lib/api.mjs';
import { canCancelItem, canCancelTab } from '@/lib/cancellation.mjs';
import { readPending, savePending, removePending } from '@/lib/command-store.mjs';
import type { Category, Item, KitchenItem, OpenTab, Product, Tab, Table } from '@/lib/types';

const money = (cents: number) => new Intl.NumberFormat('tr-TR', {style:'currency',currency:'TRY'}).format(cents / 100);
const statusNames: Record<Item['status'], string> = {draft:'Gönderilmedi', sent:'Bekliyor', preparing:'Hazırlanıyor', ready:'Hazır', cancelled:'İptal edildi'};
type Command = ReturnType<typeof createCommand> & {actorId?:number};

export default function Page() {
  return <AuthGate>{(user,onSwitch)=><POS key={`${user.id}:${user.version}`} user={user} onSwitch={onSwitch}/>}</AuthGate>;
}

function POS({user,onSwitch}:{user:Staff;onSwitch:()=>void}) {
  const [view, setView] = useState<'tables'|'kitchen'|'staff'|'inventory'>(user.role==='kitchen'?'kitchen':'tables');
  const [inventoryRevision,setInventoryRevision] = useState(0);
  const [recipeRevision,setRecipeRevision] = useState(0);
  const [tables, setTables] = useState<Table[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [openTabs, setOpenTabs] = useState<OpenTab[]>([]);
  const [kitchen, setKitchen] = useState<KitchenItem[]>([]);
  const [selected, setSelected] = useState<string|null>(null);
  const [tab, setTab] = useState<Tab|null>(null);
  const [area, setArea] = useState('all');
  const [category, setCategory] = useState('all');
  const [search, setSearch] = useState('');
  const [connected, setConnected] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [selectionLoading, setSelectionLoading] = useState(false);
  const [pending, setPending] = useState<Command|null>(null);
  const [storageError, setStorageError] = useState(false);
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const [payment, setPayment] = useState(false);
  const [method, setMethod] = useState<'cash'|'card'>('cash');
  const [confirmed, setConfirmed] = useState(false);
  const [cancel, setCancel] = useState<{item?:Item;kitchenItem?:KitchenItem}|null>(null);
  const [reason, setReason] = useState('');
  const gate = useRef(false);
  const selection = useRef<string|null>(null);
  const epoch = useRef(0);
  const pendingRef = useRef<Command|null>(null);
  const refreshing = useRef(false);
  const refreshAgain = useRef(false);

  const refresh = useCallback(async (): Promise<void> => {
    if (gate.current) return;
    if (refreshing.current) { refreshAgain.current = true; return; }
    refreshing.current = true;
    const generation = epoch.current;
    const tableId = selection.current;
    try {
      const [ts, ps, cs, os, ks] = user.role==='kitchen' ? [[], [], [], [], await request('/kitchen/items')] : await Promise.all([
        request('/tables'), request('/products'), request('/categories'), request('/tabs'), request('/kitchen/items')
      ]);
      const open = (os as OpenTab[]).find(t => t.table_id === tableId);
      const current: Tab|null = open ? await request(`/tabs/${open.id}`) : null;
      if (generation !== epoch.current || gate.current) return;
      setTables(ts); setProducts(ps); setCategories(cs); setOpenTabs(os); setKitchen(ks);
      if (selection.current === tableId) { setTab(current); setSelectionLoading(false); }
      setConnected(true); setLoaded(true);
    } catch {
      if (generation !== epoch.current) return;
      setConnected(false); setLoaded(true);
      setSelectionLoading(false);
    } finally {
      refreshing.current = false;
      if (refreshAgain.current) { refreshAgain.current = false; void refresh(); }
    }
  }, [user.role]);

  useEffect(() => {
    function restore() {
      if (gate.current) return;
      try {
        const command = readPending(localStorage);
        pendingRef.current = command; setPending(command); setStorageError(false);
      } catch {
        setStorageError(true);
        setError('Tarayıcı işlem kaydı okunamadı. Yeni işlemden önce bekleyen kayıt kontrol edilmeli.');
      }
    }
    restore();
    window.addEventListener('storage', restore);
    void refresh();
    const timer = setInterval(() => void refresh(), 5000);
    return () => { clearInterval(timer); window.removeEventListener('storage', restore); };
  }, [refresh]);

  useEffect(() => { setConfirmed(false); }, [tab?.version, method, payment]);
  useEffect(() => {
    if (loaded && area !== 'all' && !tables.some(t => t.area === area)) setArea('all');
  }, [tables, area, loaded]);

  function selectTable(id: string|null) {
    selection.current = id; epoch.current++; setSelected(id); setTab(null); setError(''); setNotice('');
    setSelectionLoading(id !== null);
    void refresh();
  }

  async function run(command: Command, retry = false): Promise<boolean> {
    if (gate.current || (pendingRef.current && !retry)) return false;
    if (command.actorId && command.actorId !== user.id) { setError('Bekleyen işlem başka personele ait. O hesapla giriş yapın.'); return false; }
    command = {...command, actorId:user.id};
    gate.current = true; epoch.current++; setBusy(true); setError(''); setNotice('');
    try {
      // Sunucuya göndermeden önce anahtarı sakla: yenileme ve ağ kesintisinde korunur.
      savePending(localStorage, command);
      pendingRef.current = command; setPending(command);
      const result = await sendCommand(command);
      removePending(localStorage, command);
      pendingRef.current = readPending(localStorage); setPending(pendingRef.current);
      if (command.path==='/kitchen/ready/clear') {
        setNotice(`${result.cleared_count} hazır kart temizlendi.`);
      } else if (command.path.startsWith('/tabs') || command.path.startsWith('/kitchen/')) {
        if (result.table_id === selection.current) setTab(result.status === 'open' ? result : null);
        if (command.path.endsWith('/payments')) {
          setPayment(false); setNotice(`${money(result.payment!.amount_cents)} ödeme kaydedildi. Masa boşaltıldı.`);
        } else setNotice('İşlem kaydedildi.');
        setCancel(null); setReason('');
      } else {
        setInventoryRevision(value=>value+1);
        if(command.path.startsWith('/recipes/'))setRecipeRevision(value=>value+1);
        setNotice(command.path.startsWith('/recipes/')?'Reçete kaydedildi.':'Stok hareketi kaydedildi.');
      }
      setConnected(true); return true;
    } catch (err) {
      const status = err instanceof ApiError ? err.status : 0;
      if (status >= 400 && status < 500 && status !== 401 && status !== 403) {
        removePending(localStorage, command);
        pendingRef.current = readPending(localStorage); setPending(pendingRef.current);
        setPayment(false); setCancel(null);
      }
      setError(err instanceof Error ? err.message : 'İşlem tamamlanamadı.');
      if (!status || status >= 500) setConnected(false);
      return false;
    } finally {
      gate.current = false; setBusy(false); void refresh();
    }
  }

  function mutate(suffix: string, data: Record<string,unknown> = {}, method = 'POST') {
    if (!tab) return;
    void run(createCommand(`/tabs/${tab.id}${suffix}`, {expected_version:tab.version,...data}, method));
  }

  const table = tables.find(t => t.id === selected);
  const locked = busy || !!pending || !connected || selectionLoading || storageError;
  const active = tab?.items.filter(i => i.status !== 'cancelled') || [];
  const canPay = !!tab && active.length > 0 && active.every(i => i.status === 'ready') && tab.total_cents > 0;
  const shown = products.filter(p => (category === 'all' || p.category_id === category) && p.name.toLocaleLowerCase('tr').includes(search.toLocaleLowerCase('tr')));
  const occupied = tables.filter(t => t.status === 'occupied').length;

  return <div className="app-shell">
    <aside className="rail">
      <div className="brand-mark"><Coffee size={25}/></div>
      <span className="rail-label">CAFE<span>ERP</span></span>
      <nav aria-label="Ana menü">
        {user.role!=='kitchen' && <button className={view==='tables'?'nav-item active':'nav-item'} onClick={() => setView('tables')}><Grid2X2 size={21}/><span>Masalar</span></button>}
        <button className={view==='kitchen'?'nav-item active':'nav-item'} onClick={() => setView('kitchen')}><ChefHat size={23}/><span>Mutfak</span></button>
        {user.role==='admin' && <button className={view==='inventory'?'nav-item active':'nav-item'} onClick={()=>setView('inventory')}><Soup size={22}/><span>Stok</span></button>}
        {user.role==='admin' && <button className={view==='staff'?'nav-item active':'nav-item'} onClick={()=>setView('staff')}><Grid2X2 size={21}/><span>Personel</span></button>}
      </nav>
    </aside>
    <div className="workspace">
      <header className="topbar"><div><span className="eyebrow">İŞLETME ÇALIŞMA ALANI</span><div className="text-sm font-medium mt-1">Servis yönetimi <span className="text-stone-300 mx-2">/</span> {view==='inventory'?'Stok ve reçeteler':view==='staff'?'Personel':view==='kitchen'?'Mutfak':selected?table?.name || 'Masa':'Masalar'}</div></div><div className={`connection ${connected?'':'offline'}`}>{connected?<Wifi size={15}/>:<WifiOff size={15}/>}<span>{connected?'Bağlı':loaded?'Bağlantı yok':'Bağlanıyor…'}</span></div><div className="session-menu"><span>{user.name} · {roleNames[user.role]}</span><Button variant="outline" disabled={busy} onClick={()=>{if(!gate.current)onSwitch();}}>Personel değiştir</Button><Button variant="outline" disabled={busy} onClick={async()=>{try{await request('/auth/logout',{method:'POST'});window.location.reload();}catch(err){setError(err instanceof Error?err.message:'Çıkış yapılamadı.');}}}>Çıkış</Button></div></header>
      <main>
        {view==='staff' && user.role==='admin' && <StaffPanel user={user}/>}
        {pending && <div className="alert warning" role="alert"><div><strong>{pending.actorId && pending.actorId!==user.id?'Bekleyen işlem başka personele ait; o hesapla giriş yapın.':'Son işlemin sonucu doğrulanmalı.'}</strong><p>Yeni işlemden önce aynı isteği güvenle tekrar gönderin. Sayfayı yenilemek işlemi iptal etmez.</p></div><Button disabled={busy || (!!pending.actorId && pending.actorId!==user.id)} onClick={() => void run(pending,true)}>{busy?<LoaderCircle className="animate-spin" size={16}/>:null}Sonucu kontrol et</Button></div>}
        {error && <div className="alert error" role="alert">{error}<button onClick={() => setError('')} aria-label="Uyarıyı kapat"><X size={17}/></button></div>}
        {notice && <div className="alert success" role="status"><Check size={17}/>{notice}</div>}
        {!connected && loaded && <div className="alert warning"><span>Sunucuya ulaşılamıyor. Son görüntülenen bilgiler güncel olmayabilir; yeni işlemler bekletiliyor.</span><Button variant="outline" onClick={() => void refresh()}>Yeniden bağlan</Button></div>}
        {view==='inventory' && user.role==='admin' && <InventoryPanel locked={locked} busy={busy} hasPending={!!pending} revision={inventoryRevision} recipeRevision={recipeRevision} onCommand={run} commandError={error}/>}
        {view==='tables' && !selected && <>
          <div className="page-heading"><div><h1>Servise hazır.</h1><p>Sipariş almak veya açık hesabı görmek için bir masa seçin.</p></div><div className="summary"><span className="summary-dot"/><strong>{occupied}</strong> dolu <span className="text-stone-300">/</span><strong>{tables.length-occupied}</strong> boş</div></div>
          <div className="section-toolbar"><div className="tabs"><button className={area==='all'?'selected':''} onClick={() => setArea('all')}>Tüm alanlar</button>{Array.from(new Set(tables.map(t => t.area))).map(a => <button key={a} className={area===a?'selected':''} onClick={() => setArea(a)}>{a}</button>)}</div><span className="text-xs text-stone-400">{tables.length} masa</span></div>
          {!loaded?<div className="empty"><LoaderCircle className="animate-spin"/>Masalar yükleniyor…</div>:tables.length===0?<div className="empty">Gösterilecek masa bulunamadı.</div>:<div className="table-grid">{tables.filter(t => area==='all'||t.area===area).map((t,index) => {
            const open = openTabs.find(o => o.table_id===t.id);
            return <button key={t.id} className={`table-card ${t.status==='occupied'?'occupied':''}`} onClick={() => selectTable(t.id)}><div className="flex justify-between items-start"><span className="table-index">{String(index+1).padStart(2,'0')}</span><span className="pill">{t.status==='occupied'?'Dolu':'Boş'}</span></div><Armchair className="table-icon" size={38} strokeWidth={1.3}/><h2>{t.name}</h2><p>{t.area}</p><div className="table-footer">{open?`${new Date(open.opened_at).toLocaleTimeString('tr-TR',{hour:'2-digit',minute:'2-digit'})} · Açık adisyon`:'Siparişe başla'}<ArrowRight size={16}/></div></button>;
          })}</div>}
          <div className="footnote"><span className="summary-dot"/> Masalar açık adisyonlara göre güncellenir.</div>
        </>}
        {view==='tables' && selected && <>
          <div className="order-heading"><Button variant="outline" onClick={() => selectTable(null)} disabled={busy}><ArrowLeft size={17}/>Masalar</Button><div><h1>{table?.name || 'Masa'}</h1><p>{table?.area} <span className="mx-2">·</span>{tab?`Adisyon #${tab.id}`:'Yeni sipariş'}</p></div><span className="pill ml-auto">{tab?'Açık adisyon':'Boş masa'}</span></div>
          <div className="pos-layout"><section className="catalog"><div className="search"><Search size={19}/><input aria-label="Ürün ara" placeholder="Menüde bir ürün ara…" value={search} onChange={e => setSearch(e.target.value)}/><kbd>MENÜ</kbd></div><div className="tabs category-tabs"><button className={category==='all'?'selected':''} onClick={() => setCategory('all')}>Tümü</button>{categories.map(c => <button key={c.id} className={category===c.id?'selected':''} onClick={() => setCategory(c.id)}>{c.name}</button>)}</div><div className="product-grid">{shown.map(p => <button disabled={locked || !tab} className={`product-card type-${p.type}`} key={p.id} onClick={() => mutate('/items',{product_id:p.id,quantity:1})}><div className="product-top">{p.type==='food'?<Soup size={27} strokeWidth={1.5}/>:<Coffee size={27} strokeWidth={1.5}/>}<Plus size={18}/></div><h2>{p.name}</h2><span>{new Intl.NumberFormat('tr-TR',{style:'currency',currency:'TRY'}).format(p.price)}</span></button>)}</div>{shown.length===0 && <div className="empty">Aramanıza uygun ürün bulunamadı.</div>}</section>
          <aside className="bill"><div className="bill-header"><div><span className="eyebrow">MASA HESABI</span><h2>Adisyon</h2></div><span className="count">{active.length} kalem</span></div>
            {!tab?<div className="empty bill-empty"><Coffee size={36} strokeWidth={1.3}/><h3>İlk siparişi alalım.</h3><p>Adisyonu açtıktan sonra menüden ürün ekleyebilirsiniz.</p><Button disabled={locked} onClick={() => void run(createCommand('/tabs',{table_id:selected}))}><Plus size={17}/>Adisyon aç</Button></div>:<>
              <div className="bill-items">{tab.items.length===0 && <div className="empty">Menüden ürün seçerek başlayın.</div>}{tab.items.map(i => <div key={i.id} className={`bill-item ${i.status==='cancelled'?'cancelled':''}`}><div className="flex justify-between gap-2"><h3>{i.product_name}</h3><span>{money(i.unit_price_cents)}</span></div><div className="flex items-center justify-between mt-3"><span className={`status status-${i.status}`}>{statusNames[i.status]}</span><div className="quantity">{i.status==='draft'?<><button disabled={locked} aria-label={`${i.product_name} azalt`} onClick={() => mutate(`/items/${i.id}`,{quantity:i.quantity-1},'PATCH')}><Minus size={14}/></button><span>× {i.quantity}</span><button disabled={locked||i.quantity>=10000} aria-label={`${i.product_name} artır`} onClick={() => mutate(`/items/${i.id}`,{quantity:i.quantity+1},'PATCH')}><Plus size={14}/></button></>:<span>× {i.quantity}</span>}{canCancelItem(user.role,i.status) && <button className="delete" disabled={locked} aria-label={`${i.product_name} iptal et`} onClick={() => {setReason('');setCancel({item:i});}}><Trash2 size={14}/></button>}</div></div></div>)}</div>
              <div className="bill-bottom"><div className="total"><span>Toplam hesap</span><strong>{money(tab.total_cents)}</strong></div><p className="text-xs text-stone-400 mb-4">Tutar, kayıtlı ürün fiyatları üzerinden hesaplanır.</p><Button className="w-full mb-2" disabled={locked || !active.some(i=>i.status==='draft')} onClick={() => mutate('/submit')}><Send size={17}/>Mutfağa gönder</Button><Button variant="outline" className="w-full" disabled={locked||!canPay||!['admin','cashier'].includes(user.role)} onClick={() => setPayment(true)}><CreditCard size={17}/>Ödeme al</Button>{!canPay && active.length>0 && <p className="text-xs text-stone-500 mt-3">Ödeme için tüm aktif ürünler hazır olmalı.</p>}<button className="text-xs text-stone-400 hover:text-red-600 mt-5 underline underline-offset-4" disabled={locked||!canCancelTab(user.role,tab.items)} onClick={() => {setReason('');setCancel({});}}>Adisyonu iptal et</button>{!canCancelTab(user.role,tab.items) && <p className="text-xs text-stone-500 mt-3">Hazırlığı başlayan ürünleri mutfak veya yönetici iptal edebilir.</p>}</div>
            </>}
          </aside></div>
        </>}
        {view==='kitchen' && <><div className="page-heading"><div><span className="eyebrow">BİRLİKTE, TAM ZAMANINDA</span><h1>Mutfak akışı.</h1><p>Gönderilen siparişleri takip edin, hazırlık durumunu güncelleyin.</p></div><div className="summary"><ChefHat size={20}/><strong>{kitchen.filter(i=>i.status!=='ready').length}</strong> bekleyen kalem</div></div><div className="kitchen-grid">{(['sent','preparing','ready'] as const).map(state => <section key={state} className="kitchen-column"><h2 className={state==='ready'?'kitchen-ready-heading':undefined}><span className={`status status-${state}`}>{statusNames[state]}</span>{state==='ready' && <Button className="min-h-7 h-7 px-2 text-[11px] gap-1 rounded-lg" variant="outline" disabled={locked||!kitchen.some(i=>i.status==='ready')||!['admin','kitchen'].includes(user.role)} onClick={()=>void run(createCommand('/kitchen/ready/clear',{item_ids:kitchen.filter(i=>i.status==='ready').slice(0,1000).map(i=>i.id)}))}><CheckCheck size={12}/>Temizle</Button>}<span>{kitchen.filter(i=>i.status===state).length}</span></h2>{kitchen.filter(i=>i.status===state).map(i => <article className="kitchen-card" key={i.id}><div className="flex justify-between text-xs text-stone-400"><span>{i.table_name}</span><span>{new Date(i.created_at).toLocaleTimeString('tr-TR',{hour:'2-digit',minute:'2-digit'})} · Eklendi</span></div><h3><b>{i.quantity}×</b> {i.product_name}</h3>{state==='ready'?<div className="text-sm text-emerald-700 flex gap-2 items-center"><CheckCheck size={17}/>Servise hazır</div>:<Button className="w-full" variant={state==='sent'?'outline':'default'} disabled={locked||!['admin','kitchen'].includes(user.role)} onClick={() => void run(createCommand(`/tabs/${i.tab_id}/items/${i.id}/status`,{expected_version:i.version,status:state==='sent'?'preparing':'ready'},'PATCH'))}>{state==='sent'?<ChefHat size={16}/>:<Check size={16}/>} {state==='sent'?'Hazırlamaya başla':'Hazır işaretle'}</Button>}{canCancelItem(user.role,i.status) && <Button variant="destructive" className="w-full mt-3" disabled={locked} onClick={()=>{setReason('');setCancel({item:i,kitchenItem:i});}}><Trash2 size={16}/>Ürünü iptal et</Button>}</article>)}{!kitchen.some(i=>i.status===state) && <div className="column-empty">Bu aşamada sipariş yok.</div>}</section>)}</div></>}
      </main>
    </div>
    <Modal open={payment} onOpenChange={v=>{if(!busy)setPayment(v);}} title="Hesabı kapat" description={`${table?.name || 'Masa'} · Tek seferde tam ödeme kaydı`}><div className="payment-total">{money(tab?.total_cents || 0)}</div><div className="grid grid-cols-2 gap-3 my-5"><Button variant={method==='cash'?'default':'outline'} onClick={()=>setMethod('cash')} disabled={locked}><Banknote size={20}/>Nakit</Button><Button variant={method==='card'?'default':'outline'} onClick={()=>setMethod('card')} disabled={locked}><CreditCard size={20}/>Kart</Button></div><label className="confirm-label"><input type="checkbox" checked={confirmed} onChange={e=>setConfirmed(e.target.checked)} disabled={locked}/><span>{method==='card'?'Harici POS cihazında ödeme başarıyla alındı.':'Nakit tahsilat alındı.'}</span></label><Button className="w-full mt-6" disabled={locked||!confirmed||!canPay} onClick={()=>mutate('/payments',{amount_cents:tab!.total_cents,method})}>{busy?<LoaderCircle className="animate-spin" size={17}/>:<Check size={17}/>}Ödemeyi kaydet ve kapat</Button></Modal>
    <Modal open={!!cancel} onOpenChange={v=>{if(!v&&!busy)setCancel(null);}} title={cancel?.item?'Ürünü iptal et':'Adisyonu iptal et'} description={cancel?.item?`${cancel.item.product_name} kaydı silinmeden iptal edilecek.`:'Tüm aktif kalemler iptal edilir ve masa boşaltılır.'}><label className="block text-sm font-medium mb-2" htmlFor="reason">İptal gerekçesi</label><textarea id="reason" maxLength={500} value={reason} onChange={e=>setReason(e.target.value)} placeholder="Örneğin: Müşteri siparişini değiştirdi" className="reason-input"/><div className="alert warning mt-4" role="alert">{cancel?.item?`${cancel.item.quantity}× ${cancel.item.product_name} iptal edilecek ve hesap toplamından çıkarılacak. ${['preparing','ready'].includes(cancel.item.status)?'Başlayan üretimin tüketimi zayiat olarak işaretlenir; stok otomatik geri eklenmez.':'Henüz hazırlık başlamadıysa stok etkilenmez.'}`:'Adisyondaki tüm aktif ürünler iptal edilecek ve masa boşaltılacak.'}</div><div className="flex gap-3 mt-4"><Button variant="outline" disabled={busy} onClick={()=>setCancel(null)}>Vazgeç</Button><Button variant="destructive" className="flex-1" disabled={locked||!reason.trim()} onClick={()=>{const item=cancel?.kitchenItem;if(item)void run(createCommand(`/kitchen/items/${item.id}/cancel`,{tab_id:item.tab_id,expected_version:item.version,reason:reason.trim()}));else mutate(cancel?.item?`/items/${cancel.item.id}/cancel`:'/cancel',{reason:reason.trim()});}}>Evet, iptal et</Button></div></Modal>
  </div>;
}
