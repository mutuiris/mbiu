import React from "react";
import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";
import { ArrowLeft, Users, Heart } from "lucide-react";

export const metadata: Metadata = {
  title: "Our Team — Mbiu",
  description:
    "The independent developers, researchers, and creators behind Mbiu, protecting independent Kenyan music artists.",
};

interface TeamMember {
  name: string;
  role: string;
  image: string;
  bio: string;
  email?: string;
  linkedin?: string;
}

const TEAM_MEMBERS: TeamMember[] = [
  {
    name: "Steve Wanangwe",
    role: "Backend developer",
    image: "/team/steve.png",
    bio: "Passionate about civic tech. Leads backend development and deployment, making sure our platform is reliable and scalable.",
    email: "stevewanash1@gmail.com",
    linkedin: "https://www.linkedin.com/in/steve-wanangwe/",
  },
  {
    name: "Bernadette Karanja",
    role: "Frontend developer & Research lead",
    image: "/team/bernadette.png",
    bio: "Passionate about human centered design. Leads user research, frontend development and documentation to ensure we're solving a real problem for real users.",
    email: "benadettekaranja@gmail.com",
    linkedin: "https://www.linkedin.com/in/bernadette-karanja/",
  },
  {
    name: "Addy Mutuiri",
    role: "Project lead & AI engineer",
    image: "/team/addy.png",
    bio: "Passionate about civic innovation and machine learning. Oversees project architecture, Gemini and retrieval pipeline orchestration, and technical strategy.",
    email: "muneneaddy@gmail.com",
    linkedin: "https://www.linkedin.com/in/addy-mutuiri/",
  },
  {
    name: "Mercyline Nyaboke",
    role: "Frontend & Accessibility developer",
    image: "/team/mercyline.png",
    bio: "Passionate about accessible user experiences and digital inclusion. Drives responsive mobile interfaces, accessible navigation, and community-driven design.",
    email: "mercylinenyaboke08@gmail.com",
    linkedin: "https://www.linkedin.com/in/mercyline-nyaboke/",
  },
];

function LinkedInIcon({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.75M6.46 10.9h2.79v8.37H6.46v-8.37M7.86 6.54a1.63 1.63 0 1 0 1.63 1.63 1.63 1.63 0 0 0-1.63-1.63Z" />
    </svg>
  );
}

function GmailIcon({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M20 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4-8 5-8-5V6l8 5 8-5v2z" />
    </svg>
  );
}

export default function TeamPage() {
  return (
    <div className="relative min-h-screen overflow-x-clip bg-mbiu-cream font-sans text-mbiu-ink transition-colors dark:bg-mbiu-bg-dark dark:text-[#F4EFE6]">
      <Navbar basePath="/" />

      <main className="mx-auto w-full max-w-[1280px] px-4 py-6 sm:px-8 sm:py-10">
        {/* Back Link */}
        <div className="mb-6">
          <Link
            href="/"
            className="group inline-flex items-center gap-2 text-[0.92rem] font-medium text-mbiu-ink/75 transition-colors hover:text-mbiu-indigo dark:text-[#B9C1C5] dark:hover:text-white"
            aria-label="Back to home"
          >
            <ArrowLeft className="h-4 w-4 transition-transform group-hover:-translate-x-1" />
            <span>Back to Home</span>
          </Link>
        </div>

        {/* Main Team Card */}
        <div className="w-full rounded-[28px] border border-white/70 bg-white/60 p-6 shadow-[0_30px_80px_-56px_rgba(22,26,38,0.6)] backdrop-blur-2xl dark:border-white/10 dark:bg-white/[0.06] sm:p-10 md:p-12">
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-mbiu-peach/50 px-3 py-1 text-[0.72rem] font-bold uppercase tracking-[0.16em] text-mbiu-warning-text dark:bg-mbiu-peach/15 dark:text-[#f3c9b8]">
              <Users className="h-3.5 w-3.5" />
              Contributors
            </span>
          </div>

          <h1 className="mt-3 font-serif text-[1.65rem] font-semibold tracking-[-0.025em] text-mbiu-ink dark:text-[#F6F2E9] sm:text-[2rem]">
            Our Team
          </h1>

          <p className="mt-2 text-[0.95rem] leading-relaxed text-[#6B7280] dark:text-[#9aa5aa]">
            The independent developers and civic researchers behind Mbiu.
          </p>

          {/* Members 2-Column Grid */}
          <div className="mt-10 grid grid-cols-1 gap-x-12 gap-y-12 md:grid-cols-2">
            {TEAM_MEMBERS.map((member) => (
              <div key={member.name} className="flex flex-col">
                <div className="flex items-center gap-4 sm:gap-5">
                  <div className="relative h-20 w-20 flex-shrink-0 overflow-hidden rounded-full border border-stone-200/90 shadow-sm dark:border-white/10 sm:h-24 sm:w-24">
                    <Image
                      src={member.image}
                      alt={member.name}
                      fill
                      sizes="(max-width: 640px) 80px, 96px"
                      className="object-cover"
                    />
                  </div>

                  <div className="min-w-0 flex-1">
                    <h2 className="font-sans text-[1.12rem] font-bold text-mbiu-ink dark:text-[#F6F2E9] sm:text-[1.2rem]">
                      {member.name}
                    </h2>
                    <p className="mt-0.5 text-[0.88rem] font-semibold text-[#155e42] dark:text-[#48bb78]">
                      {member.role}
                    </p>

                    <div className="mt-2.5 flex items-center gap-2">
                      {member.linkedin && (
                        <a
                          href={member.linkedin}
                          target="_blank"
                          rel="noopener noreferrer"
                          aria-label={`${member.name}'s LinkedIn profile`}
                          className="flex h-8 w-8 items-center justify-center rounded-[6px] border border-stone-200/90 bg-[#F4F3EF] text-[#0A66C2] transition hover:border-[#0A66C2]/40 hover:bg-white hover:shadow-sm dark:border-white/10 dark:bg-white/5 dark:text-[#70b5f9] dark:hover:bg-white/10"
                        >
                          <LinkedInIcon className="h-4 w-4" />
                        </a>
                      )}

                      {member.email && (
                        <a
                          href={`mailto:${member.email}`}
                          aria-label={`Email ${member.name}`}
                          className="flex h-8 w-8 items-center justify-center rounded-[6px] border border-stone-200/90 bg-[#F4F3EF] text-[#EA4335] transition hover:border-[#EA4335]/40 hover:bg-white hover:shadow-sm dark:border-white/10 dark:bg-white/5 dark:text-[#f87171] dark:hover:bg-white/10"
                        >
                          <GmailIcon className="h-4 w-4" />
                        </a>
                      )}
                    </div>
                  </div>
                </div>

                <p className="mt-4 text-[0.93rem] leading-relaxed text-mbiu-ink/80 dark:text-[#c2c9cd]">
                  {member.bio}
                </p>
              </div>
            ))}
          </div>

          {/* Mozilla x KamiLimu Section */}
          <div className="mt-12 rounded-2xl border border-mbiu-ink/10 bg-white/50 p-6 dark:border-white/10 dark:bg-white/[0.04]">
            <h2 className="font-serif text-[1.08rem] font-semibold text-mbiu-ink dark:text-[#F6F2E9] sm:text-[1.15rem]">
              Mozilla x KamiLimu Innovation
            </h2>
            <p className="mt-2 text-[0.92rem] leading-relaxed text-mbiu-ink/80 dark:text-[#B9C1C5]">
              Developed under the mentorship and sponsorship of{" "}
              <a
                href="https://www.kamilimu.org/"
                target="_blank"
                rel="noopener noreferrer"
                className="font-medium underline decoration-mbiu-ink/30 underline-offset-2 hover:text-mbiu-indigo dark:hover:text-white"
              >
                KamiLimu Limited
              </a>{" "}
              and the Mozilla Foundation. Built to advance creative rights and fair contract literacy
              across Kenya.
            </p>
          </div>

          <div className="mt-6 flex items-center gap-2 text-[0.9rem] font-medium text-mbiu-ink/70 dark:text-[#9aa5aa]">
            <Heart className="h-4 w-4 text-rose-500" />
            <span>Built for independent artists in Nairobi and across Africa.</span>
          </div>
        </div>
      </main>

      <Footer basePath="/" />
    </div>
  );
}
