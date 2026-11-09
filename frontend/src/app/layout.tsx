import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import "./globals.css";

// Fonts ship with the app, so builds never fetch from Google and visitors never contact it
import "@fontsource-variable/fraunces/wght.css";
import "@fontsource-variable/fraunces/wght-italic.css";
import "@fontsource-variable/manrope/wght.css";
import { EvaluationFloatingBanner } from "@/components/EvaluationFloatingBanner";
import "./globals.css";

const title = "Mbiu - Understand your contract before you sign it";
const description =
  "Upload your music contract and understand what you're agreeing to, what could affect you, and what questions to ask before signing.";

// The share picture is app/opengraph-image.png: the header logo, unchanged, over the site's own words
export const metadata: Metadata = {
  metadataBase: new URL("https://mbiu-music.vercel.app"),
  title,
  description,
  openGraph: { type: "website", siteName: "Mbiu", title, description },
  twitter: { card: "summary_large_image", title, description },
};

export const viewport: Viewport = {
  themeColor: "#fcf4e5",
};

// Applies the saved theme before first paint so dark mode never flashes.
const themeScript = `(function(){try{var s=localStorage.getItem("mbiu-theme");var d=s?s==="dark":window.matchMedia("(prefers-color-scheme: dark)").matches;var r=document.documentElement;r.classList.toggle("dark",d);r.style.colorScheme=d?"dark":"light";}catch(e){}})();`;

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="antialiased">
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
        <EvaluationFloatingBanner />
        {children}
      </body>
    </html>
  );
}
