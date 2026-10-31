// Tarayıcı yalnızca kendi origin'i ile konuşur; backend adresi sunucuda kalır.
type Context = {params: Promise<{path:string[]}>};
async function forward(request: Request, context: Context) {
  const {path} = await context.params;
  if (!['auth','tabs','tables','products','categories','kitchen','inventory','recipes'].includes(path[0]) || path.some(p=>p==='.'||p==='..')) {
    return Response.json({detail:'Uç bulunamadı.'},{status:404});
  }
  const url = `${process.env.API_BASE_URL || 'http://127.0.0.1:8000'}/api/${path.map(encodeURIComponent).join('/')}${new URL(request.url).search}`;
  try {
    const headers: Record<string,string> = {'Content-Type':'application/json', 'Connection':'close'};
    const key = request.headers.get('Idempotency-Key');
    if (key) headers['Idempotency-Key'] = key;
    // Başlığı kendimiz üretmeyiz: çapraz kaynaklı formlar bu denetimi geçemez.
    for (const name of ['Cookie', 'Origin', 'X-CafeERP-Request', 'X-CafeERP-Actor']) {
      const value = request.headers.get(name);
      if (value) headers[name] = value;
    }
    const upstream = await fetch(url, {method:request.method, headers,
      body:request.method==='GET'?undefined:await request.text(), cache:'no-store', signal:AbortSignal.timeout(12000)});
    const responseHeaders = new Headers({'Content-Type':'application/json','Cache-Control':'no-store'});
    for (const cookie of upstream.headers.getSetCookie()) responseHeaders.append('Set-Cookie', cookie);
    const retryAfter = upstream.headers.get('Retry-After');
    if (retryAfter) responseHeaders.set('Retry-After', retryAfter);
    return new Response(await upstream.text(), {status:upstream.status, headers:responseHeaders});
  } catch {
    return Response.json({detail:'API bağlantısı kesildi. Son işlemin sonucunu kontrol edin.'},{status:502});
  }
}
export const GET = forward;
export const POST = forward;
export const PATCH = forward;
export const PUT = forward;
