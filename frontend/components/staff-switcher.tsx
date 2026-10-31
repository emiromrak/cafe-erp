'use client';

import { useEffect, useRef, useState } from 'react';
import { ArrowLeft, Delete, LoaderCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Modal } from '@/components/ui/dialog';
import { request } from '@/lib/api.mjs';
import { roleNames, type Staff } from '@/lib/staff';

type Choice = Pick<Staff,'id'|'username'|'name'|'role'>;

export function StaffSwitcher({user,onClose,onChanged}:{user:Staff;onClose:()=>void;onChanged:(user:Staff)=>void}) {
  const [staff,setStaff] = useState<Choice[]>([]);
  const [selected,setSelected] = useState<Choice|null>(null);
  const [password,setPassword] = useState('');
  const [loading,setLoading] = useState(true);
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState('');
  const input = useRef<HTMLInputElement>(null);
  const gate = useRef(false);

  useEffect(()=>{
    let alive=true;
    request('/auth/switchable-staff').then((accounts:Choice[])=>{if(alive)setStaff(accounts);})
      .catch((err:Error)=>{if(alive)setError(err.message);})
      .finally(()=>{if(alive)setLoading(false);});
    return ()=>{alive=false;};
  },[]);

  async function submit() {
    if (gate.current || !selected || password.length<4) return;
    gate.current=true; setBusy(true); setError('');
    try {
      const next:Staff = await request('/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({username:selected.username,password})});
      setPassword(''); onChanged(next);
    } catch(err) {
      setPassword(''); setError(err instanceof Error?err.message:'Personel değiştirilemedi.');
    } finally { gate.current=false; setBusy(false); input.current?.focus(); }
  }

  return <Modal open onOpenChange={open=>{if(!open&&!busy)onClose();}} title="Personel değiştir"
    description="Hesabını seç, parolanı gir ve devam et.">
    {error && <div className="alert error" role="alert">{error}</div>}
    {loading?<div className="empty"><LoaderCircle className="animate-spin"/>Personel yükleniyor…</div>:selected?
      <form onSubmit={e=>{e.preventDefault();void submit();}}>
        <Button type="button" variant="outline" disabled={busy} onClick={()=>{setSelected(null);setPassword('');setError('');}}><ArrowLeft size={16}/>Hesaplar</Button>
        <div className="switch-account"><strong>{selected.name}</strong><span>{roleNames[selected.role]}</span></div>
        <label className="switch-password" htmlFor="switch-password">Parola
          <input ref={input} id="switch-password" type="password" inputMode="numeric" autoFocus autoComplete="off" minLength={4} maxLength={128}
            required value={password} onChange={e=>setPassword(e.target.value)} readOnly={busy}/>
        </label>
        <div className="switch-keypad" aria-label="Sayısal parola tuşları">
          {['1','2','3','4','5','6','7','8','9'].map(digit=><button type="button" disabled={busy||password.length>=128} key={digit}
            onClick={()=>setPassword(value=>value+digit)}>{digit}</button>)}
          <button type="button" disabled={busy||!password} onClick={()=>setPassword('')}>Temizle</button>
          <button type="button" disabled={busy||password.length>=128} onClick={()=>setPassword(value=>value+'0')}>0</button>
          <button type="button" aria-label="Son karakteri sil" disabled={busy||!password} onClick={()=>setPassword(value=>value.slice(0,-1))}><Delete size={21}/></button>
        </div>
        <Button className="w-full" disabled={busy||password.length<4}>{busy?<LoaderCircle size={17} className="animate-spin"/>:null}Geçiş yap</Button>
      </form>:
      <div className="switch-accounts">{staff.filter(account=>account.id!==user.id).map(account=><button type="button" key={account.id}
        onClick={()=>{setSelected(account);setPassword('');setError('');}}><strong>{account.name}</strong><span>{roleNames[account.role]}</span></button>)}
        {!staff.some(account=>account.id!==user.id) && <p>Geçiş yapılabilecek başka aktif personel yok. Yönetici Personel ekranından hesap açabilir.</p>}
      </div>}
  </Modal>;
}
