// Yanıtı belirsiz kalan yazmalar aynı anahtar ve gövdeyle tekrar gönderilir.
export class ApiError extends Error {
  constructor(message, status) { super(message); this.status = status; }
}
export async function request(path, options = {}, transport = fetch) {
  let response;
  try {
    response = await transport(`/api${path}`, { ...options, cache: 'no-store', signal: AbortSignal.timeout(15000) });
  } catch {
    throw new ApiError('Sunucu yanıtı alınamadı. İşlemin sonucu kontrol edilmeli.', 0);
  }
  let data;
  try { data = await response.json(); } catch {
    throw new ApiError('Sunucudan okunabilir yanıt alınamadı.', response.ok ? 0 : response.status);
  }
  if (!response.ok) throw new ApiError(typeof data.detail === 'string' ? data.detail : 'İstek doğrulanamadı. Bilgileri kontrol edin.', response.status);
  return data;
}
export function createCommand(path, body, method = 'POST') {
  return { path, body, method, key: crypto.randomUUID() };
}
export async function sendCommand(command, transport = fetch) {
  return request(command.path, { method: command.method, headers: { 'Content-Type': 'application/json', 'Idempotency-Key': command.key }, body: JSON.stringify(command.body) }, transport);
}
