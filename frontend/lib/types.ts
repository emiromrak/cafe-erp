export type Table = { id: string; name: string; area: string; status: string };
export type Product = { id: string; name: string; category_id: string; price: number; type: string };
export type Category = { id: string; name: string };
export type Item = { id: number; tab_id: number; product_id: string; product_name: string; quantity: number; unit_price_cents: number; status: 'draft'|'sent'|'preparing'|'ready'|'cancelled'; created_at: string };
export type Tab = { id: number; table_id: string; version: number; status: string; opened_at: string; closed_at: string|null; total_cents: number; items: Item[]; payment: null|{method: string; amount_cents: number} };
export type OpenTab = Pick<Tab, 'id'|'table_id'|'version'|'opened_at'|'status'>;
export type KitchenItem = Item & { table_id: string; table_name: string; version: number };
