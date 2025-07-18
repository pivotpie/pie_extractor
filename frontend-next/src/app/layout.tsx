import type { Metadata, Viewport } from "next";
import { Poppins } from "next/font/google";
import { Providers } from "./providers";
import "./globals.css";

// Load Poppins from Google Fonts
const poppins = Poppins({
  weight: ['100', '200', '300', '400', '500', '600', '700', '800', '900'],
  style: ['normal', 'italic'],
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-poppins',
  preload: true,
});

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
  viewportFit: 'cover',
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#0f172a" },
  ],
};

export const metadata: Metadata = {
  title: "Pie Extractor | Document Management System",
  description: "A modern document management system with AI-powered search and organization",
  keywords: ["document management", "AI search", "file organization", "productivity"],
  authors: [{ name: "Pie Extractor Team" }],
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: 'https://pie-extractor.vercel.app',
    title: 'Pie Extractor | Document Management System',
    description: 'A modern document management system with AI-powered search and organization',
    siteName: 'Pie Extractor',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Pie Extractor | Document Management System',
    description: 'A modern document management system with AI-powered search and organization',
    creator: '@pieextractor',
  },
  icons: {
    icon: '/favicon.ico',
    shortcut: '/favicon-16x16.png',
    apple: '/apple-touch-icon.png',
  },
  manifest: '/site.webmanifest',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning className={`${poppins.variable}`}>
      <body className={`font-sans antialiased ${poppins.className} min-h-screen bg-background text-foreground`}>
        <Providers>
          <div className="relative flex min-h-screen flex-col">
            {children}
          </div>
        </Providers>
      </body>
    </html>
  );
}
