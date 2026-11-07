"use client";

import { Moon, Sun } from "lucide-react";

const buttonClass =
  "grid h-10 w-10 place-items-center rounded-full border border-mbiu-ink/10 bg-white/70 text-mbiu-ink transition hover:bg-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-mbiu-indigo dark:border-white/10 dark:bg-white/5 dark:text-[#F4EFE6] dark:hover:bg-white/10 dark:focus-visible:outline-mbiu-indigo-dark";

export function ThemeToggle() {
  const toggleTheme = () => {
    const root = document.documentElement;
    const isDark = root.classList.toggle("dark");
    root.style.colorScheme = isDark ? "dark" : "light";

    try {
      localStorage.setItem("mbiu-theme", isDark ? "dark" : "light");
    } catch {
      // Storage can be unavailable in private contexts; the toggle still works for the session.
    }
  };

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label="Switch between light and dark mode"
      title="Switch between light and dark mode"
      className={buttonClass}
    >
      <Moon className="h-[18px] w-[18px] dark:hidden" strokeWidth={1.8} />
      <Sun className="hidden h-[18px] w-[18px] dark:block" strokeWidth={1.8} />
    </button>
  );
}
