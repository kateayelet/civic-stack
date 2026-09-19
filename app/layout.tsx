import type { Metadata } from "next";
import { Geist, Geist_Mono, Source_Serif_4 } from "next/font/google";
import { Suspense } from "react";
import { AppShell } from "@/components/app-shell";
import { LawProvider } from "@/components/law-provider";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const sourceSerif = Source_Serif_4({
  variable: "--font-source-serif",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "94920 Corpus — homeowner authority graph",
  description:
    "Every statute, ordinance, regulation, and founding instrument that binds a homeowner in ZIP 94920, walked back to the Declaration, with contradiction and taking flags.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} ${sourceSerif.variable} h-full antialiased`}
    >
      <body className="min-h-full">
        <LawProvider>
          <Suspense
            fallback={
              <div className="min-h-screen flex items-center justify-center text-[var(--muted)]">
                Loading…
              </div>
            }
          >
            <AppShell>{children}</AppShell>
          </Suspense>
        </LawProvider>
      </body>
    </html>
  );
}
