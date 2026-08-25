// BorderPulse — Analytics Page
import { useEffect, useState } from 'react';
import { getAnalytics } from '../services/api';
import { Card, SectionHeader, StatCard, Spinner } from '../components/ui';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

const COLORS = ['#ff3a3a', '#ff7043', '#ffaa00', '#64b5f6', '#6b7fa3'];

const CHART_STYLE = {
  background: 'transparent',
  fontSize: 11,
  color: '#6b7fa3',
};

export default function Analytics() {
  const [data,    setData]    = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try { setData(await getAnalytics()); } catch (e) { console.error(e); }
      setLoading(false);
    };
    load();
    const t = setInterval(load, 15000);
    return () => clearInterval(t);
  }, []);

  if (loading) return <div className="p-4"><Spinner /></div>;

  const byType = Object.entries(data?.by_type || {}).map(([k, v]) => ({ name: k, value: v }));
  const bySev  = Object.entries(data?.by_severity || {}).map(([k, v]) => ({ name: k, value: v }));

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      <SectionHeader title="Analytics" subtitle="Event statistics and system performance" />

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard label="Total Events"    value={data?.total_events ?? 0}         color="text-bp-accent" icon="▦" />
        <StatCard label="Events Today"    value={data?.events_today ?? 0}         color="text-bp-warning" icon="📅" />
        <StatCard label="Last Hour"       value={data?.events_last_hour ?? 0}     color="text-bp-safe" icon="⏱" />
        <StatCard label="False Positives" value={data?.false_positives ?? 0}      color="text-bp-muted" icon="⊘" />
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard label="Avg Confidence"  value={`${((data?.avg_confidence ?? 0)*100).toFixed(1)}%`} color="text-bp-accent" />
        <StatCard label="Inferences"      value={data?.inference_count ?? 0}      color="text-bp-dim" icon="◉" />
        <StatCard label="Camera FPS"      value={(data?.camera_fps ?? 0).toFixed(1)} unit="fps" color="text-bp-safe" icon="⌗" />
        <StatCard label="Camera Status"   value={data?.camera_uptime ? 'ONLINE' : 'OFFLINE'} color={data?.camera_uptime ? 'text-bp-safe' : 'text-bp-danger'} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Events by type */}
        <Card>
          <div className="text-xs text-bp-muted uppercase tracking-widest mb-3">Events by Type</div>
          {byType.length === 0 ? (
            <div className="text-bp-muted text-sm text-center py-8">No events recorded</div>
          ) : (
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={byType} style={CHART_STYLE}>
                <XAxis dataKey="name" tick={{ fill: '#6b7fa3', fontSize: 10 }} />
                <YAxis tick={{ fill: '#6b7fa3', fontSize: 10 }} />
                <Tooltip contentStyle={{ background: '#111d2e', border: '1px solid #1a2d47', color: '#e2e8f0' }} />
                <Bar dataKey="value" fill="#00d4ff" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>

        {/* Events by severity */}
        <Card>
          <div className="text-xs text-bp-muted uppercase tracking-widest mb-3">Events by Severity</div>
          {bySev.length === 0 ? (
            <div className="text-bp-muted text-sm text-center py-8">No events recorded</div>
          ) : (
            <div className="flex items-center">
              <ResponsiveContainer width="60%" height={180}>
                <PieChart>
                  <Pie
                    data={bySev}
                    cx="50%"
                    cy="50%"
                    innerRadius={40}
                    outerRadius={70}
                    dataKey="value"
                    paddingAngle={3}
                  >
                    {bySev.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Pie>
                  <Tooltip contentStyle={{ background: '#111d2e', border: '1px solid #1a2d47', color: '#e2e8f0' }} />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex-1 space-y-1.5">
                {bySev.map((item, i) => (
                  <div key={item.name} className="flex items-center gap-2 text-xs">
                    <div className="w-2 h-2 rounded-full" style={{ background: COLORS[i % COLORS.length] }} />
                    <span className="text-bp-dim capitalize">{item.name}</span>
                    <span className="ml-auto mono text-bp-text">{item.value}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>
      </div>

      {/* False alarm metrics */}
      <Card>
        <div className="text-xs text-bp-muted uppercase tracking-widest mb-3">False-Alarm Resilience Metrics</div>
        {(() => {
          const total          = data?.total_events ?? 0;
          const falsePos       = data?.false_positives ?? 0;
          // confirmed = total - false positives (resolved/acknowledged treated as genuine)
          const confirmed      = Math.max(0, total - falsePos);
          const fpRate         = total > 0 ? (falsePos / total) * 100 : null;
          const confirmRate    = total > 0 ? (confirmed / total) * 100 : null;
          const insufficient   = total < 3;

          return insufficient ? (
            <div className="text-center py-6">
              <div className="text-2xl mb-2 text-bp-muted">⊘</div>
              <div className="text-sm text-bp-muted">Insufficient labeled events</div>
              <div className="text-xs text-bp-dim mt-1">
                Mark events as 'False Positive' or 'Resolve' to populate this section.
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <div className="text-bp-muted text-xs mb-1">Total Events</div>
                <div className="text-xl font-bold mono text-bp-text">{total}</div>
              </div>
              <div>
                <div className="text-bp-muted text-xs mb-1">Confirmed Events</div>
                <div className="text-xl font-bold mono text-bp-safe">{confirmed}</div>
              </div>
              <div>
                <div className="text-bp-muted text-xs mb-1">False Positives</div>
                <div className="text-xl font-bold mono text-bp-danger">{falsePos}</div>
              </div>
              <div>
                <div className="text-bp-muted text-xs mb-1">FP Rate</div>
                <div className={`text-xl font-bold mono ${fpRate > 20 ? 'text-bp-danger' : 'text-bp-safe'}`}>
                  {fpRate !== null ? `${fpRate.toFixed(1)}%` : '—'}
                </div>
              </div>
              <div className="col-span-2 md:col-span-4">
                <div className="text-bp-muted text-xs mb-1">Confirmed-Event Rate</div>
                <div className="h-2 bg-bp-border rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full bg-bp-safe transition-all"
                    style={{ width: confirmRate !== null ? `${confirmRate}%` : '0%' }}
                  />
                </div>
                <div className="text-xs text-bp-muted mt-1">{confirmRate !== null ? `${confirmRate.toFixed(1)}% of events were genuine` : '—'}</div>
              </div>
            </div>
          );
        })()}
        <div className="mt-3 text-xs text-bp-muted">
          Based on operator-labelled resolutions. Rates improve as more events are reviewed.
        </div>
      </Card>

      {/* Detection Quality (existing) */}
      <Card>
        <div className="text-xs text-bp-muted uppercase tracking-widest mb-3">Detection Quality</div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div>
            <div className="text-bp-muted text-xs mb-1">False Positive Rate</div>
            <div className="text-xl font-bold mono text-bp-accent">
              {data?.total_events > 0
                ? `${((data.false_positives / data.total_events) * 100).toFixed(1)}%`
                : '—'}
            </div>
          </div>
          <div>
            <div className="text-bp-muted text-xs mb-1">Average Confidence</div>
            <div className="text-xl font-bold mono text-bp-accent">
              {`${((data?.avg_confidence ?? 0) * 100).toFixed(1)}%`}
            </div>
          </div>
          <div>
            <div className="text-bp-muted text-xs mb-1">Total Inferences</div>
            <div className="text-xl font-bold mono text-bp-accent">
              {(data?.inference_count ?? 0).toLocaleString()}
            </div>
          </div>
        </div>
        <div className="mt-3 text-xs text-bp-muted">
          Note: Confidence and fusion weight values are engineering starting points.
          Calibrate thresholds using actual operational data.
        </div>
      </Card>
    </div>
  );
}
