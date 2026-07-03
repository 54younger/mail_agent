import type { ExtractStatus } from '../../api/jobs';

// Three pipeline stages, shown as a stepper so the user sees which step is live.
const STAGES = [
  { key: 'keyword', label: '关键字预筛' },
  { key: 'classify', label: '分类判断' },
  { key: 'extract', label: '信息抽取' },
] as const;

export function ExtractProgress({ status }: { status: ExtractStatus }) {
  const caching = status.phase === 'cache';
  const activeIndex = STAGES.findIndex((s) => s.key === status.stage);
  const indeterminate = status.total === 0;
  const pct = indeterminate ? 0 : Math.round((status.current / status.total) * 100);

  const title = caching ? '正在缓存邮件正文' : '正在从邮件抽取投递记录';
  const tail = caching ? (
    <>{indeterminate ? '准备中…' : `${status.current}/${status.total}`}</>
  ) : (
    <>
      {indeterminate ? '扫描中…' : `${status.current}/${status.total}`} · 已新增{' '}
      <span className="font-medium text-violet-600">{status.created}</span>
    </>
  );

  return (
    <div className="border-b border-violet-100 bg-gradient-to-r from-violet-50 to-white px-6 py-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
          <span className="relative flex h-2.5 w-2.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-violet-400 opacity-75" />
            <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-violet-500" />
          </span>
          {title}
        </div>
        <div className="text-xs tabular-nums text-slate-500">{tail}</div>
      </div>

      {!caching && (
      <div className="mt-2.5 flex items-center">
        {STAGES.map((s, i) => {
          const state = i < activeIndex ? 'done' : i === activeIndex ? 'active' : 'todo';
          return (
            <div key={s.key} className="flex items-center">
              <span
                className={[
                  'flex h-6 items-center gap-1 rounded-full px-2.5 text-[11px] font-medium transition-colors duration-300',
                  state === 'done' && 'bg-violet-100 text-violet-600',
                  state === 'active' && 'bg-violet-600 text-white shadow-sm',
                  state === 'todo' && 'bg-slate-100 text-slate-400',
                ]
                  .filter(Boolean)
                  .join(' ')}
              >
                <span aria-hidden>{state === 'done' ? '✓' : i + 1}</span>
                {s.label}
              </span>
              {i < STAGES.length - 1 && (
                <span
                  className={`mx-1.5 h-px w-5 transition-colors duration-300 ${
                    i < activeIndex ? 'bg-violet-300' : 'bg-slate-200'
                  }`}
                />
              )}
            </div>
          );
        })}
      </div>
      )}

      <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
        <div
          className={[
            'h-full rounded-full bg-gradient-to-r from-violet-500 to-fuchsia-500',
            indeterminate ? 'w-1/3 animate-pulse' : 'transition-[width] duration-500 ease-out',
          ].join(' ')}
          style={indeterminate ? undefined : { width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
