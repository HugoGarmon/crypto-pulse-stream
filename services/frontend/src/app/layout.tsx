import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CryptoPulse Stream | Real-Time Market Intelligence",
  description: "High-throughput financial analytics engine powered by Redpanda, ClickHouse, and FastAPI",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es" className="dark">
      <body className="min-h-screen bg-[#090d16] text-slate-100 antialiased selection:bg-blue-600 selection:text-white">
        {children}
      </body>
    </html>
  );
}
