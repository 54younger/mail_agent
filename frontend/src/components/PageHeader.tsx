// Consistent page header used across the board / inbox / settings surfaces.
export function PageHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <header className="border-b border-hairline bg-surface px-6 py-5">
      <h1 className="font-display text-xl font-semibold tracking-tight text-ink">{title}</h1>
      {subtitle && <p className="mt-1 text-sm text-ink-mute">{subtitle}</p>}
    </header>
  );
}
