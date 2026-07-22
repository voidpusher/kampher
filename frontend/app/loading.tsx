export default function Loading() {
  return (
    <div aria-live="polite" className="mx-auto min-h-[60vh] max-w-6xl px-6 py-16">
      <div className="flex items-center gap-3">
        <span className="h-2 w-2 animate-pulse rounded-full bg-ember" />
        <p className="editorial-label">Loading indexed evidence</p>
      </div>
    </div>
  );
}
