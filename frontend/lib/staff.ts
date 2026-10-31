export type Staff = {id:number; username:string; name:string; role:'admin'|'cashier'|'waiter'|'kitchen'; is_active:boolean; version:number};
export const roleNames = {admin:'Yönetici', cashier:'Kasiyer', waiter:'Garson', kitchen:'Mutfak'};
