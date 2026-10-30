'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { Armchair, ArrowLeft, ArrowRight, Banknote, Check, CheckCheck, ChefHat, Coffee, CreditCard, Grid2X2, Leaf, LoaderCircle, Minus, Plus, Search, Send, Soup, Trash2, Wifi, WifiOff, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Modal } from '@/components/ui/dialog';
import { ApiError, createCommand, request, sendCommand } from '@/lib/api.mjs';
import type { Category, Item, KitchenItem, OpenTab, Product, Tab, Table } from '@/lib/types';

const money = (cents: number) => new Intl.NumberFormat('tr-TR', {style:'currency',currency:'TRY'}).format(cents / 100);
const statusNames: Record<Item['status'], string> = {draft:'Gönderilmedi', sent:'Bekliyor', preparing:'Hazırlanıyor', ready:'Hazır', cancelled:'İptal edildi'};
const STORAGE = 'cafe-erp-pending-v1';
type Command = ReturnType<typeof createCommand>;

export default function POS() {
  const [view, setView] = useState<'tables'|'kitchen'>('tables');
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
  const [pending, setPending] = useState<Command|null>(null);
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const [payment, setPayment] = useState(false);
  const [method, setMethod] = useState<'cash'|'card'>('cash');
  const [confirmed, setConfirmed] = useState(false);
  const [cancel, setCancel] = useState<{item?:Item}|null>(null);
  const [reason, setReason] = useState('');
  const gate = useRef(false);
  const selection = useRef<string|null>(null);
  const epoch = useRef(0);
  const pendingRef = useRef<Command|null>(null);

  const refresh = useCallback(async () => {
    if (gate.current) return;
    const generation = epoch.current;
    const tableId = selection.current;
    try {
      const [ts, ps, cs, os, ks] = await Promise.all([
        request('/tables'), request('/products'), request('/categories'), request('/tabs'), request('/kitchen/items')
      ]);
      const open = (os as OpenTab[]).find(t => t.table_id === tableId);
      const current: Tab|null = open ? await request(`/tabs/${open.id}`) : null;
      if (generation !== epoch.current || gate.current) return;
      setTables(ts); setProducts(ps); setCategories(cs); setOpenTabs(os); setKitchen(ks);
      if (selection.current === tableId) setTab(current);
      setConnected(true); setLoaded(true);
    } catch {
      if (generation !== epoch.current) return;
      setConnected(false); setLoaded(true);
    }
  }, []);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE);
      if (raw) {
        const command = JSON.parse(raw);
        if (typeof command.path === 'string' && typeof command.key === 'string' && command.body && ['POST','PATCH'].includes(command.method)) {
          pendingRef.current = command; setPending(command);
        } else localStorage.removeItem(STORAGE);
      }
    } catch { setError('Tarayıcı işlem kaydı okunamadı. Yeni işlemden önce bağlantınızı kontrol edin.'); }
    void refresh();
    const timer = setInterval(() => void refresh(), 5000);
    return () => clearInterval(timer);
  }, [refresh]);

  useEffect(() => { setConfirmed(false); }, [tab?.version, method, payment]);

  function selectTable(id: string|null) {
    selection.current = id; epoch.current++; setSelected(id); setTab(null); setError(''); setNotice('');
    void refresh();
  }

  async function run(command: Command, retry = false) {
    if (gate.current || (pendingRef.current && !retry)) return;
    gate.current = true; epoch.current++; setBusy(true); setError(''); setNotice('');
    try {
      // Sunucuya göndermeden önce anahtarı sakla: yenileme ve ağ kesintisinde korunur.
      localStorage.setItem(STORAGE, JSON.stringify(command));
      pendingRef.current = command; setPending(command);
      const result: Tab = await sendCommand(command);
      localStorage.removeItem(STORAGE); pendingRef.current = null; setPending(null);
      if (result.table_id === selection.current) setTab(result.status === 'open' ? result : null);
      if (command.path.endsWith('/payments')) {
        setPayment(false); setNotice(`${money(result.payment!.amount_cents)} ödeme kaydedildi. Masa boşaltıldı.`);
      } else setNotice('İşlem kaydedildi.');
      setCancel(null); setReason(''); setConnected(true);
    } catch (err) {
      const status = err instanceof ApiError ? err.status : 0;
      if (status >= 400 && status < 500) {
        localStorage.removeItem(STORAGE); pendingRef.current = null; setPending(null);
        setPayment(false); setCancel(null);
      }
      setError(err instanceof Error ? err.message : 'İşlem tamamlanamadı.');
      if (!status || status >= 500) setConnected(false);
    } finally {
      gate.current = false; setBusy(false); void refresh();
    }
  }

  function mutate(suffix: string, data: Record<string,unknown> = {}, method = 'POST') {
    if (!tab) return;
    void run(createCommand(`/tabs/${tab.id}${suffix}`, {expected_version:tab.version,...data}, method));
  }

  const table = tables.find(t => t.id === selected);
  const locked = busy || !!pending || !connected;
  const active = tab?.items.filter(i => i.status !== 'cancelled') || [];
  const canPay = !!tab && active.length > 0 && active.every(i => i.status === 'ready') && tab.total_cents > 0;
  const shown = products.filter(p => (category === 'all' || p.category_id === category) && p.name.toLocaleLowerCase('tr').includes(search.toLocaleLowerCase('tr')));
  const occupied = tables.filter(t => t.status === 'occupied').length;

  return <div className="app-shell">
    <aside className="rail">
      <div className="brand-mark"><Coffee size={25}/></div>
      <span className="rail-label">CAFE<span>ERP</span></span>
      <nav aria-label="Ana menü">
        <button className={view==='tables'?'nav-item active':'nav-item'} onClick={() => setView('tables')}><Grid2X2 size={21}/><span>Servis</span></button>
        <button className={view==='kitchen'?'nav-item active':'nav-item'} onClick={() => setView('kitchen')}><ChefHat size={23}/><span>Mutfak</span></button>
      </nav>
      <div className="rail-bottom"><Leaf size={21}/><span>Masa servisi</span></div>
    </aside>
    <div className="workspace">
      <header className="topbar"><div><span className="eyebrow">İŞLETME ÇALIŞMA ALANI</span><div className="text-sm font-medium mt-1">Servis yönetimi <span className="text-stone-300 mx-2">/</span> {view==='kitchen'?'Mutfak':selected?table?.name || 'Masa':'Masalar'}</div></div><div className={`connection ${connected?'':'offline'}`}>{connected?<Wifi size={15}/>:<WifiOff size={15}/>}<span>{connected?'Bağlı · 5 sn yenileme':'Bağlantı bekleniyor'}</span></div></header>
      <main>
        {pending && <div className="alert warning" role="alert"><div><strong>Son işlemin sonucu doğrulanmalı.</strong><p>Yeni işlemden önce aynı isteği güvenle tekrar gönderin. Sayfayı yenilemek işlemi iptal etmez.</p></div><Button disabled={busy} onClick={() => void run(pending,true)}>{busy?<LoaderCircle className="animate-spin" size={16}/>:null}Sonucu kontrol et</Button></div>}
        {error && <div className="alert error" role="alert">{error}<button onClick={() => setError('')} aria-label="Uyarıyı kapat"><X size={17}/></button></div>}
        {notice && <div className="alert success" role="status"><Check size={17}/>{notice}</div>}
        {!connected && <div className="alert warning"><span>Sunucuya ulaşılamıyor. Son görüntülenen bilgiler güncel olmayabilir; yeni işlemler bekletiliyor.</span><Button variant="outline" onClick={() => void refresh()}>Yeniden bağlan</Button></div>}
        {view==='tables' && !selected && <>
          <div className="page-heading"><div><span className="eyebrow">HER MASADA İYİ BİR DENEYİM</span><h1>Servise hazır.</h1><p>Sipariş almak veya açık hesabı görmek için bir masa seçin.</p></div><div className="summary"><span className="summary-dot"/><strong>{occupied}</strong> dolu <span className="text-stone-300">/</span><strong>{tables.length-occupied}</strong> boş</div></div>
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
              <div className="bill-items">{tab.items.length===0 && <div className="empty">Menüden ürün seçerek başlayın.</div>}{tab.items.map(i => <div key={i.id} className={`bill-item ${i.status==='cancelled'?'cancelled':''}`}><div className="flex justify-between gap-2"><h3>{i.product_name}</h3><span>{money(i.unit_price_cents)}</span></div><div className="flex items-center justify-between mt-3"><span className={`status status-${i.status}`}>{statusNames[i.status]}</span><div className="quantity">{i.status==='draft'?<><button disabled={locked||i.quantity<=1} aria-label={`${i.product_name} azalt`} onClick={() => mutate(`/items/${i.id}`,{quantity:i.quantity-1},'PATCH')}><Minus size={14}/></button><span>{i.quantity}</span><button disabled={locked||i.quantity>=10000} aria-label={`${i.product_name} artır`} onClick={() => mutate(`/items/${i.id}`,{quantity:i.quantity+1},'PATCH')}><Plus size={14}/></button></>:<span>× {i.quantity}</span>}{i.status!=='cancelled' && <button className="delete" disabled={locked} aria-label={`${i.product_name} iptal et`} onClick={() => {setReason('');setCancel({item:i});}}><Trash2 size={14}/></button>}</div></div></div>)}</div>
              <div className="bill-bottom"><div className="total"><span>Toplam hesap</span><strong>{money(tab.total_cents)}</strong></div><p className="text-xs text-stone-400 mb-4">Tutar, kayıtlı ürün fiyatları üzerinden hesaplanır.</p><Button className="w-full mb-2" disabled={locked || !active.some(i=>i.status==='draft')} onClick={() => mutate('/submit')}><Send size={17}/>Mutfağa gönder</Button><Button variant="outline" className="w-full" disabled={locked||!canPay} onClick={() => setPayment(true)}><CreditCard size={17}/>Ödeme al</Button>{!canPay && active.length>0 && <p className="text-xs text-stone-500 mt-3">Ödeme için tüm aktif ürünler hazır olmalı.</p>}<button className="text-xs text-stone-400 hover:text-red-600 mt-5 underline underline-offset-4" disabled={locked} onClick={() => {setReason('');setCancel({});}}>Adisyonu iptal et</button></div>
            </>}
          </aside></div>
        </>}
        {view==='kitchen' && <><div className="page-heading"><div><span className="eyebrow">BİRLİKTE, TAM ZAMANINDA</span><h1>Mutfak akışı.</h1><p>Gönderilen siparişleri takip edin, hazırlık durumunu güncelleyin.</p></div><div className="summary"><ChefHat size={20}/><strong>{kitchen.filter(i=>i.status!=='ready').length}</strong> bekleyen kalem</div></div><div className="kitchen-grid">{(['sent','preparing','ready'] as const).map(state => <section key={state} className="kitchen-column"><h2><span className={`status status-${state}`}>{statusNames[state]}</span><span>{kitchen.filter(i=>i.status===state).length}</span></h2>{kitchen.filter(i=>i.status===state).map(i => <article className="kitchen-card" key={i.id}><div className="flex justify-between text-xs text-stone-400"><span>{i.table_name}</span><span>{new Date(i.created_at).toLocaleTimeString('tr-TR',{hour:'2-digit',minute:'2-digit'})} · Eklendi</span></div><h3><b>{i.quantity}×</b> {i.product_name}</h3>{state==='ready'?<div className="text-sm text-emerald-700 flex gap-2 items-center"><CheckCheck size={17}/>Servise hazır</div>:<Button className="w-full" variant={state==='sent'?'outline':'default'} disabled={locked} onClick={() => void run(createCommand(`/tabs/${i.tab_id}/items/${i.id}/status`,{expected_version:i.version,status:state==='sent'?'preparing':'ready'},'PATCH'))}>{state==='sent'?<ChefHat size={16}/>:<Check size={16}/>} {state==='sent'?'Hazırlamaya başla':'Hazır işaretle'}</Button>}</article>)}{!kitchen.some(i=>i.status===state) && <div className="column-empty">Bu aşamada sipariş yok.</div>}</section>)}</div></>}
      </main>
      <footer className="app-footer"><span>CAFEERP <span className="text-stone-300 mx-2">/</span> Masa servisi</span><span>İyi servis, iyi bir gün.</span></footer>
    </div>
    <Modal open={payment} onOpenChange={v=>{if(!busy)setPayment(v);}} title="Hesabı kapat" description={`${table?.name || 'Masa'} · Tek seferde tam ödeme kaydı`}><div className="payment-total">{money(tab?.total_cents || 0)}</div><div className="grid grid-cols-2 gap-3 my-5"><Button variant={method==='cash'?'default':'outline'} onClick={()=>setMethod('cash')} disabled={locked}><Banknote size={20}/>Nakit</Button><Button variant={method==='card'?'default':'outline'} onClick={()=>setMethod('card')} disabled={locked}><CreditCard size={20}/>Kart</Button></div><label className="confirm-label"><input type="checkbox" checked={confirmed} onChange={e=>setConfirmed(e.target.checked)} disabled={locked}/><span>{method==='card'?'Harici POS cihazında ödeme başarıyla alındı.':'Nakit tahsilat alındı.'}</span></label><Button className="w-full mt-6" disabled={locked||!confirmed||!canPay} onClick={()=>mutate('/payments',{amount_cents:tab!.total_cents,method})}>{busy?<LoaderCircle className="animate-spin" size={17}/>:<Check size={17}/>}Ödemeyi kaydet ve kapat</Button></Modal>
    <Modal open={!!cancel} onOpenChange={v=>{if(!v&&!busy)setCancel(null);}} title={cancel?.item?'Ürünü iptal et':'Adisyonu iptal et'} description={cancel?.item?`${cancel.item.product_name} kaydı silinmeden iptal edilecek.`:'Tüm aktif kalemler iptal edilir ve masa boşaltılır.'}><label className="block text-sm font-medium mb-2" htmlFor="reason">İptal gerekçesi</label><textarea id="reason" maxLength={500} value={reason} onChange={e=>setReason(e.target.value)} placeholder="Örneğin: Müşteri siparişini değiştirdi" className="reason-input"/><Button variant="destructive" className="w-full mt-4" disabled={locked||!reason.trim()} onClick={()=>mutate(cancel?.item?`/items/${cancel.item.id}/cancel`:'/cancel',{reason:reason.trim()})}>İptali kaydet</Button></Modal>
  </div>;
}
