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
    return <BackendDown />;
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

// The one-liner that starts each user's own local backend. Replace OWNER with
// your registry namespace once the image is published (see README).
const BACKEND_DOCKER_CMD =
  'docker run -d --name mailagent -p 127.0.0.1:8765:8765 -v mailagent-data:/data ghcr.io/OWNER/mail-agent:latest';

// Shown when the hosted frontend can't reach the user's local backend: guides
// them to start it with Docker. `useHealth` keeps polling, so once the backend
// is up the app advances on its own (see api/health.ts).
function BackendDown() {
  const { t } = useI18n();
  return (
    <div className="flex h-full items-center justify-center p-6">
      <div className="w-full max-w-lg rounded-3xl bg-surface p-8 shadow-lift ring-1 ring-hairline">
        <div className="mb-5 grid h-11 w-11 place-items-center rounded-2xl bg-gradient-to-br from-primary to-primary-strong text-lg font-bold text-white shadow-lift">
          M
        </div>
        <h1 className="font-display text-2xl font-semibold tracking-tight text-ink">
          {t('app.backendDownTitle')}
        </h1>
        <p className="mt-2 text-sm leading-relaxed text-ink-soft">{t('app.backendDownBody')}</p>
        <pre className="mt-4 overflow-x-auto rounded-xl bg-canvas-tint p-3 font-mono text-xs leading-relaxed text-ink-soft">
          {BACKEND_DOCKER_CMD}
        </pre>
        <p className="mt-3 text-xs text-ink-mute">{t('app.backendDownRetry')}</p>
      </div>
    </div>
  );
}
