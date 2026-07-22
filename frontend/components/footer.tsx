import Link from "next/link";

/** Yellow slab, checkerboard strip, wordmark you can't miss. */
export function Footer() {
  return (
    <footer className="border-t-4 border-fg">
      {/* Checkerboard strip — built from solid cells, not a pattern fill. */}
      <div aria-hidden="true" className="flex h-5 overflow-hidden">
        {Array.from({ length: 64 }, (_, index) => (
          <span
            className={`h-5 w-5 shrink-0 ${index % 2 === 0 ? "bg-fg" : "bg-yolk"}`}
            key={index}
          />
        ))}
      </div>

      <div className="border-t-4 border-fg bg-yolk">
        <div className="mx-auto max-w-[1400px] px-4 py-12 sm:px-6">
          <div className="flex flex-wrap items-start justify-between gap-8">
            <p className="max-w-md text-sm font-medium leading-6">
              Build from evidence, not instinct. Kampher preserves public
              conversations and turns repeated pain into inspectable product
              signal.
            </p>
            <nav aria-label="Footer" className="flex flex-wrap gap-6">
              <Link className="font-mono text-[12px] font-bold uppercase tracking-[0.1em] underline decoration-2 underline-offset-4 hover:text-ember" href="/insights">
                Corpus status
              </Link>
              <Link className="font-mono text-[12px] font-bold uppercase tracking-[0.1em] underline decoration-2 underline-offset-4 hover:text-ember" href="/polls">
                Survey sources
              </Link>
              <a
                className="font-mono text-[12px] font-bold uppercase tracking-[0.1em] underline decoration-2 underline-offset-4 hover:text-ember"
                href="https://github.com/voidpusher/kampher"
                rel="noopener noreferrer"
                target="_blank"
              >
                Source code ↗
              </a>
            </nav>
          </div>
          <p className="outline-text mt-10 select-none font-display text-[clamp(4rem,13vw,13rem)] uppercase leading-[0.85]">
            Kampher!
          </p>
          <p className="mt-4 font-mono text-[10px] uppercase tracking-[0.14em]">
            © {new Date().getFullYear()} — signal from public conversations · no gradients were harmed
          </p>
        </div>
      </div>
    </footer>
  );
}
