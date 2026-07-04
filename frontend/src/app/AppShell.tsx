import type { ReactNode } from 'react';
import { useEffect, useRef } from 'react';
import { NavLink } from 'react-router-dom';
import { useAccounts } from '../api/account';
import { useSettings } from '../api/settings';
import { useTriggerSync } from '../api/sync';
import { SyncBar } from '../components/SyncBar';
import { LanguageSwitcher } from '../components/LanguageSwitcher';
import { useI18n } from '../i18n/useI18n';
import { APP_VERSION } from '../i18n/messages';

type IconName = 'board' | 'inbox' | 'settings';

interface NavItem {
  to: string;
  labelKey: string;
  icon: IconName;
}

const NAV: NavItem[] = [
  { to: '/', labelKey: 'nav.board', icon: 'board' },
  { to: '/inbox', labelKey: 'nav.inbox', icon: 'inbox' },
  { to: '/settings', labelKey: 'nav.settings', icon: 'settings' },
];

function NavIcon({ name }: { name: IconName }) {
  const common = {
    width: 18,
    height: 18,
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 1.8,
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const,
    'aria-hidden': true,
  };
  if (name === 'board')
    return (
      <svg {...common}>
        <rect x="3" y="3" width="7" height="9" rx="1.5" />
        <rect x="14" y="3" width="7" height="5" rx="1.5" />
        <rect x="14" y="12" width="7" height="9" rx="1.5" />
        <rect x="3" y="16" width="7" height="5" rx="1.5" />
      </svg>
    );
  if (name === 'inbox')
    return (
      <svg {...common}>
        <path d="M4 13h4l1.5 3h5L20 13h0" />
        <path d="M4 13 6 5h12l2 8v5a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 4 18Z" />
      </svg>
    );
  return (
    <svg {...common}>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-2.7 1.1V21a2 2 0 1 1-4 0v-.1a1.6 1.6 0 0 0-2.7-1.1l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.6 1.6 0 0 0-1.1-2.7H3a2 2 0 1 1 0-4h.1a1.6 1.6 0 0 0 1.1-2.7l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.6 1.6 0 0 0 2.7-1.1V3a2 2 0 1 1 4 0v.1a1.6 1.6 0 0 0 2.7 1.1l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.6 1.6 0 0 0 1.1 2.7H21a2 2 0 1 1 0 4h-.1a1.6 1.6 0 0 0-1.5 1.1Z" />
    </svg>
  );
}

// Trigger one incremental sync per app load once an account exists, so reopening
// the app refreshes the newest mail (with the top progress bar).
function useAutoSyncOnMount() {
  const accounts = useAccounts();
  const trigger = useTriggerSync();
  const started = useRef(false);
  useEffect(() => {
    if (!started.current && accounts.data && accounts.data.length > 0) {
      started.current = true;
      trigger.mutate(false);
    }
  }, [accounts.data, trigger]);
}

// While the app stays open, incrementally refresh mail on the user's configured
// interval. The backend no-ops a trigger when a sync is already running, so this
// can't stack. Disabled when there are no accounts or the setting is off.
function useAutoRefreshInterval() {
  const accounts = useAccounts();
  const settings = useSettings();
  const trigger = useTriggerSync();

  const enabled = settings.data?.auto_refresh_enabled ?? false;
  const minutes = settings.data?.auto_refresh_minutes ?? 15;
  const hasAccounts = (accounts.data?.length ?? 0) > 0;

  useEffect(() => {
    if (!enabled || !hasAccounts) return;
    const ms = Math.max(1, minutes) * 60_000;
    const id = window.setInterval(() => trigger.mutate(false), ms);
    return () => window.clearInterval(id);
  }, [enabled, minutes, hasAccounts, trigger]);
}

// Left-rail shell. Board is the primary destination; inbox + settings support it.
export function AppShell({ children }: { children: ReactNode }) {
  const { t } = useI18n();
  useAutoSyncOnMount();
  useAutoRefreshInterval();

  return (
    <div className="flex h-full">
      <aside className="flex w-60 shrink-0 flex-col border-r border-hairline bg-surface/80 backdrop-blur-sm">
        <div className="flex items-center gap-3 px-5 pb-5 pt-6">
          <div className="grid h-9 w-9 place-items-center rounded-2xl bg-gradient-to-br from-primary to-primary-strong text-base font-bold text-white shadow-lift">
            M
          </div>
          <div className="min-w-0">
            <div className="font-display text-[15px] font-semibold leading-tight tracking-tight text-ink">
              Mail Agent
            </div>
            <div className="truncate text-[11px] text-ink-mute">{t('nav.brandSubtitle')}</div>
          </div>
        </div>

        <nav className="flex flex-1 flex-col gap-1 px-3">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                [
                  'group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all',
                  isActive
                    ? 'bg-primary-tint text-primary-strong shadow-soft'
                    : 'text-ink-soft hover:bg-canvas-tint hover:text-ink',
                ].join(' ')
              }
            >
              {({ isActive }) => (
                <>
                  <span
                    aria-hidden
                    className={[
                      'absolute left-0 top-1/2 h-5 w-1 -translate-y-1/2 rounded-r-full bg-primary transition-opacity',
                      isActive ? 'opacity-100' : 'opacity-0',
                    ].join(' ')}
                  />
                  <NavIcon name={item.icon} />
                  {t(item.labelKey)}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="flex flex-col gap-3 px-4 py-4">
          <LanguageSwitcher />
          <div className="text-[11px] text-ink-mute">
            v{APP_VERSION} · {t('nav.local')}
          </div>
        </div>
      </aside>
      <main className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <SyncBar />
        <div className="min-h-0 flex-1 overflow-hidden">{children}</div>
      </main>
    </div>
  );
}
