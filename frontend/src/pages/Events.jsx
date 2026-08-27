// BorderPulse — Events Page
import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { getEvents, updateEvent } from '../services/api';
import { Card, SeverityBadge, SectionHeader, Btn, Spinner } from '../components/ui';

function timeAgo(ts) {
  if (!ts) return '—';
  const d = Math.floor(Date.now() / 1000 - ts);
  if (d < 60) return `${d}s ago`;
  if (d < 3600) return `${Math.floor(d / 60)}m ago`;
  return `${Math.floor(d / 3600)}h ago`;
}

const STATUS_FILTER = ['all', 'active', 'acknowledged', 'resolved', 'false_positive'];

export default function Events() {
  const [events,  setEvents]  = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter,  setFilter]  = useState('all');
  const [meta,    setMeta]    = useState({});
  const nav = useNavigate();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const q = filter !== 'all' ? `?status=${filter}` : '';
      const data = await getEvents(q);
      setEvents(data.events || []);
      setMeta({ total: data.total, active: data.active_count, today: data.today_count });
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => { load(); const t = setInterval(load, 8000); return () => clearInterval(t); }, [load]);

  const act = async (id, action) => {
    try {
      await updateEvent(id, action);
      await load();
    } catch (e) { console.error(e); }
  };

  const severityIcon = (s) => ({ critical: '🔴', high: '🟠', medium: '🟡', low: '🔵', info: '⚪' }[s] || '⚪');

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      <SectionHeader
        title="Security Events"
        subtitle={`${meta.active ?? 0} active · ${meta.today ?? 0} today · ${meta.total ?? 0} total`}
      />

      {/* Filter tabs */}
      <div className="flex gap-2 flex-wrap">
        {STATUS_FILTER.map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1.5 rounded text-xs font-semibold uppercase tracking-wide transition-colors ${
              filter === f
                ? 'bg-bp-accent/20 text-bp-accent border border-bp-accent/40'
                : 'text-bp-muted border border-bp-border hover:text-bp-text'
            }`}
          >
            {f.replace('_', ' ')}
          </button>
        ))}
        <button onClick={load} className="ml-auto px-3 py-1.5 text-xs text-bp-muted border border-bp-border rounded hover:text-bp-text">
          ↻ Refresh
        </button>
      </div>

      {/* Events table */}
      {loading ? <Spinner /> : events.length === 0 ? (
        <Card className="text-center py-12 text-bp-muted">
          <div className="text-4xl mb-2">◉</div>
          <div>No events found</div>
        </Card>
      ) : (
        <div className="space-y-2">
          {events.map(ev => (
            <div
              key={ev.id}
              className={`bg-bp-card border rounded-lg px-4 py-3 card-hover cursor-pointer transition-all ${
                ev.status === 'active' && ev.severity === 'critical'
                  ? 'border-red-600/60 alert-critical'
                  : ev.status === 'active'
                  ? 'border-yellow-600/40'
                  : 'border-bp-border'
              }`}
              onClick={() => nav(`/events/${ev.id}`)}
            >
              <div className="flex items-start gap-3">
                <span className="text-xl mt-0.5">{severityIcon(ev.severity)}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-semibold text-bp-text truncate">{ev.reason}</span>
                    <SeverityBadge severity={ev.severity} />
                    <span className={`text-xs px-2 py-0.5 rounded uppercase font-semibold border ${
                      ev.status === 'active' ? 'border-red-600/50 text-red-300' :
                      ev.status === 'acknowledged' ? 'border-yellow-600/50 text-yellow-300' :
                      ev.status === 'resolved' ? 'border-green-600/50 text-green-300' :
                      'border-gray-600 text-gray-400'
                    }`}>
                      {ev.status}
                    </span>
                  </div>
                  <div className="text-xs text-bp-muted mt-1 flex flex-wrap gap-3">
                    <span className="mono">{ev.event_code}</span>
                    <span>Type: {ev.event_type}</span>
                    <span>Conf: {(ev.confidence * 100).toFixed(0)}%</span>
                    <span>{timeAgo(ev.started_at)}</span>
                  </div>
                </div>
                {/* Actions */}
                {ev.status === 'active' && (
                  <div className="flex gap-2 shrink-0" onClick={e => e.stopPropagation()}>
                    <Btn variant="warning" size="sm" onClick={() => act(ev.id, 'acknowledge')}>Ack</Btn>
                    <Btn variant="ghost" size="sm" onClick={() => act(ev.id, 'resolve')}>Resolve</Btn>
                    <Btn variant="danger" size="sm" onClick={() => act(ev.id, 'false_positive')}>FP</Btn>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
