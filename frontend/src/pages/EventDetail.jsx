// BorderPulse — Event Detail Page
// Shows full event metadata, fusion evidence breakdown bars, and media.
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

// Visual bar for fusion contribution display
function EvidenceBar({ label, value, maxWeight, color, note, badge }) {
  const pct = Math.round((value || 0) * 100);
  const barWidth = maxWeight > 0 ? Math.round((value / maxWeight) * 100) : 0;
  return (
    <div className="py-2 border-b border-bp-border last:border-0">
      <div className="flex justify-between items-center mb-1.5">
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono font-bold text-bp-dim">{label}</span>
          {badge && (
            <span className="text-xs border border-yellow-700/40 text-yellow-600/70 px-1 rounded">{badge}</span>
          )}
        </div>
        <span className="text-xs font-bold mono text-bp-text">{pct}%</span>
      </div>
      <div className="h-2 bg-bp-border rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${color}`}
          style={{ width: `${barWidth}%` }}
        />
      </div>
      {note && <div className="text-xs text-bp-muted mt-1 italic">{note}</div>}
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

  const meta     = event.metadata || {};
  const evidence = meta.sensor_evidence || {};

  // Extract actual stored contribution values
  const visionContrib   = evidence.vision_contribution   || 0;
  const radarContrib    = evidence.radar_contribution    || 0;
  const groundContrib   = evidence.ground_contribution   || 0;
  const temporalContrib = evidence.temporal_contribution || 0;
  const maxContrib = Math.max(visionContrib, radarContrib, groundContrib, temporalContrib, 0.01);

  // Temporal confirmation evidence
  const confirmCount    = evidence.person_confirm_count    ?? null;
  const confirmRequired = evidence.person_confirm_required ?? 4;

  // "Why did this alarm fire?" explanation
  const isHighConf = (event.confidence || 0) >= 0.85;
  const alarmExplanation = isHighConf
    ? `High-confidence detection (${((event.confidence || 0) * 100).toFixed(1)}% ≥ 85%) triggered fast path — temporal confirmation skipped.`
    : confirmCount !== null
      ? `Person detected in restricted zone for ${confirmCount}/${confirmRequired} consecutive frames (temporal confirmation complete).`
      : 'Alarm was confirmed through the decision engine.';

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
          {confirmCount !== null && (
            <Row label="Temporal Conf." value={`${confirmCount} / ${confirmRequired} frames`} />
          )}
        </Card>

        {/* Fusion evidence breakdown */}
        <Card>
          <div className="text-xs text-bp-muted uppercase tracking-widest mb-1">Why Did This Alarm Fire?</div>
          <div className="text-xs text-bp-dim mb-3 italic">{alarmExplanation}</div>

          <div className="text-xs text-bp-muted uppercase tracking-widest mb-2">Fusion Evidence</div>

          <div className="mb-1">
            <Row label="Fused Score" value={`${((meta.fused_score || 0) * 100).toFixed(1)}%`} />
          </div>

          <EvidenceBar
            label="VISION"
            value={visionContrib}
            maxWeight={maxContrib}
            color="bg-bp-accent"
            note="YOLO object classification (only source that identifies humans)"
          />
          <EvidenceBar
            label="RADAR"
            value={radarContrib}
            maxWeight={maxContrib}
            color="bg-yellow-500"
            note={evidence.radar_note || 'Motion evidence only — not a human classifier'}
            badge={evidence.radar_active !== undefined ? (evidence.radar_active ? 'ACTIVE' : 'CLEAR') : 'SIMULATED'}
          />
          <EvidenceBar
            label="GROUND"
            value={groundContrib}
            maxWeight={maxContrib}
            color="bg-orange-500"
            note={evidence.ground_note || 'Physical disturbance — not a human classifier'}
            badge={evidence.ground_active ? 'TRIGGERED' : 'CLEAR'}
          />
          <EvidenceBar
            label="TEMPORAL"
            value={temporalContrib}
            maxWeight={maxContrib}
            color="bg-purple-500"
            note="Consecutive-frame confirmation weight"
          />

          {(radarContrib > 0 || groundContrib > 0) && (
            <div className="mt-3 p-2 bg-yellow-900/20 rounded text-xs text-yellow-600/80 border border-yellow-700/30">
              ⚠ Radar and Ground contributions indicate supporting evidence.
              Human identity is determined exclusively by YOLO vision.
            </div>
          )}
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
