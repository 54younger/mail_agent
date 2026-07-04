import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api, ApiError } from '../../api/client';
import { useI18n } from '../../i18n/useI18n';

interface SetupResponse {
  data_dir: string;
}

// First-run screen: the user names a local folder where their SQLite DB and
// settings live. On success we invalidate `health` so the app re-renders into
// the shell.
export function SetupGate() {
  const qc = useQueryClient();
  const { t } = useI18n();
  const [path, setPath] = useState('');

  const mutation = useMutation({
    mutationFn: (folder: string) =>
      api.post<SetupResponse>('/api/setup/data-folder', { path: folder }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['health'] }),
  });

  return (
    <div className="relative flex h-full items-center justify-center overflow-hidden p-6">
      <div className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full bg-primary/15 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-24 -left-24 h-72 w-72 rounded-full bg-primary/10 blur-3xl" />
      <div className="relative w-full max-w-lg rounded-3xl bg-surface p-8 shadow-lift ring-1 ring-hairline">
        <div className="mb-5 grid h-11 w-11 place-items-center rounded-2xl bg-gradient-to-br from-primary to-primary-strong text-lg font-bold text-white shadow-lift">
          M
        </div>
        <h1 className="font-display text-2xl font-semibold tracking-tight text-ink">
          {t('setup.title')}
        </h1>
        <p className="mt-2 text-sm leading-relaxed text-ink-soft">{t('setup.intro')}</p>

        <form
          className="mt-6 space-y-3"
          onSubmit={(e) => {
            e.preventDefault();
            if (path.trim()) mutation.mutate(path.trim());
          }}
        >
          <label className="block text-sm font-medium text-ink-soft" htmlFor="data-folder">
            {t('setup.folderLabel')}
          </label>
          <input
            id="data-folder"
            value={path}
            onChange={(e) => setPath(e.target.value)}
            placeholder="/mnt/c/Users/You/MailData"
            className="w-full rounded-xl border border-hairline bg-surface-muted px-3 py-2.5 text-sm text-ink outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-primary/20"
          />
          <p className="text-xs leading-relaxed text-ink-mute">
            {t('setup.hintAbsolute')}
            <br />· {t('setup.hintMac')}
            <code>/home/you/mail-data</code> {t('setup.hintWslOr')} <code>~/mail-data</code>
            <br />· {t('setup.hintWin')}
            <code>D:\MailData</code>
            <br />· {t('setup.hintWsl')}
            <code>C:\Users\You\MailData</code>
            {t('setup.hintWslOr')}
            <code>/mnt/c/Users/You/MailData</code>
          </p>

          {mutation.isError && (
            <p className="text-sm text-red-600">{(mutation.error as ApiError).message}</p>
          )}

          <button
            type="submit"
            disabled={!path.trim() || mutation.isPending}
            className="w-full rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-white shadow-soft transition-all hover:bg-primary-strong hover:shadow-card disabled:opacity-50"
          >
            {mutation.isPending ? t('setup.creating') : t('setup.start')}
          </button>
        </form>
      </div>
    </div>
  );
}
