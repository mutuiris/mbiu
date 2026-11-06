import type { Metadata } from "next";
import type { ReactNode } from "react";

// Fonts ship with the app, so builds never fetch from Google and visitors never contact it
import "@fontsource-variable/fraunces/wght.css";
import "@fontsource-variable/fraunces/wght-italic.css";
import "@fontsource-variable/manrope/wght.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "Mbiu - Understand your contract before you sign it",
  description:
    "Upload your music contract and understand what you're agreeing to, what could affect you, and what questions to ask before signing.",
};

// Applies the saved theme before first paint so dark mode never flashes.
const themeScript = `(function(){try{var s=localStorage.getItem("mbiu-theme");var d=s?s==="dark":window.matchMedia("(prefers-color-scheme: dark)").matches;var r=document.documentElement;r.classList.toggle("dark",d);r.style.colorScheme=d?"dark":"light";}catch(e){}})();`;

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="antialiased">
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
        {children}
      </body>
    </html>
  );
}
