import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api, ApiError } from '../../api/client';

interface SetupResponse {
  data_dir: string;
}

// First-run screen: the user names a local folder where their SQLite DB and
// settings live. Backend endpoint (POST /api/setup/data-folder) lands in Phase 1;
// on success we invalidate `health` so the app re-renders into the shell.
export function SetupGate() {
  const qc = useQueryClient();
  const [path, setPath] = useState('');

  const mutation = useMutation({
    mutationFn: (folder: string) =>
      api.post<SetupResponse>('/api/setup/data-folder', { path: folder }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['health'] }),
  });

  return (
    <div className="flex h-full items-center justify-center bg-slate-50 p-6">
      <div className="w-full max-w-lg rounded-2xl bg-white p-8 shadow-sm ring-1 ring-slate-100">
        <h1 className="text-xl font-semibold text-slate-900">欢迎使用 Mail Agent</h1>
        <p className="mt-2 text-sm leading-relaxed text-slate-500">
          请选择一个本地文件夹用于存放你的数据库与设置。你的邮件数据只保存在这台电脑上，
          账户密码与 API Key 存入系统安全存储（不会明文落盘）。
        </p>

        <form
          className="mt-6 space-y-3"
          onSubmit={(e) => {
            e.preventDefault();
            if (path.trim()) mutation.mutate(path.trim());
          }}
        >
          <label className="block text-sm font-medium text-slate-700" htmlFor="data-folder">
            数据文件夹路径
          </label>
          <input
            id="data-folder"
            value={path}
            onChange={(e) => setPath(e.target.value)}
            placeholder="/mnt/c/Users/You/MailData"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900 focus:ring-1 focus:ring-slate-900"
          />
          <p className="text-xs text-slate-400">
            请填写<strong>绝对路径</strong>（不要用相对路径，否则会落在程序目录内）。示例：
            <br />· macOS/Linux：<code>/home/you/mail-data</code> 或 <code>~/mail-data</code>
            <br />· Windows：<code>D:\MailData</code>
            <br />· 在 WSL 中指向 Windows 盘：<code>C:\Users\You\MailData</code> 或{' '}
            <code>/mnt/c/Users/You/MailData</code>
          </p>

          {mutation.isError && (
            <p className="text-sm text-red-600">{(mutation.error as ApiError).message}</p>
          )}

          <button
            type="submit"
            disabled={!path.trim() || mutation.isPending}
            className="w-full rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-slate-700 disabled:opacity-50"
          >
            {mutation.isPending ? '创建中…' : '开始使用'}
          </button>
        </form>
      </div>
    </div>
  );
}
