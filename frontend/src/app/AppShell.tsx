import type { ReactNode } from 'react';
import { useEffect, useRef } from 'react';
import { NavLink } from 'react-router-dom';
import { useAccount } from '../api/account';
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
  const account = useAccount();
  const trigger = useTriggerSync();
  const started = useRef(false);
  useEffect(() => {
    if (!started.current && account.data) {
      started.current = true;
      trigger.mutate(false);
    }
  }, [account.data, trigger]);
}

// Left-rail shell. Board is the primary destination; inbox + settings support it.
export function AppShell({ children }: { children: ReactNode }) {
  useAutoSyncOnMount();

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
