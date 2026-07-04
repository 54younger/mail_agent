import type { ReactNode } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { useHealth } from '../api/health';
import { AppShell } from './AppShell';
import { SetupGate } from '../features/setup/SetupGate';
import { BoardPage } from '../features/board/BoardPage';
import { InboxPage } from '../features/inbox/InboxPage';
import { SettingsPage } from '../features/settings/SettingsPage';
import { useI18n } from '../i18n/useI18n';

export function App() {
  const health = useHealth();
  const { t } = useI18n();

  if (health.isLoading) {
    return <FullScreenMessage>{t('app.connecting')}</FullScreenMessage>;
  }
  if (health.isError) {
    return (
      <FullScreenMessage>
        {t('app.connectErrorPre')}
        <code className="rounded bg-canvas-tint px-1.5 py-0.5 font-mono text-[0.85em] text-ink-soft">
          python run.py
        </code>
        {t('app.connectErrorPost')}
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
    <div className="flex h-full items-center justify-center p-8 text-center text-ink-soft">
      <p className="max-w-md text-sm leading-relaxed">{children}</p>
    </div>
  );
}
