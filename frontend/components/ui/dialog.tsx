'use client';
import * as Dialog from '@radix-ui/react-dialog';
import { X } from 'lucide-react';
export function Modal({ open, onOpenChange, title, description, children }: {open:boolean; onOpenChange:(open:boolean)=>void; title:string; description:string; children:React.ReactNode}) {
  return <Dialog.Root open={open} onOpenChange={onOpenChange}><Dialog.Portal><Dialog.Overlay className="modal-overlay"/><Dialog.Content className="modal-content"><Dialog.Title className="text-2xl font-semibold tracking-tight">{title}</Dialog.Title><Dialog.Description className="mt-2 mb-6 text-sm text-stone-500">{description}</Dialog.Description>{children}<Dialog.Close className="absolute right-4 top-4 rounded-lg p-2 hover:bg-stone-100" aria-label="Kapat"><X size={18}/></Dialog.Close></Dialog.Content></Dialog.Portal></Dialog.Root>;
}
