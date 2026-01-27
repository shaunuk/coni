import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Consensus Engine",
  description: "Humanity's Knowledge, Verified",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
