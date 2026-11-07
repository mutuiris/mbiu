import { Music, Music2, Sparkles } from "lucide-react";
import Image from "next/image";

export function SunburstRays({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 70 80" fill="currentColor" aria-hidden="true" className={className}>
      <polygon points="44,5 58,7 63,41" />
      <polygon points="10,32 20,23 46,51" />
      <polygon points="6,64 6,73 38,67" />
    </svg>
  );
}

function TribalPattern({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 220 260" fill="none" className={className}>
      <path d="M-36 252 54 132l94 120" stroke="currentColor" strokeWidth="5" strokeLinejoin="round" />
      <path d="M-62 240 54 96l120 144" stroke="currentColor" strokeWidth="5" strokeLinejoin="round" />
      <path d="M-40 216 54 60l104 156" stroke="currentColor" strokeWidth="5" strokeLinejoin="round" />
      <path d="M-14 224 54 148l70 76" stroke="currentColor" strokeWidth="5" strokeLinejoin="round" />
      <circle cx="54" cy="132" r="3.5" fill="currentColor" />
      <circle cx="54" cy="96" r="3.5" fill="currentColor" />
      <circle cx="54" cy="60" r="3.5" fill="currentColor" />
      <circle cx="118" cy="118" r="3" fill="currentColor" />
      <circle cx="150" cy="168" r="3" fill="currentColor" />
    </svg>
  );
}

/**
 * The same margin doodles on every page: horn watermark, rays, tribal corner,
 * music notes and sparkles. The results variant is quieter so cards stay legible.
 */
export function SiteBackdrop({ variant = "landing" }: { variant?: "landing" | "results" }) {
  if (variant === "results") {
    return (
      <div aria-hidden className="pointer-events-none absolute inset-0 z-0 overflow-hidden">
        <Image
          src="/brand/mbiu-horn-watermark.png"
          alt=""
          width={972}
          height={590}
          priority
          className="absolute -right-20 top-[4%] w-[62%] max-w-[520px] opacity-[0.18] mix-blend-multiply dark:-right-10 dark:invert dark:opacity-[0.05] dark:mix-blend-screen sm:w-[46%]"
        />

        <SunburstRays className="absolute left-[3%] top-[2%] hidden h-12 w-11 text-mbiu-ink/80 sm:block dark:text-white/50" />
        <Music2 className="absolute right-[7%] top-[1%] h-7 w-7 rotate-[10deg] text-mbiu-ink/60 dark:text-white/40" />

        <Music2 className="absolute left-[4%] top-[46%] hidden h-8 w-8 -rotate-[12deg] text-mbiu-ink/45 sm:block dark:text-white/30" />
        <Sparkles className="absolute right-[4%] top-[38%] hidden h-5 w-5 text-mbiu-ink/45 sm:block dark:text-white/30" />

        <TribalPattern className="absolute -bottom-10 -left-10 h-[200px] w-[172px] text-mbiu-ink/75 dark:text-white/40" />
        <Music2 className="absolute bottom-8 right-[5%] h-9 w-9 rotate-[14deg] text-mbiu-ink/60 dark:text-white/40" />
        <Music className="absolute bottom-2 right-[2%] h-7 w-7 -rotate-[12deg] text-mbiu-ink/50 dark:text-white/30" />
        <Sparkles className="absolute bottom-24 right-[12%] h-5 w-5 text-mbiu-ink/45 dark:text-white/30" />
      </div>
    );
  }

  return (
    <div
      aria-hidden
      className="pointer-events-none absolute inset-x-0 top-0 h-[100svh] min-h-[620px] max-h-[880px] overflow-hidden"
    >
      <Image
        src="/brand/mbiu-horn-watermark.png"
        alt=""
        width={972}
        height={590}
        priority
        className="absolute left-1/2 top-[30%] w-[185%] max-w-none -translate-x-1/2 opacity-35 mix-blend-multiply sm:top-[12%] sm:w-[128%] xl:left-auto xl:right-[22%] xl:top-[8%] xl:w-[60%] xl:translate-x-0 xl:opacity-45 dark:opacity-[0.08] dark:invert dark:mix-blend-screen"
      />

      <TribalPattern className="absolute -bottom-10 -left-10 h-[200px] w-[170px] text-mbiu-ink/15 sm:h-[240px] sm:w-[205px] dark:text-white/20" />

      <Music2 className="absolute right-[6%] top-[10%] h-9 w-9 rotate-[10deg] text-mbiu-ink/90 dark:text-white/70 xl:right-[11%] xl:top-[20%]" />
      <Music2 className="absolute bottom-[7%] right-[7%] h-10 w-10 rotate-[14deg] text-mbiu-ink/90 dark:text-white/70" />
      <Music className="absolute bottom-[3%] right-[3%] h-7 w-7 -rotate-[12deg] text-mbiu-ink/80 dark:text-white/60" />
      <Sparkles className="absolute bottom-[11%] right-[2%] h-5 w-5 text-mbiu-ink/60 dark:text-white/50" />
    </div>
  );
}
