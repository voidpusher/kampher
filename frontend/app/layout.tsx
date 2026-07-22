import type { Metadata } from "next";
import { Anton, IBM_Plex_Mono, Inter } from "next/font/google";
import { Nav } from "@/components/nav";
import { Footer } from "@/components/footer";
import "./globals.css";

// Condensed impact face — the loud voice of the design.
const display = Anton({
  subsets: ["latin"],
  weight: "400",
  variable: "--font-display",
});

const sans = Inter({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-sans",
});

const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  metadataBase: new URL("https://kampher.vercel.app"),
  title: {
    default: "Kampher — opportunity intelligence",
    template: "%s | Kampher",
  },
  description:
    "Discover what people need before they search for a solution. Ranked, explained startup opportunities mined from public internet conversations.",
  applicationName: "Kampher",
  openGraph: {
    title: "Kampher — opportunity intelligence",
    description: "Find evidence-backed problems worth solving in public technical conversations.",
    type: "website",
    siteName: "Kampher",
    url: "/",
  },
  twitter: {
    card: "summary",
    title: "Kampher — opportunity intelligence",
    description: "Find evidence-backed problems worth solving.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${display.variable} ${sans.variable} ${mono.variable}`}>
      <body className="font-sans min-h-screen">
        <Nav />
        <main>{children}</main>
        <Footer />
      </body>
    </html>
  );
}
