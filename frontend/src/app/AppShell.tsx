import type { ReactNode } from 'react';
import { useEffect, useRef } from 'react';
import { NavLink } from 'react-router-dom';
import { useAccounts } from '../api/account';
import { useSettings } from '../api/settings';
import { useTriggerSync } from '../api/sync';
import { SyncBar } from '../components/SyncBar';

interface NavItem {
  to: string;
  label: string;
  icon: string;
}

const NAV: NavItem[] = [
  { to: '/', label: '求职看板', icon: '📋' },
  { to: '/inbox', label: '收件箱', icon: '📬' },
  { to: '/settings', label: '设置', icon: '⚙️' },
];

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
  useAutoSyncOnMount();
  useAutoRefreshInterval();

  return (
    <div className="flex h-full">
      <aside className="flex w-56 shrink-0 flex-col border-r border-slate-200 bg-white">
        <div className="px-5 py-6">
          <div className="text-lg font-semibold tracking-tight text-slate-900">Mail Agent</div>
          <div className="mt-0.5 text-xs text-slate-400">求职邮件助手</div>
        </div>
        <nav className="flex flex-1 flex-col gap-1 px-3">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                [
                  'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-slate-900 text-white'
                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900',
                ].join(' ')
              }
            >
              <span aria-hidden>{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="px-5 py-4 text-[11px] text-slate-400">v0.1.0 · 本地运行</div>
      </aside>
      <main className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <SyncBar />
        <div className="min-h-0 flex-1 overflow-hidden">{children}</div>
      </main>
    </div>
  );
}
