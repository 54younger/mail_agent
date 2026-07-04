import { useContext } from 'react';
import { I18nContext, type I18nValue } from './I18nProvider';

// Access the active language + translator. Must be used inside <I18nProvider>.
export function useI18n(): I18nValue {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error('useI18n must be used within an I18nProvider');
  return ctx;
}
