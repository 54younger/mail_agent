// Consistent page header used across the board / inbox / settings surfaces.
export function PageHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <header className="border-b border-slate-200 bg-white px-6 py-5">
      <h1 className="text-lg font-semibold tracking-tight text-slate-900">{title}</h1>
      {subtitle && <p className="mt-0.5 text-sm text-slate-400">{subtitle}</p>}
    </header>
  );
}
