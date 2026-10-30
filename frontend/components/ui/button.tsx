import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
import * as React from 'react';
const buttonVariants = cva('inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xl text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 disabled:pointer-events-none disabled:opacity-40 min-h-11 px-4', { variants: { variant: { default: 'bg-emerald-800 text-white hover:bg-emerald-900', outline: 'border border-stone-200 bg-white hover:bg-stone-100 text-stone-700', ghost: 'hover:bg-stone-100 text-stone-600', destructive: 'bg-red-50 text-red-700 hover:bg-red-100' } }, defaultVariants: { variant: 'default' } });
export function Button({ className, variant, asChild = false, ...props }: React.ComponentProps<'button'> & VariantProps<typeof buttonVariants> & {asChild?: boolean}) {
  const Comp = asChild ? Slot : 'button';
  return <Comp className={twMerge(clsx(buttonVariants({ variant }), className))} {...props} />;
}
