import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const title = "MCPolska — federacyjny gateway MCP";
const description =
  "Wspólna warstwa integracyjna MCP: jeden punkt dostępu (konektor), przez który asystenci AI korzystają z wielu niezależnych aplikacji — z centralnymi uprawnieniami i audytem.";

export const metadata: Metadata = {
  metadataBase: new URL("https://oazai.pl"),
  title,
  description,
  openGraph: {
    title,
    description,
    url: "https://oazai.pl",
    siteName: "MCPolska",
    locale: "pl_PL",
    type: "website",
  },
  twitter: { card: "summary_large_image", title, description },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="pl"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
