import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";

import "./globals.css";

export const metadata: Metadata = {
  title: "Mbiu",
  description: "Understand a music contract before you sign it.",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
