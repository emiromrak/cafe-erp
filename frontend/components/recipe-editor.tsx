'use client';

import { useEffect, useState } from 'react';
import { Plus, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { createCommand, request } from '@/lib/api.mjs';
import { recipePayload } from '@/lib/inventory.mjs';
import type { InventoryCommand, Material, Recipe, RecipeDraft } from '@/lib/inventory-types';

export function RecipeEditor({productId,materials,locked,revision,onCommand,commandError}:{productId:string;materials:Material[];locked:boolean;revision:number;onCommand:(command:InventoryCommand)=>Promise<boolean>;commandError:string}) {
  const [recipe,setRecipe] = useState<Recipe|null>(null);
  const [lines,setLines] = useState<RecipeDraft[]>([]);
  const [reason,setReason] = useState('');
  const [loading,setLoading] = useState(true);
  const [error,setError] = useState('');
  const [reload,setReload] = useState(0);
  useEffect(()=>{
    let alive=true; setLoading(true); setError('');
    request(`/recipes/${encodeURIComponent(productId)}`).then((current:Recipe)=>{
      if(!alive)return;
      setRecipe(current); setLines(current.lines.map(line=>({material_id:line.material_id,quantity:line.quantity})));setReason('');
    }).catch((err:Error)=>{if(alive){setRecipe(null);setError(err.message);}})
      .finally(()=>{if(alive)setLoading(false);});
    return ()=>{alive=false;};
  },[productId,revision,reload]);
  const disabled=locked||loading||!recipe;
  return <form className="inventory-card recipe-form" onSubmit={async e=>{
    e.preventDefault(); if(disabled)return; setError('');
    try {
      const body=recipePayload(recipe!.version,lines,reason);
      await onCommand(createCommand(`/recipes/${encodeURIComponent(productId)}`,body,'PUT'));
    } catch(err) {setError(err instanceof Error?err.message:'Reçete doğrulanamadı.');}
  }}>
    <div className="inventory-card-heading"><div><h2>Bir ürünün reçetesi</h2><p>{loading?'Yükleniyor…':recipe?.version?`Sürüm ${recipe.version}`:'Henüz reçete tanımlanmamış'}</p></div>
      <Button type="button" variant="outline" disabled={locked||loading} onClick={()=>setReload(value=>value+1)}>Güncel reçeteyi yükle</Button></div>
    <p className="inventory-help">Miktarlar bir adet ürün içindir. Güncel reçeteyi yüklemek formdaki düzenlemeleri yeniler; kaydedilen yeni sürüm sonraki hazırlıklarda kullanılır.</p>
    {(error||commandError) && <div className="alert error" role="alert">{error||commandError}</div>}
    <fieldset disabled={disabled}>
      <div className="recipe-lines">{lines.map((line,index)=>{
        const material=materials.find(item=>item.id===line.material_id);
        return <div className="recipe-line" key={index}>
          <label>Hammadde<select aria-label={`Hammadde ${index+1}`} value={line.material_id} required onChange={e=>setLines(previous=>previous.map((item,i)=>i===index?{...item,material_id:e.target.value}:item))}>
            <option value="">Hammadde seçin</option>{materials.map(item=><option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
          <label>Miktar ({material?.unit||'birim'})<input aria-label={`Miktar ${index+1}`} inputMode="decimal" required maxLength={40} value={line.quantity} onChange={e=>setLines(previous=>previous.map((item,i)=>i===index?{...item,quantity:e.target.value}:item))}/></label>
          <Button type="button" variant="outline" aria-label={`Reçete satırı ${index+1} kaldır`} onClick={()=>setLines(previous=>previous.filter((_,i)=>i!==index))}><Trash2 size={16}/></Button>
        </div>;
      })}</div>
      <Button type="button" variant="outline" disabled={lines.length>=100||!materials.length} onClick={()=>setLines(previous=>[...previous,{material_id:'',quantity:''}])}><Plus size={16}/>Hammadde ekle</Button>
      <label className="inventory-label">Değişiklik gerekçesi<textarea maxLength={500} required value={reason} onChange={e=>setReason(e.target.value)} placeholder="Örneğin: Yeni ürün reçetesi veya gramaj güncellemesi"/></label>
      <p className="inventory-help">Ondalık ayırıcı olarak virgül veya nokta kullanabilirsiniz; en fazla 6 ondalık basamak.</p>
      <Button disabled={!lines.length||!reason.trim()}>Reçeteyi kaydet</Button>
    </fieldset>
  </form>;
}
