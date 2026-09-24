import type { Metadata } from "next";
import { IBM_Plex_Sans, IBM_Plex_Mono, Noto_Sans_Devanagari, Courier_Prime } from "next/font/google";
import "./globals.css";
import { AppState } from "@/lib/state";
import { FileFrame } from "@/components/kk/FileFrame";

const plex = IBM_Plex_Sans({ subsets: ["latin"], weight: ["400", "500", "600"], variable: "--font-plex" });
const mono = IBM_Plex_Mono({ subsets: ["latin"], weight: ["400", "500"], variable: "--font-plex-mono" });
const deva = Noto_Sans_Devanagari({ subsets: ["devanagari"], weight: ["400", "500"], variable: "--font-deva" });
const courier = Courier_Prime({ subsets: ["latin"], weight: ["400", "700"], variable: "--font-courier" });

export const metadata: Metadata = {
  title: "Kupakosh — well memory",
  description: "Prototype for Oil India Limited · SIH 2026. Decision support only — the engineer decides.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${plex.variable} ${mono.variable} ${deva.variable} ${courier.variable}`}>
      <body><AppState><FileFrame>{children}</FileFrame></AppState></body>
    </html>
  );
}
