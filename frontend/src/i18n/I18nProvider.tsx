import { createContext, useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { messages, type Lang } from './messages';

export type TParams = Record<string, string | number>;

export interface I18nValue {
  lang: Lang;
  setLang: (lang: Lang) => void;
  t: (key: string, params?: TParams) => string;
}

export const I18nContext = createContext<I18nValue | null>(null);

const STORAGE_KEY = 'mail-agent-lang';

// Default to English; persist the user's choice. Guarded so no-storage
// environments still resolve to a valid language.
function readInitialLang(): Lang {
  try {
    return localStorage.getItem(STORAGE_KEY) === 'zh' ? 'zh' : 'en';
  } catch {
    return 'en';
  }
}

// Traverse a nested dict by dot path (e.g. "settings.sectionAiModel").
function lookup(dict: unknown, key: string): unknown {
  return key.split('.').reduce<unknown>((node, part) => {
    if (node && typeof node === 'object') return (node as Record<string, unknown>)[part];
    return undefined;
  }, dict);
}

// Replace {name} tokens with provided params; unknown tokens are left intact
// (so literal placeholders like {sender} in prompt templates survive).
function interpolate(text: string, params?: TParams): string {
  if (!params) return text;
  return text.replace(/\{(\w+)\}/g, (match, name: string) =>
    name in params ? String(params[name]) : match,
  );
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(readInitialLang);

  useEffect(() => {
    document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en';
    document.title = lang === 'zh' ? 'Mail Agent · 求职看板' : 'Mail Agent · Job Board';
  }, [lang]);

  const setLang = useCallback((next: Lang) => {
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      /* storage unavailable — keep in-memory only */
    }
    setLangState(next);
  }, []);

  const t = useCallback(
    (key: string, params?: TParams): string => {
      const active = lookup(messages[lang], key);
      if (typeof active === 'string') return interpolate(active, params);
      // Fall back to English, then to the raw key.
      const fallback = lookup(messages.en, key);
      if (typeof fallback === 'string') return interpolate(fallback, params);
      return key;
    },
    [lang],
  );

  const value = useMemo<I18nValue>(() => ({ lang, setLang, t }), [lang, setLang, t]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}
