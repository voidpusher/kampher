import Link from "next/link";

export default function NotFound() {
  return (
    <div className="mx-auto flex max-w-6xl flex-col items-start px-6 py-32">
      <p className="font-mono text-[11px] uppercase tracking-[0.25em] text-faint">
        404 — no signal
      </p>
      <h1 className="mt-4 font-display text-4xl">
        Nothing indexed at this address.
      </h1>
      <Link href="/feed" className="mt-8 text-sm text-muted hover:text-fg">
        Back to the feed →
      </Link>
    </div>
  );
}
