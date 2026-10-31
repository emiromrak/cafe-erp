export type Material = {id:string;name:string;category:string;unit:string;current_stock:string;min_alert:string;is_critical:boolean};
export type Movement = {id:number;material_id:string;material_name:string;kind:string;quantity:string;balance_after:string;unit:string;reason:string;created_at:string;item_id:number|null;disposition:string|null};
export type Recipe = {product_id:string;version:number;updated_at:string|null;lines:{material_id:string;quantity:string;material_name:string;unit:string}[]};
export type RecipeDraft = {material_id:string;quantity:string};
export type InventoryCommand = {path:string;body:Record<string,unknown>;method:string;key:string;actorId?:number};
