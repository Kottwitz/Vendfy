import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Vendfy | Gestão comercial",
  description: "Clientes e orçamentos da sua empresa, em um só lugar.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="pt-BR">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
