"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { cn } from "@/lib/utils";

const LINKS = [
  { href: "/feed", label: "Feed" },
  { href: "/insights", label: "Insights" },
  { href: "/trends", label: "Trends" },
  { href: "/polls", label: "Polls" },
  { href: "/search", label: "Search" },
  { href: "/saved", label: "Saved" },
];

/** Brutalist top bar: sticker logo, mono links, a button that jumps. */
export function Nav() {
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);

  useEffect(() => {
    function openChat(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        router.push("/chat");
      }
    }
    window.addEventListener("keydown", openChat);
    return () => window.removeEventListener("keydown", openChat);
  }, [router]);

  return (
    <header className="sticky top-0 z-50 border-b-4 border-fg bg-ink">
      <div className="mx-auto flex h-[68px] max-w-[1400px] items-center justify-between px-4 sm:px-6">
        <Link className="group flex items-center gap-3" href="/" onClick={() => setOpen(false)}>
          <span className="shadow-hard-sm grid h-10 w-10 -rotate-6 place-items-center border-2 border-fg bg-yolk font-display text-xl transition-transform group-hover:rotate-6">
            K
          </span>
          <span className="font-display text-2xl uppercase tracking-wide">
            Kampher<span className="text-ember">!</span>
          </span>
        </Link>

        <nav aria-label="Primary" className="hidden items-center gap-4 md:flex">
          {LINKS.map((link) => {
            const active = pathname === link.href || pathname.startsWith(`${link.href}/`);
            return (
              <Link
                className={cn(
                  "font-mono text-[12px] font-bold uppercase tracking-[0.1em] transition-colors",
                  active
                    ? "bg-fg px-2.5 py-1.5 text-yolk"
                    : "text-fg hover:bg-panel hover:px-2.5 hover:py-1.5",
                )}
                href={link.href}
                key={link.href}
              >
                {link.label}
              </Link>
            );
          })}
          <Link className="editorial-button" href="/chat">
            Ask <span className="ml-2 font-mono text-[10px]">⌘K</span>
          </Link>
        </nav>

        <button
          aria-expanded={open}
          aria-label="Toggle navigation"
          className="shadow-hard-sm grid h-11 w-11 place-items-center border-2 border-fg bg-surface md:hidden"
          onClick={() => setOpen((value) => !value)}
          type="button"
        >
          <span aria-hidden="true" className="relative block h-4 w-6">
            <span className={cn("absolute left-0 top-0.5 h-[3px] w-6 bg-fg transition-transform", open && "translate-y-[5px] rotate-45")} />
            <span className={cn("absolute bottom-0.5 left-0 h-[3px] w-6 bg-fg transition-transform", open && "-translate-y-[6px] -rotate-45")} />
          </span>
        </button>
      </div>

      {open ? (
        <nav aria-label="Mobile" className="border-t-4 border-fg bg-ink md:hidden">
          {[...LINKS, { href: "/chat", label: "Ask Kampher" }].map((link) => (
            <Link
              className={cn(
                "block border-b-2 border-fg px-5 py-4 font-mono text-sm font-bold uppercase tracking-[0.1em]",
                pathname === link.href ? "bg-yolk" : "bg-ink hover:bg-panel",
              )}
              href={link.href}
              key={link.href}
              onClick={() => setOpen(false)}
            >
              {link.label}
            </Link>
          ))}
        </nav>
      ) : null}
    </header>
  );
}
