import { expect, test } from 'vitest';
import { catalogs, locales } from './catalogs';
import { formatTimestamp } from './i18n';
import { parseProfile } from './profileApi';

test('all catalogs preserve keys and interpolation placeholders', () => {
  const keys = Object.keys(catalogs['en-US']).sort();
  for (const locale of locales) {
    expect(Object.keys(catalogs[locale]).sort()).toEqual(keys);
    for (const key of keys) {
      expect(catalogs[locale][key].trim()).not.toBe('');
      expect(catalogs[locale][key].match(/\{\w+\}/g) ?? []).toEqual(catalogs['en-US'][key].match(/\{\w+\}/g) ?? []);
    }
  }
});

test('timezone changes presentation without modifying the UTC source', () => {
  const original = '2026-11-01T12:00:00Z';
  expect(formatTimestamp(original, 'en-US', 'UTC')).toContain('12:00');
  expect(formatTimestamp(original, 'pt-BR', 'America/Sao_Paulo')).toContain('09:00');
  expect(formatTimestamp(original, 'es-ES', 'UTC')).toContain('12:00');
  expect(original).toBe('2026-11-01T12:00:00Z');
});

test('invalid profile contracts cannot set frontend identity or locale', () => {
  const profile = {user_id: 'synthetic', email: 'user@example.test', role: 'user', display_name: 'User', timezone: 'UTC', locale: 'en-US', revision: 0};
  expect(parseProfile(profile)).toEqual(profile);
  for (const patch of [{locale: 'fr-FR'}, {role: 'owner'}, {revision: -1}, {revision: 0.5}]) {
    expect(() => parseProfile({...profile, ...patch})).toThrow();
  }
});
