import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Navbar } from "@/components/layout/Navbar";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "PolyEdge - Your Edge in Prediction Markets",
  description: "Trade Polymarket with confidence. AI-powered signals with a transparent track record.",
  keywords: ["polymarket", "prediction markets", "trading signals", "crypto", "politics"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.variable} font-sans antialiased bg-zinc-950 text-zinc-100 min-h-screen`}>
        <Navbar />
        <main className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>
        <footer className="border-t border-zinc-800 mt-16">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">
            <div className="flex flex-col md:flex-row justify-between items-center gap-4">
              <div className="flex items-center gap-2">
                <div className="h-6 w-6 rounded bg-gradient-to-br from-emerald-500 to-emerald-600 flex items-center justify-center">
                  <span className="text-white font-bold text-xs">PE</span>
                </div>
                <span className="text-sm text-zinc-400">PolyEdge</span>
              </div>
              <p className="text-zinc-500 text-sm text-center">
                Not financial advice. Trade at your own risk. Past performance does not guarantee future results.
              </p>
              <div className="flex items-center gap-4 text-sm text-zinc-400">
                <a href="/track-record" className="hover:text-white transition-colors">Track Record</a>
                <span className="text-zinc-700">|</span>
                <a href="#alerts" className="hover:text-white transition-colors">Get Alerts</a>
              </div>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
