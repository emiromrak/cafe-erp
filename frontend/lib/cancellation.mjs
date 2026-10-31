export function canCancelItem(role,status) {
  if (!['admin','cashier','waiter','kitchen'].includes(role)) return false;
  return status === 'sent' || (['preparing','ready'].includes(status) && ['admin','kitchen'].includes(role));
}

export function canCancelTab(role,items) {
  if (!['admin','cashier','waiter'].includes(role)) return false;
  return role === 'admin' || !items.some(item=>['preparing','ready'].includes(item.status));
}
