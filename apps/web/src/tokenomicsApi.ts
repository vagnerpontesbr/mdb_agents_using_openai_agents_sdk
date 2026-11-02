import { InterfaceError, request } from './api';

export type Period = '7d' | '30d' | '90d';
export type TokenomicsTab = 'Overview' | 'Breakdown' | 'FOCUS';
export type Metric = { value: string | null; unit: string; basis: string; currency: string | null; source: string;
  scope: string; observed_at: string; window: { start: string; end: string }; coverage: string; reason: string | null };
export type Row = { key: string; metric: Metric };
export type Section = { status: string; rows: Row[]; reason: string | null };
export const kpiKeys = ['total_cost', 'observed_tokens', 'average_cost_per_execution', 'cache_hit_ratio', 'token_goodput', 'execution_count'] as const;
export const sectionKeys = ['applications', 'daily', 'anomalies', 'context', 'token_categories', 'models', 'agents', 'intents'] as const;
export type Dashboard = Record<typeof sectionKeys[number], Section> & {
  schema_version: 1; kpis: Record<typeof kpiKeys[number], Metric> & { partial: boolean };
  estimate: { amount_usd: string; basis: 'estimated'; price: { source_url: string; checked_at: string; model: string; context_band: string }; assumptions: string[] } | null;
};
export type Focus = { schema_version: 1; status: string; reason: string | null; next_cursor: string | null;
  records: { record_id: string; provider: string; sku: string; consumed: Metric; billed_cost: Metric; estimated_cost: Metric | null }[] };
const sources = ['https://developers.openai.com/api/docs/pricing', 'https://platform.claude.com/docs/en/about-claude/pricing'];
function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error();
  return value as Record<string, unknown>;
}
function date(value: unknown): boolean { return typeof value === 'string' && Number.isFinite(Date.parse(value)); }
export function parseMetric(value: unknown): Metric {
  const m = object(value), w = object(m.window);
  if (!['tokens', 'seconds', 'calls', 'executions', 'ratio', 'money'].includes(String(m.unit)) ||
      !['observed', 'estimated', 'billed', 'unavailable'].includes(String(m.basis)) ||
      !['complete', 'partial', 'unknown'].includes(String(m.coverage)) ||
      typeof m.source !== 'string' || typeof m.scope !== 'string' || !date(m.observed_at) || !date(w.start) || !date(w.end) ||
      Date.parse(String(w.end)) <= Date.parse(String(w.start)) || Date.parse(String(w.end)) - Date.parse(String(w.start)) > 90 * 86400000 ||
      (m.unit === 'money' ? m.currency !== 'USD' : m.currency !== null) ||
      (m.basis === 'billed' && m.unit !== 'money') ||
      (m.value === null) !== (m.basis === 'unavailable')) throw new Error();
  if (m.value !== null && (typeof m.value !== 'string' || !/^-?\d+(\.\d+)?([eE][+-]?\d+)?$/.test(m.value) ||
      !Number.isFinite(Number(m.value)) || Math.abs(Number(m.value)) > Number.MAX_SAFE_INTEGER ||
      (m.unit !== 'money' && Number(m.value) < 0) || (m.unit === 'ratio' && Number(m.value) > 1) ||
      (['tokens', 'calls', 'executions'].includes(String(m.unit)) && !Number.isSafeInteger(Number(m.value))))) throw new Error();
  if (m.value === null && (typeof m.reason !== 'string' || !m.reason)) throw new Error();
  return m as unknown as Metric;
}
function section(value: unknown): Section {
  const s = object(value);
  if (!['available', 'empty', 'partial', 'unavailable'].includes(String(s.status)) || !Array.isArray(s.rows) || s.rows.length > 100) throw new Error();
  const keys = new Set<string>();
  for (const value of s.rows) {
    const row = object(value);
    if (typeof row.key !== 'string' || !row.key || keys.has(row.key)) throw new Error();
    keys.add(row.key); parseMetric(row.metric);
  }
  if ((['empty', 'unavailable'].includes(String(s.status)) && s.rows.length) ||
      (s.status === 'available' && !s.rows.length) ||
      (['unavailable', 'partial'].includes(String(s.status)) && (typeof s.reason !== 'string' || !s.reason))) throw new Error();
  return s as unknown as Section;
}
export function parseDashboard(value: unknown): Dashboard {
  try {
    const d = object(value), kpis = object(d.kpis);
    if (d.schema_version !== 1 || typeof kpis.partial !== 'boolean') throw new Error();
    const units = ['money', 'tokens', 'money', 'ratio', 'ratio', 'executions'];
    const total = parseMetric(kpis.total_cost);
    function scope(m: Metric) {
      if (m.scope !== total.scope || m.window.start !== total.window.start || m.window.end !== total.window.end) throw new Error();
      if ((m.coverage !== 'complete' || m.value === null) && !kpis.partial) throw new Error();
    }
    kpiKeys.forEach((key, index) => { const m = parseMetric(kpis[key]); if (m.unit !== units[index]) throw new Error(); scope(m); });
    sectionKeys.forEach(key => { const s = section(d[key]); s.rows.forEach(row => scope(row.metric));
      if (['partial', 'unavailable'].includes(s.status) && !kpis.partial) throw new Error(); });
    if (total.basis === 'estimated') {
      const e = object(d.estimate), p = object(e.price);
      if (e.basis !== 'estimated' || e.amount_usd !== total.value || !sources.includes(String(p.source_url)) ||
          !date(p.checked_at) || typeof p.model !== 'string' || !['short', 'long'].includes(String(p.context_band)) ||
          !Array.isArray(e.assumptions) || !e.assumptions.length || e.assumptions.some(v => typeof v !== 'string')) throw new Error();
    } else if (d.estimate !== null) throw new Error();
    return d as unknown as Dashboard;
  } catch { throw new InterfaceError('Tokenomics response could not be verified.'); }
}
export function parseFocus(value: unknown): Focus {
  try {
    const f = object(value);
    if (f.schema_version !== 1 || !['available', 'empty', 'partial', 'unavailable'].includes(String(f.status)) ||
        !Array.isArray(f.records) || f.records.length > 100 ||
        f.next_cursor !== null || (f.status === 'available' && !f.records.length) ||
        (['empty', 'unavailable'].includes(String(f.status)) && (f.records.length || f.next_cursor)) ||
        (['partial', 'unavailable'].includes(String(f.status)) && typeof f.reason !== 'string')) throw new Error();
    const ids = new Set<string>();
    for (const item of f.records) {
      const r = object(item), consumed = parseMetric(r.consumed), billed = parseMetric(r.billed_cost);
      if (typeof r.record_id !== 'string' || ids.has(r.record_id) || typeof r.provider !== 'string' || typeof r.sku !== 'string' ||
          !['tokens', 'seconds', 'calls'].includes(consumed.unit) || billed.unit !== 'money' || !['billed', 'unavailable'].includes(billed.basis)) throw new Error();
      ids.add(r.record_id);
      const costs = [billed];
      if (r.estimated_cost !== null) { const e = parseMetric(r.estimated_cost); if (e.unit !== 'money' || e.basis !== 'estimated') throw new Error(); costs.push(e); }
      if (costs.some(cost => cost.scope !== consumed.scope || cost.window.start !== consumed.window.start || cost.window.end !== consumed.window.end)) throw new Error();
    }
    return f as unknown as Focus;
  } catch { throw new InterfaceError('Tokenomics response could not be verified.'); }
}
export async function loadTokenomics(period: Period): Promise<{ dashboard: Dashboard; focus: Focus }> {
  const [dashboard, focus] = await Promise.all([
    request(`/api/admin/tokenomics/dashboard?period=${period}`),
    request(`/api/admin/tokenomics/focus-records?period=${period}&limit=100`),
  ]);
  return { dashboard: parseDashboard(dashboard), focus: parseFocus(focus) };
}
