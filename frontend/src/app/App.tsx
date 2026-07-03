import type { ReactNode } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { useHealth } from '../api/health';
import { AppShell } from './AppShell';
import { SetupGate } from '../features/setup/SetupGate';
import { BoardPage } from '../features/board/BoardPage';
import { InboxPage } from '../features/inbox/InboxPage';
import { SettingsPage } from '../features/settings/SettingsPage';

export function App() {
  const health = useHealth();

  if (health.isLoading) {
    return <FullScreenMessage>正在连接本地服务…</FullScreenMessage>;
  }
  if (health.isError) {
    return (
      <FullScreenMessage>
        无法连接本地后端服务。请确认后端已启动（<code>python run.py</code>）。
      </FullScreenMessage>
    );
  }

  // First run: user hasn't picked a data folder yet.
  if (!health.data?.configured) {
    return <SetupGate />;
  }

  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<BoardPage />} />
        <Route path="/inbox" element={<InboxPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  );
}

function FullScreenMessage({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-full items-center justify-center p-8 text-center text-slate-600">
      <p className="max-w-md text-sm leading-relaxed">{children}</p>
    </div>
  );
}
