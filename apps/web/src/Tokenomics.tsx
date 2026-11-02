import { useEffect, useRef, useState } from 'react';
import { InterfaceError } from './api';
import { formatTimestamp, useI18n } from './i18n';
import { kpiKeys, loadTokenomics } from './tokenomicsApi';
import type { Metric, Period, Section, TokenomicsTab } from './tokenomicsApi';

const labels = ['Estimated cost', 'Observed tokens', 'Average cost per execution', 'Cache hit ratio', 'Token goodput', 'Execution count'];
const tabs: TokenomicsTab[] = ['Overview', 'Breakdown', 'FOCUS'];
export function displayMetric(metric: Metric, locale: string): string {
  if (metric.value === null) return '—';
  const value = Number(metric.value);
  if (metric.unit === 'money' && value !== 0 && Math.abs(value) < 0.00000001) return new Intl.NumberFormat(locale, { style: 'currency', currency: 'USD', notation: 'scientific', maximumFractionDigits: 4 }).format(value);
  if (metric.unit === 'money') return new Intl.NumberFormat(locale, { style: 'currency', currency: 'USD', minimumFractionDigits: 4, maximumFractionDigits: 8 }).format(value);
  if (metric.unit === 'ratio') return new Intl.NumberFormat(locale, { style: 'percent', maximumFractionDigits: 2 }).format(value);
  return new Intl.NumberFormat(locale, { maximumFractionDigits: 3 }).format(value);
}
function Bars({ title, section }: { title: string; section: Section }) {
  const { t, locale } = useI18n();
  const max = Math.max(0, ...section.rows.map(row => Number(row.metric.value ?? 0)));
  return <section className="tok-section"><h2>{t(title)}</h2>
    <p>{t(section.status === 'unavailable' ? 'No supported measurement.' : section.status === 'empty' ? 'No observations in this period.' : 'Observed tokens · partial coverage')}</p>
    <>
      <div className={title === 'Daily usage (UTC)' ? 'tok-chart tok-daily' : 'tok-chart'} aria-hidden="true">
        {section.rows.map(row => <div className="tok-bar-row" key={row.key}>
          <span>{t(row.key)}</span><span className="tok-track"><i data-value={row.metric.value ?? 'missing'}
            style={{ [title === 'Daily usage (UTC)' ? 'height' : 'width']: `${max && row.metric.value !== null ? Math.max(0, Number(row.metric.value)) / max * 100 : 0}%` }} /></span>
          <span>{displayMetric(row.metric, locale)}</span>
        </div>)}
      </div>
      <div className="tok-table" tabIndex={0} role="region" aria-label={t(title) + ' — ' + t('Data table')}>
        <table><caption>{t(title)} — {t('Data table')}</caption><thead><tr><th scope="col">{t('Category')}</th><th scope="col">{t('Value')}</th><th scope="col">{t('Unit')}</th><th scope="col">{t('Coverage')}</th></tr></thead>
          <tbody>{section.rows.map(row => <tr key={row.key}><th scope="row">{t(row.key)}</th><td>{displayMetric(row.metric, locale)}</td><td>{t(row.metric.unit)}</td><td>{t(row.metric.value === null ? 'unavailable' : row.metric.coverage)}</td></tr>)}</tbody>
        </table>
      </div>
    </>
  </section>;
}
export default function Tokenomics({ period, setPeriod, tab, setTab }: {
  period: Period; setPeriod: (value: Period) => void; tab: TokenomicsTab; setTab: (value: TokenomicsTab) => void;
}) {
  const { t, locale, timezone } = useI18n();
  const [data, setData] = useState<Awaited<ReturnType<typeof loadTokenomics>> | null>(null);
  const [refresh, setRefresh] = useState(0);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState('');
  const pending = useRef<{ key: string; promise: ReturnType<typeof loadTokenomics> } | null>(null);
  useEffect(() => {
    let active = true;
    setBusy(true); setError(''); setData(null);
    const key = `${period}:${refresh}`;
    // Share StrictMode's repeated effect subscription; never issue a second refresh.
    if (pending.current?.key !== key) pending.current = { key, promise: loadTokenomics(period) };
    pending.current.promise.then(result => { if (active) setData(result); })
      .catch(reason => { if (active) setError(reason instanceof InterfaceError ? reason.key : 'Tokenomics unavailable.'); })
      .finally(() => { if (active) setBusy(false); });
    return () => { active = false; };
  }, [period, refresh]);
  function changeTab(event: React.KeyboardEvent<HTMLButtonElement>, index: number) {
    const next = event.key === 'ArrowRight' ? (index + 1) % tabs.length : event.key === 'ArrowLeft' ? (index + tabs.length - 1) % tabs.length : event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : -1;
    if (next < 0) return;
    event.preventDefault(); setTab(tabs[next]); document.getElementById(`tok-tab-${next}`)?.focus();
  }
  const view = data?.dashboard;
  return <div className="tokenomics" aria-busy={busy}>
    <p className="tok-intro">{t('Usage from Agent Engine. Estimates from official provider prices.')}</p>
    <div className="tok-filters"><label>{t('Period')}<select value={period} disabled={busy} onChange={event => setPeriod(event.target.value as Period)}>
      <option value="7d">{t('Last 7 days')}</option><option value="30d">{t('Last 30 days')}</option><option value="90d">{t('Last 90 days')}</option>
    </select></label><button className="secondary" disabled={busy} onClick={() => setRefresh(n => n + 1)}>{t('Refresh usage')}</button></div>
    <details className="tok-note"><summary>{t('Custom date range')}</summary><p>{t('Historical date ranges are not supported by this source. Use a trailing period.')}</p></details>
    <p role="status">{busy ? t('Loading usage…') : error ? '' : t('Partial data. Missing values are not zero.')}</p>
    {error && <p role="alert">{t(error)}</p>}
    {view && <>
      <p className="tok-meta">{t('Observed at:')} {formatTimestamp(view.kpis.total_cost.observed_at, locale, timezone)} · {timezone}</p>
      <p className="tok-meta">{t('Requested window:')} {formatTimestamp(view.kpis.total_cost.window.start, locale, timezone)} — {formatTimestamp(view.kpis.total_cost.window.end, locale, timezone)}</p>
      <p className="tok-meta">{t('Source boundaries may differ. Daily buckets remain in UTC.')}</p>
      <div className="tok-kpis">{kpiKeys.map((key, index) => <article className="tok-card" key={key}>
        <h2>{t(labels[index])}</h2><strong>{displayMetric(view.kpis[key], locale)}</strong>
        <span className="tok-badge">{t(view.kpis[key].basis)}</span>
        <details><summary>{t('Data details')}</summary><p>{t('Coverage')}: {t(view.kpis[key].coverage)}</p>
          <p>{t(key === 'total_cost' ? 'Public-price scenario, not an invoice. Other fees and cache behavior are excluded.' : 'Only native measurements are shown. Unsupported attribution remains unavailable.')}</p>
          <p>{t('Unit')}: {view.kpis[key].unit === 'money' ? 'USD' : t(view.kpis[key].unit)}</p>
          <p>{t('Telecom workspace')} · {view.kpis[key].source === 'agent_engine_cost_dashboard' ? 'Agent Engine' : t('Official pricing')}</p></details>
      </article>)}</div>
      {view.estimate && <details className="tok-note"><summary>{t('Estimate assumptions and price source')}</summary>
        <p>{t('Standard service. Assumed context band:')} {t(view.estimate.price.context_band)}. {t('All input treated as uncached; cache reads and writes are unknown.')}</p>
        <p>{t('Current prices applied retrospectively. Excludes voice, embeddings, tools, gateway fees, discounts and taxes. Not an upper bound.')}</p>
        <p>{view.estimate.price.model} · {formatTimestamp(view.estimate.price.checked_at, locale, timezone)}</p>
        <a href={view.estimate.price.source_url} target="_blank" rel="noreferrer">{t('Official pricing')}</a>
      </details>}
      <div className="tok-tabs" role="tablist" aria-label={t('Tokenomics views')}>{tabs.map((name, index) => <button
        id={`tok-tab-${index}`} key={name} role="tab" aria-selected={tab === name} aria-controls="tok-tabpanel" tabIndex={tab === name ? 0 : -1}
        onClick={() => setTab(name)} onKeyDown={event => changeTab(event, index)}>{t(name)}</button>)}</div>
      <div id="tok-tabpanel" role="tabpanel" aria-labelledby={`tok-tab-${tabs.indexOf(tab)}`} tabIndex={0}>
        {tab === 'Overview' && <>
          <Bars title="Application usage" section={view.applications} />
          <Bars title="Daily usage (UTC)" section={view.daily} />
          <section className="tok-section"><h2>{t('Anomalies')}</h2><p>{t('Insufficient comparable daily data. No anomaly inferred.')}</p></section>
        </>}
        {tab === 'Breakdown' && <>
          <Bars title="Context attribution" section={view.context} />
          {view.context.status === 'unavailable' && <ul className="tok-unavailable">{['Instructions', 'History', 'Semantic memory', 'RAG chunks', 'Tool results', 'User input', 'Reasoning tokens', 'Final answer'].map(label => <li key={label}>{t(label)} <span>{t('unavailable')}</span></li>)}</ul>}
          <Bars title="Token categories" section={view.token_categories} />
          <p>{t('Input and output are disjoint. Cached input is a subset, never added to the total.')}</p>
          <Bars title="Models" section={view.models} />
          <p>{t('Model names are source-reported. Unmeasured embedding and voice usage is excluded.')}</p>
          <Bars title="Agents" section={view.agents} /><Bars title="Business categories" section={view.intents} />
        </>}
        {tab === 'FOCUS' && data && <section className="tok-section"><h2>{t('FOCUS-like records')}</h2>
          <p>{t('FOCUS-like presentation; not certified billing records. Estimates never populate billed cost.')}</p>
          <p>{t(data.focus.status === 'unavailable' ? 'Native invoice and SKU records are unavailable.' : data.focus.status === 'empty' ? 'No observations in this period.' : 'Partial data. Missing values are not zero.')}</p>
          <div className="tok-table" tabIndex={0} role="region" aria-label={t('FOCUS-like records')}><table><caption>{t('FOCUS-like records')}</caption>
            <thead><tr>{['Period', 'Provider', 'SKU', 'Quantity', 'Unit', 'Billed cost', 'Estimated cost'].map(label => <th key={label} scope="col">{t(label)}</th>)}</tr></thead>
            <tbody>{data.focus.records.map(row => <tr key={row.record_id}><td>{formatTimestamp(row.consumed.window.start, locale, timezone)} — {formatTimestamp(row.consumed.window.end, locale, timezone)}</td><td>{row.provider}</td><td>{row.sku}</td><td>{displayMetric(row.consumed, locale)}</td><td>{t(row.consumed.unit)}</td><td>{displayMetric(row.billed_cost, locale)}</td><td>{row.estimated_cost ? displayMetric(row.estimated_cost, locale) : '—'}</td></tr>)}</tbody>
          </table></div>
          <p>{t('No supported source pagination.')}</p>
        </section>}
      </div>
    </>}
  </div>;
}
