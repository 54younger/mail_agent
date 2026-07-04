import type { ExtractStatus } from '../../api/jobs';
import { useI18n } from '../../i18n/useI18n';

// Three pipeline stages, shown as a stepper so the user sees which step is live.
const STAGES = [
  { key: 'keyword', labelKey: 'extract.stageKeyword' },
  { key: 'classify', labelKey: 'extract.stageClassify' },
  { key: 'extract', labelKey: 'extract.stageExtract' },
] as const;

export function ExtractProgress({ status }: { status: ExtractStatus }) {
  const { t } = useI18n();
  const caching = status.phase === 'cache';
  const activeIndex = STAGES.findIndex((s) => s.key === status.stage);
  const indeterminate = status.total === 0;
  const pct = indeterminate ? 0 : Math.round((status.current / status.total) * 100);

  const title = caching ? t('extract.caching') : t('extract.extractingTitle');
  const tail = caching ? (
    <>{indeterminate ? t('extract.preparing') : `${status.current}/${status.total}`}</>
  ) : (
    <>
      {indeterminate ? t('extract.scanning') : `${status.current}/${status.total}`} ·{' '}
      {t('extract.added')} <span className="font-semibold text-primary-strong">{status.created}</span>
    </>
  );

  return (
    <div className="border-b border-primary/15 bg-gradient-to-r from-primary-tint to-surface px-6 py-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium text-ink-soft">
          <span className="relative flex h-2.5 w-2.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary/50 opacity-75" />
            <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-primary" />
          </span>
          {title}
        </div>
        <div className="text-xs tabular-nums text-ink-mute">{tail}</div>
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
                    state === 'done' && 'bg-primary-tint text-primary-strong',
                    state === 'active' && 'bg-primary text-white shadow-soft',
                    state === 'todo' && 'bg-canvas-tint text-ink-mute',
                  ]
                    .filter(Boolean)
                    .join(' ')}
                >
                  <span aria-hidden>{state === 'done' ? '✓' : i + 1}</span>
                  {t(s.labelKey)}
                </span>
                {i < STAGES.length - 1 && (
                  <span
                    className={`mx-1.5 h-px w-5 transition-colors duration-300 ${
                      i < activeIndex ? 'bg-primary/40' : 'bg-hairline'
                    }`}
                  />
                )}
              </div>
            );
          })}
        </div>
      )}

      <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-canvas-tint">
        <div
          className={[
            'h-full rounded-full bg-gradient-to-r from-primary to-primary-strong',
            indeterminate ? 'w-1/3 animate-pulse' : 'transition-[width] duration-500 ease-out',
          ].join(' ')}
          style={indeterminate ? undefined : { width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
