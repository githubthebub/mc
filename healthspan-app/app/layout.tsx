import type { Metadata } from "next";
import { Geist } from "next/font/google";
import "./globals.css";
import Navigation from "@/components/Navigation";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "HealthSpan — Personalized Health Tracking",
  description: "Track your healthspan with AI-powered personalized feedback that evolves with you.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${geistSans.variable} h-full antialiased`}>
      <body className="min-h-full bg-slate-950 text-slate-100 flex flex-col">
        <Navigation />
        <main className="flex-1 mx-auto w-full max-w-2xl px-4 py-6 pb-24 md:pb-6">
          {children}
        </main>
      </body>
    </html>
  );
}
