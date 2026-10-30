import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = { title: 'CafeERP · Servis', description: 'Masa servisi, adisyon ve mutfak yönetimi' };
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="tr"><body>{children}</body></html>;
}
