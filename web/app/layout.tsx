import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Plant Atlas",
  description: "Questa macchina si può usare oggi? Ogni risposta viene da fatti che portano le parole della loro fonte.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="it">
      <body className="antialiased">{children}</body>
    </html>
  );
}
