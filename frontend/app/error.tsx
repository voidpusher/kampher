"use client";

export default function GlobalError({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="mx-auto flex min-h-[60vh] max-w-3xl flex-col items-start justify-center px-6 py-20">
      <p className="editorial-label">Connection interrupted</p>
      <h1 className="mt-4 font-display text-4xl font-semibold tracking-[-0.04em]">
        This signal could not be loaded.
      </h1>
      <p className="mt-4 max-w-lg text-sm leading-6 text-muted">
        Nothing was changed. Retry the request or return to search the indexed corpus.
      </p>
      <button className="editorial-button mt-8" onClick={reset} type="button">
        Try again
      </button>
    </div>
  );
}
