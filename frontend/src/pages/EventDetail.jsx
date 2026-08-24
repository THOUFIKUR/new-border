// BorderPulse — Event Detail Page
import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getEvent, getEventMedia, updateEvent } from '../services/api';
import { Card, SeverityBadge, Btn, Spinner } from '../components/ui';

function Row({ label, value, mono }) {
  return (
    <div className="flex justify-between py-2 border-b border-bp-border last:border-0">
      <span className="text-xs text-bp-muted">{label}</span>
      <span className={`text-xs text-bp-text ${mono ? 'mono' : ''}`}>{value ?? '—'}</span>
    </div>
  );
}

export default function EventDetail() {
  const { id } = useParams();
  const nav    = useNavigate();
  const [event, setEvent]   = useState(null);
  const [media, setMedia]   = useState([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const [ev, med] = await Promise.all([getEvent(id), getEventMedia(id).catch(() => ({ media: [] }))]);
      setEvent(ev.event);
      setMedia(med.media || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [id]);

  const act = async (action) => {
    await updateEvent(id, action).catch(console.error);
    await load();
  };

  if (loading) return <div className="p-4"><Spinner /></div>;
  if (!event) return (
    <div className="p-4 text-center text-bp-muted">
      <div className="text-4xl mb-2">⊘</div>
      <div>Event not found</div>
      <Btn onClick={() => nav('/events')} variant="ghost" className="mt-4">← Back to Events</Btn>
    </div>
  );

  const meta = event.metadata || {};
  const evidence = meta.sensor_evidence || {};

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      {/* Header */}
      <div className="flex items-start gap-3">
        <button onClick={() => nav('/events')} className="text-bp-muted hover:text-bp-text mt-1">←</button>
        <div className="flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="text-lg font-bold text-bp-text">{event.reason}</h1>
            <SeverityBadge severity={event.severity} />
          </div>
          <div className="text-xs text-bp-muted mono mt-0.5">{event.event_code}</div>
        </div>
        {event.status === 'active' && (
          <div className="flex gap-2">
            <Btn variant="warning" onClick={() => act('acknowledge')}>Acknowledge</Btn>
            <Btn variant="success" onClick={() => act('resolve')}>Resolve</Btn>
            <Btn variant="danger"  onClick={() => act('false_positive')}>False Positive</Btn>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Event details */}
        <Card>
          <div className="text-xs text-bp-muted uppercase tracking-widest mb-3">Event Details</div>
          <Row label="Event Code"  value={event.event_code}        mono />
          <Row label="Type"        value={event.event_type} />
          <Row label="Status"      value={event.status?.toUpperCase()} />
          <Row label="Severity"    value={event.severity?.toUpperCase()} />
          <Row label="Confidence"  value={`${((event.confidence || 0) * 100).toFixed(1)}%`} />
          <Row label="Zone ID"     value={event.zone_id}            mono />
          <Row label="Camera ID"   value={event.camera_id}          mono />
          <Row label="Track ID"    value={event.track_id} />
          <Row label="Started"     value={event.started_at ? new Date(event.started_at * 1000).toLocaleString() : '—'} />
          <Row label="Ended"       value={event.ended_at  ? new Date(event.ended_at  * 1000).toLocaleString() : 'Ongoing'} />
        </Card>

        {/* Fusion evidence */}
        <Card>
          <div className="text-xs text-bp-muted uppercase tracking-widest mb-3">Fusion Evidence</div>
          <Row label="Fused Score"         value={`${((meta.fused_score || 0) * 100).toFixed(1)}%`} />
          <Row label="Is Critical"         value={meta.is_critical ? 'YES' : 'NO'} />
          <Row label="Vision"              value={`${((evidence.vision_contribution || 0) * 100).toFixed(1)}%`} />
          <Row label="Radar (SIMULATED)"   value={`${((evidence.radar_contribution  || 0) * 100).toFixed(1)}%`} />
          <Row label="Ground (SIMULATED)"  value={`${((evidence.ground_contribution || 0) * 100).toFixed(1)}%`} />
          <Row label="Temporal"            value={`${((evidence.temporal_contribution || 0) * 100).toFixed(1)}%`} />
          <div className="mt-3 p-2 bg-yellow-900/20 rounded text-xs text-yellow-600/80 border border-yellow-700/30">
            ⚠ Radar and Ground contributions are from SIMULATED sensors — not real hardware
          </div>
        </Card>
      </div>

      {/* Media */}
      <Card>
        <div className="text-xs text-bp-muted uppercase tracking-widest mb-3">Evidence Media</div>
        {media.length === 0 ? (
          <div className="text-bp-muted text-sm py-4 text-center">No media captured for this event</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {media.map((m, i) => (
              <div key={i} className="bg-black/30 rounded p-3 border border-bp-border">
                <div className="text-xs text-bp-muted uppercase mb-1">{m.media_type}</div>
                {m.public_url ? (
                  m.media_type === 'snapshot'
                    ? <img src={m.public_url} alt="snapshot" className="w-full rounded" />
                    : <video src={m.public_url} controls className="w-full rounded" />
                ) : (
                  <div className="text-xs text-bp-muted">
                    Local: <span className="mono">{m.storage_path}</span>
                    {m.metadata?.upload_status === 'FAILED' && (
                      <span className="ml-2 text-red-400">Upload failed</span>
                    )}
                  </div>
                )}
                <div className="text-xs text-bp-muted mt-1 mono">{m.storage_path}</div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
