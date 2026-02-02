import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Consensus",
  description: "Multi-source knowledge synthesis",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.className} min-h-screen flex flex-col`}>
        <main className="flex-1">{children}</main>
        <footer className="border-t border-gray-200 py-6 text-center text-sm text-gray-500">
          <p>
            <span className="font-medium text-gray-700">Consensus</span>
            {" "}&mdash; an{" "}
            <a
              href="https://energy2.co.uk"
              target="_blank"
              rel="noopener noreferrer"
              className="text-orange-600 hover:text-orange-700 hover:underline"
            >
              Energy2 Ltd
            </a>
            {" "}research project
          </p>
        </footer>
      </body>
    </html>
  );
}
