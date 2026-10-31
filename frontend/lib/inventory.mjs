// Miktarları float'a çevirmeden SQL'in 14 tam / 6 ondalık basamak sınırında tutar.
export function parseQuantity(input) {
  const value = input.trim().replace(',', '.');
  if (!/^[0-9]+(?:\.[0-9]{1,6})?$/.test(value)) throw new Error('Miktar pozitif olmalı; en fazla 6 ondalık basamak kullanın.');
  const [whole, fraction] = value.split('.');
  const integer = whole.replace(/^0+(?=\d)/, '');
  if (integer.length > 14 || !/[1-9]/.test(integer + (fraction || ''))) throw new Error('Miktar sıfırdan büyük ve 100 trilyondan küçük olmalı.');
  return integer + (fraction === undefined ? '' : `.${fraction}`);
}

export function recipePayload(version, lines, reason) {
  if (!lines.length || lines.length > 100) throw new Error('Reçetede 1–100 hammadde bulunmalı.');
  if (!reason.trim() || reason.trim().length > 500) throw new Error('Kaydetmek için en fazla 500 karakterlik bir gerekçe yazın.');
  const ids = new Set();
  return {expected_version:version, reason:reason.trim(), lines:lines.map(line=>{
    if (!line.material_id || ids.has(line.material_id)) throw new Error('Her hammaddeyi seçin ve reçeteye yalnızca bir kez ekleyin.');
    ids.add(line.material_id);
    return {material_id:line.material_id, quantity:parseQuantity(line.quantity)};
  })};
}

export function formatQuantity(value) {
  const [integer,fraction=''] = String(value).split('.');
  const decimals=fraction.replace(/0+$/, '');
  return integer.replace(/\B(?=(\d{3})+(?!\d))/g, '.') + (decimals?`,${decimals}`:'');
}
