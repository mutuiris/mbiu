import React from "react";
import { HeroContent } from "@/components/landing/hero/HeroContent";
import { PreviewCard } from "@/components/landing/hero/PreviewCard";

export interface HeroProps {
  id?: string;
  className?: string;
}

export function Hero({ id = "about", className = "" }: HeroProps) {
  return (
    <section
      id={id}
      className={`mx-auto grid w-full max-w-[1280px] scroll-mt-20 items-center gap-8 px-4 pb-6 pt-4 sm:scroll-mt-24 sm:gap-10 sm:px-8 sm:pb-8 sm:pt-6 xl:grid-cols-[1.15fr_0.85fr] xl:gap-8 xl:pb-8 xl:pt-8 ${className}`}
    >
      <HeroContent />
      <div className="flex w-full min-w-0 justify-center xl:justify-end xl:pr-14">
        <PreviewCard />
      </div>
    </section>
  );
}
