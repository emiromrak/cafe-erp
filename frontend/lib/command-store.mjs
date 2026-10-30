// Her isteğin ayrı kaydı vardır: iki sekme birbirinin tekrar anahtarını ezmez.
const PREFIX = 'cafe-erp-pending-v1';
export function readPending(storage) {
  for (let index = 0; index < storage.length; index++) {
    const key = storage.key(index);
    if (key !== PREFIX && !key?.startsWith(`${PREFIX}:`)) continue;
    const command = JSON.parse(storage.getItem(key));
    if (!command || typeof command.path !== 'string' || typeof command.key !== 'string' ||
        !command.body || !['POST', 'PATCH'].includes(command.method)) {
      throw new Error('Bekleyen işlem kaydı okunamadı; tarayıcı kaydını kontrol edin.');
    }
    return command;
  }
  return null;
}
export function savePending(storage, command) {
  storage.setItem(`${PREFIX}:${command.key}`, JSON.stringify(command));
}
export function removePending(storage, command) {
  storage.removeItem(`${PREFIX}:${command.key}`);
  // Eski tek kayıt biçiminden kalan anahtarı yalnızca aynı işleme aitse temizle.
  const legacy = storage.getItem(PREFIX);
  if (legacy && JSON.parse(legacy).key === command.key) storage.removeItem(PREFIX);
}
