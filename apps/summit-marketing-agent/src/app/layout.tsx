import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Summit Marketing Agent",
  description: "Semi-autonomous marketing agent for prospecting, scoring, and outreach.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
