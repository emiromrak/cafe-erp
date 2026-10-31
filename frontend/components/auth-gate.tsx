'use client';

import { useEffect, useRef, useState } from 'react';
import { Coffee, LoaderCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ApiError, advanceSession, request } from '@/lib/api.mjs';
import { StaffSwitcher } from '@/components/staff-switcher';
import type { Staff } from '@/lib/staff';

export function AuthGate({children}:{children:(user:Staff,onSwitch:()=>void)=>React.ReactNode}) {
  const [user, setUser] = useState<Staff|null>(null);
  const [checking, setChecking] = useState(true);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [switching,setSwitching] = useState(false);
  const generation = useRef(0);

  function acceptUser(current:Staff) {
    advanceSession(); generation.current++; setPassword(''); setError(''); setUser(current); setSwitching(false);
  }

  useEffect(() => {
    let alive = true;
    const ended = () => { advanceSession(); generation.current++; setUser(null); setPassword(''); setSwitching(false); };
    async function check() {
      const checkingGeneration=generation.current;
      try {
        const current: Staff = await request('/auth/me');
        if (alive && checkingGeneration===generation.current) setUser(previous => previous?.id === current.id && previous.version === current.version ? previous : current);
      } catch (err) {
        if (alive && checkingGeneration===generation.current) {
          if (err instanceof ApiError && err.status === 401) setUser(null);
          else setError('Sunucuya ulaşılamıyor. Bağlantıyı kontrol edip yeniden deneyin.');
        }
      } finally { if (alive) setChecking(false); }
    }
    void check();
    window.addEventListener('cafeerp-session-ended', ended);
    const timer = setInterval(() => void check(), 15000);
    return () => { alive = false; clearInterval(timer); window.removeEventListener('cafeerp-session-ended', ended); };
  }, []);

  if (checking) return <div className="login-shell"><LoaderCircle className="animate-spin" aria-label="Oturum kontrol ediliyor"/></div>;
  if (user) return <>{children(user,()=>setSwitching(true))}{switching && <StaffSwitcher user={user}
    onClose={()=>setSwitching(false)} onChanged={acceptUser}/>}</>;
  return <div className="login-shell"><form className="login-card" onSubmit={async e => {
    e.preventDefault(); setBusy(true); setError('');
    try {
      const current: Staff = await request('/auth/login', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({username,password})});
      acceptUser(current);
    } catch (err) { setError(err instanceof Error ? err.message : 'Giriş yapılamadı.'); }
    finally { setBusy(false); }
  }}>
    <Coffee size={35}/><h1>CafeERP</h1><p>Servise başlamak için personel hesabınızla giriş yapın.</p>
    <label>Kullanıcı adı<input name="username" autoComplete="username" required minLength={3} maxLength={50} value={username} onChange={e=>setUsername(e.target.value)} disabled={busy}/></label>
    <label>Parola<input name="password" type="password" inputMode="numeric" autoComplete="current-password" required minLength={4} maxLength={128} value={password} onChange={e=>setPassword(e.target.value)} disabled={busy}/></label>
    {error && <div className="alert error" role="alert">{error}</div>}
    <Button className="w-full" disabled={busy}>{busy?<LoaderCircle className="animate-spin" size={17}/>:null}Giriş yap</Button>
    <p className="login-help">Hesabınız yoksa işletme yöneticisine başvurun.</p>
  </form></div>;
}
