import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = { title: "Mulec — From recording to rehearsal", description: "A local workspace for editable music charts." };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
