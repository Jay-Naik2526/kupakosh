import type { Metadata } from "next";
import { IBM_Plex_Sans, IBM_Plex_Mono, IBM_Plex_Serif, Noto_Sans_Devanagari, Courier_Prime } from "next/font/google";
import "./globals.css";
import { AppState } from "@/lib/state";
import { AppShell } from "@/components/v2/AppShell";

const plex = IBM_Plex_Sans({ subsets: ["latin"], weight: ["400", "500", "600"], variable: "--font-plex" });
const serif = IBM_Plex_Serif({ subsets: ["latin"], weight: ["500", "600"], variable: "--font-serif" });
const mono = IBM_Plex_Mono({ subsets: ["latin"], weight: ["400", "500"], variable: "--font-plex-mono" });
const deva = Noto_Sans_Devanagari({ subsets: ["devanagari"], weight: ["400", "500"], variable: "--font-deva" });
const courier = Courier_Prime({ subsets: ["latin"], weight: ["400", "700"], variable: "--font-courier" });

export const metadata: Metadata = {
  title: "Kupakosh — well memory",
  description: "Prototype for Oil India Limited · SIH 2026. Decision support only — the engineer decides.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${plex.variable} ${serif.variable} ${mono.variable} ${deva.variable} ${courier.variable}`}>
      <body><AppState><AppShell>{children}</AppShell></AppState></body>
    </html>
  );
}
