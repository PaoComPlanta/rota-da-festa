import type { Metadata, Viewport } from "next";
import { Analytics } from "@vercel/analytics/next";
import { ThemeProvider } from "@/components/ThemeProvider";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://rotadafesta.vercel.app"),
  title: "Rota da Festa 🇵🇹",
  description: "Descobre jogos de futebol e festas populares perto de ti. No mapa. Grátis.",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "Rota da Festa",
  },
  openGraph: {
    title: "Rota da Festa — Jogos e Festas de Portugal",
    description: "Todos os jogos de futebol (profissional até distrital) e festas populares num mapa interativo. Grátis.",
    url: "https://rotadafesta.vercel.app",
    siteName: "Rota da Festa",
    images: [{ url: "/og-image.png", width: 1200, height: 630, alt: "Rota da Festa — Futebol, Festas, Cultura Local" }],
    locale: "pt_PT",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Rota da Festa 🇵🇹",
    description: "Todos os jogos e festas de Portugal. No mapa. Grátis.",
    images: ["/og-image.png"],
  },
  keywords: ["futebol", "portugal", "jogos", "festas populares", "romarias", "mapa", "distrital", "formação"],
};

export const viewport: Viewport = {
  themeColor: "#16a34a",
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt" suppressHydrationWarning>
      <head>
        <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
        <link rel="apple-touch-icon" href="/icons/icon-192.png" />
      </head>
      <body className="antialiased bg-gray-50 text-gray-900 dark:bg-gray-950 dark:text-gray-100 transition-colors duration-300">
        <ThemeProvider>{children}</ThemeProvider>
        <Analytics />
        <script
          dangerouslySetInnerHTML={{
            __html: `
              if ('serviceWorker' in navigator) {
                window.addEventListener('load', () => {
                  navigator.serviceWorker.register('/sw.js');
                });
              }
            `,
          }}
        />
      </body>
    </html>
  );
}
