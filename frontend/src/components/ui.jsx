// Shared UI components

// StatusDot
export function StatusDot({ status }) {
  const cls = {
    online: 'dot-online', offline: 'dot-offline', warning: 'dot-warning',
    simulated: 'dot-simulated', healthy: 'dot-online', offline_cam: 'dot-offline',
  }[status] || 'dot-simulated';
  return <span className={`status-dot ${cls}`} />;
}

// SeverityBadge
export function SeverityBadge({ severity }) {
  const map = {
    critical: 'bg-red-900/60 text-red-300 border border-red-600',
    high:     'bg-orange-900/60 text-orange-300 border border-orange-600',
    medium:   'bg-yellow-900/60 text-yellow-300 border border-yellow-600',
    low:      'bg-blue-900/60 text-blue-300 border border-blue-600',
    info:     'bg-gray-800 text-gray-400 border border-gray-600',
  };
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-semibold uppercase tracking-wide ${map[severity] || map.info}`}>
      {severity}
    </span>
  );
}

// Card
export function Card({ children, className = '', onClick }) {
  return (
    <div
      className={`bg-bp-card border border-bp-border rounded-lg p-4 card-hover ${className}`}
      onClick={onClick}
      style={onClick ? { cursor: 'pointer' } : {}}
    >
      {children}
    </div>
  );
}

// StatCard
export function StatCard({ label, value, unit = '', color = 'text-bp-accent', icon }) {
  return (
    <Card className="flex flex-col gap-1">
      <div className="flex items-center gap-2 text-bp-muted text-xs uppercase tracking-widest font-medium">
        {icon && <span>{icon}</span>}
        {label}
      </div>
      <div className={`text-3xl font-bold mono ${color}`}>
        {value}<span className="text-base font-normal ml-1 text-bp-dim">{unit}</span>
      </div>
    </Card>
  );
}

// SectionHeader
export function SectionHeader({ title, subtitle, actions }) {
  return (
    <div className="flex items-start justify-between mb-4">
      <div>
        <h2 className="text-lg font-semibold text-bp-text">{title}</h2>
        {subtitle && <p className="text-bp-muted text-sm mt-0.5">{subtitle}</p>}
      </div>
      {actions && <div className="flex gap-2">{actions}</div>}
    </div>
  );
}

// Button
export function Btn({ children, onClick, variant = 'primary', size = 'sm', disabled, className = '' }) {
  const base = 'inline-flex items-center gap-1.5 font-medium rounded transition-all focus:outline-none';
  const sizes = { sm: 'px-3 py-1.5 text-xs', md: 'px-4 py-2 text-sm', lg: 'px-5 py-2.5 text-base' };
  const variants = {
    primary:   'bg-bp-accent/10 text-bp-accent border border-bp-accent/40 hover:bg-bp-accent/20',
    danger:    'bg-red-900/30 text-red-300 border border-red-600/50 hover:bg-red-900/50',
    warning:   'bg-yellow-900/30 text-yellow-300 border border-yellow-600/50 hover:bg-yellow-900/50',
    ghost:     'text-bp-muted border border-bp-border hover:text-bp-text hover:border-bp-muted',
    success:   'bg-green-900/30 text-green-300 border border-green-600/50 hover:bg-green-900/50',
  };
  return (
    <button
      className={`${base} ${sizes[size]} ${variants[variant]} ${disabled ? 'opacity-40 cursor-not-allowed' : ''} ${className}`}
      onClick={onClick}
      disabled={disabled}
    >
      {children}
    </button>
  );
}

// SimulatedBadge
export function SimulatedBadge({ mode }) {
  if (mode === 'REAL') return <span className="text-xs text-green-400 border border-green-700 px-1.5 py-0.5 rounded">REAL HARDWARE</span>;
  if (mode === 'SIMULATED') return <span className="text-xs text-yellow-400 border border-yellow-700 px-1.5 py-0.5 rounded">SIMULATED</span>;
  return <span className="text-xs text-red-400 border border-red-700 px-1.5 py-0.5 rounded">OFFLINE</span>;
}

// ConfBar
export function ConfBar({ value, max = 1 }) {
  const pct = Math.min(100, (value / max) * 100);
  const color = pct >= 85 ? '#ff3a3a' : pct >= 65 ? '#ffaa00' : '#00d4ff';
  return (
    <div className="conf-bar w-full">
      <div className="conf-fill" style={{ width: `${pct}%`, background: color }} />
    </div>
  );
}

// Spinner
export function Spinner() {
  return (
    <div className="flex items-center justify-center h-24">
      <div className="w-8 h-8 border-2 border-bp-border border-t-bp-accent rounded-full animate-spin" />
    </div>
  );
}
