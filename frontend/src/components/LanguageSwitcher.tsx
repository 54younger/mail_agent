import type { Lang } from '../i18n/messages';
import { useI18n } from '../i18n/useI18n';

// Compact segmented EN | 中文 control for the sidebar footer. Persists via
// useI18n().setLang. Default language is English.
const OPTIONS: { code: Lang; label: string }[] = [
  { code: 'en', label: 'EN' },
  { code: 'zh', label: '中文' },
];

export function LanguageSwitcher() {
  const { lang, setLang } = useI18n();

  return (
    <div
      role="group"
      aria-label="Language"
      className="inline-flex items-center rounded-full border border-hairline bg-surface-muted p-0.5 shadow-soft"
    >
      {OPTIONS.map((opt) => {
        const active = lang === opt.code;
        return (
          <button
            key={opt.code}
            type="button"
            onClick={() => setLang(opt.code)}
            aria-pressed={active}
            className={[
              'rounded-full px-2.5 py-1 text-xs font-medium transition-colors',
              active ? 'bg-primary text-white shadow-soft' : 'text-ink-mute hover:text-ink-soft',
            ].join(' ')}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
