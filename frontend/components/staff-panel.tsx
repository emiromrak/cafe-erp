'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { request } from '@/lib/api.mjs';
import { roleNames, type Staff } from '@/lib/staff';

export function StaffPanel({user}:{user:Staff}) {
  const [staff, setStaff] = useState<Staff[]>([]);
  const [selected, setSelected] = useState<Staff|null>(null);
  const [username, setUsername] = useState('');
  const [name, setName] = useState('');
  const [role, setRole] = useState<Staff['role']>('waiter');
  const [active, setActive] = useState(true);
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  async function load() { setStaff(await request('/auth/staff')); }
  useEffect(() => { void load().catch(err=>setError(err.message)); }, []);
  function select(account:Staff|null) {
    setSelected(account); setUsername(account?.username || ''); setName(account?.name || '');
    setRole(account?.role || 'waiter'); setActive(account?.is_active ?? true); setPassword(''); setError(''); setNotice('');
  }
  return <>
    <div className="page-heading"><div><h1>Personel hesapları.</h1><p>Rolleri ve erişimi yönetin. Kaydedilen değişiklik personelin açık oturumlarını kapatır.</p></div><Button variant="outline" disabled={busy} onClick={()=>select(null)}>Yeni personel</Button></div>
    {error && <div className="alert error" role="alert">{error}</div>}
    {notice && <div className="alert success" role="status">{notice}</div>}
    <div className="staff-layout"><section className="staff-list" aria-label="Personel listesi">{staff.map(account=><button disabled={busy} className={selected?.id===account.id?'selected':''} key={account.id} onClick={()=>select(account)}><strong>{account.name}{account.id===user.id?' (siz)':''}</strong><span>{account.username} · {roleNames[account.role]} · {account.is_active?'Aktif':'Pasif'}</span></button>)}</section>
    <form className="staff-form" onSubmit={async e=>{
      e.preventDefault(); setBusy(true); setError(''); setNotice('');
      try {
        await request(selected?`/auth/staff/${selected.id}`:'/auth/staff', {method:selected?'PATCH':'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(selected?
          {name,role,is_active:active,expected_version:selected.version,...(password?{password}:{})}:{username,name,role,password})});
        setPassword('');
        if (selected?.id===user.id) { window.dispatchEvent(new Event('cafeerp-session-ended')); return; }
        select(null); setNotice('Personel kaydı kaydedildi.'); await load();
      } catch (err) { setError(err instanceof Error?err.message:'Kayıt tamamlanamadı. Listeyi yenileyin.'); }
      finally { setBusy(false); }
    }}><h2>{selected?'Personeli düzenle':'Yeni personel hesabı'}</h2>
      <label>Kullanıcı adı<input autoComplete="off" value={username} onChange={e=>setUsername(e.target.value.toLowerCase())} disabled={busy||!!selected} required pattern="[a-z0-9_.\-]{3,50}" maxLength={50}/></label>
      <label>Ad soyad<input autoComplete="off" value={name} onChange={e=>setName(e.target.value)} required maxLength={100} disabled={busy}/></label>
      <label>Rol<select value={role} onChange={e=>setRole(e.target.value as Staff['role'])} disabled={busy}>{Object.entries(roleNames).map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label>
      <label>{selected?'Yeni sayısal parola (değişmeyecekse boş bırakın)':'Parola (yalnızca rakam, en az 4 hane)'}<input type="password" inputMode="numeric" pattern="[0-9]{4,128}" title="Yalnızca 0–9 rakamları, en az 4 hane" autoComplete="new-password" value={password} onChange={e=>setPassword(e.target.value)} required={!selected} minLength={4} maxLength={128} disabled={busy}/></label>
      {selected && <label className="confirm-label"><input type="checkbox" checked={active} onChange={e=>setActive(e.target.checked)} disabled={busy}/>Hesap aktif</label>}
      <Button disabled={busy}>{busy?'Kaydediliyor…':'Kaydet'}</Button>
      <p>Garson sipariş alır; mutfak hazırlığı ilerletir; kasiyer ödeme kaydeder. Yönetici tüm işlemlere erişir.</p>
    </form></div>
  </>;
}
