import { createContext, useContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { catalogs } from './catalogs';
import type { Locale } from './catalogs';
const Context = createContext({ locale: 'en-US' as Locale, timezone: 'UTC', setTimezone: (zone: string) => { void zone; }, setLocale: (locale: Locale) => { void locale; }, t: (key: string) => key });
export function I18nProvider({ children }: { children: ReactNode }) {
  const [timezone, setTimezone] = useState('UTC');
  const [locale, setLocale] = useState<Locale>('en-US');
  useEffect(() => { document.documentElement.lang = locale; }, [locale]);
  const t = (key: string) => catalogs[locale][key] ?? catalogs['en-US'][key] ?? key;
  return <Context.Provider value={{ locale, setLocale, timezone, setTimezone, t }}>{children}</Context.Provider>;
}
export const useI18n = () => useContext(Context);

export function formatTimestamp(value: unknown, locale: Locale, timezone: string): string {
  const date = new Date(String(value));
  if (!Number.isFinite(date.getTime())) return String(value);
  return new Intl.DateTimeFormat(locale, { dateStyle: 'medium', timeStyle: 'short', timeZone: timezone }).format(date);
}
