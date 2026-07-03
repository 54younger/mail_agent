// Job-application status metadata. Tailwind class names are written as full
// literals so the purge step keeps them (no dynamic `bg-status-${x}`).

export interface StatusMeta {
  code: number;
  key: string;
  label: string;
  dot: string; // background dot color
  accent: string; // top accent bar for the column
  chip: string; // small badge on the card
}

export const JOB_STATUSES: StatusMeta[] = [
  { code: 0, key: 'applied', label: '已投递', dot: 'bg-status-applied', accent: 'bg-status-applied', chip: 'bg-indigo-50 text-indigo-700' },
  { code: 1, key: 'test', label: '笔试 / 测评', dot: 'bg-status-test', accent: 'bg-status-test', chip: 'bg-sky-50 text-sky-700' },
  { code: 2, key: 'interview', label: '面试', dot: 'bg-status-interview', accent: 'bg-status-interview', chip: 'bg-amber-50 text-amber-700' },
  { code: 3, key: 'offer', label: 'Offer', dot: 'bg-status-offer', accent: 'bg-status-offer', chip: 'bg-emerald-50 text-emerald-700' },
  { code: 4, key: 'rejected', label: '已拒', dot: 'bg-status-rejected', accent: 'bg-status-rejected', chip: 'bg-red-50 text-red-700' },
  { code: 99, key: 'unknown', label: '未分类', dot: 'bg-status-unknown', accent: 'bg-status-unknown', chip: 'bg-slate-100 text-slate-600' },
];

export function statusMeta(code: number): StatusMeta {
  return JOB_STATUSES.find((s) => s.code === code) ?? JOB_STATUSES[JOB_STATUSES.length - 1];
}
