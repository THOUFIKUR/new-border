// BorderPulse — Sidebar Navigation
import { NavLink } from 'react-router-dom';
import { useStream } from '../contexts/StreamContext';

const links = [
  { to: '/',          icon: '01', label: 'COMMAND CENTER' },
  { to: '/monitor',   icon: '02', label: 'LIVE MONITOR'   },
  { to: '/events',    icon: '03', label: 'EVENTS'         },
  { to: '/zones',     icon: '04', label: 'ZONES'          },
  { to: '/settings',  icon: '05', label: 'SYSTEM'         },
  { to: '/analytics', icon: '06', label: 'ANALYTICS'      },
];

export default function Sidebar() {
  const { connected } = useStream();

  return (
    <aside className="w-56 flex-shrink-0 bg-bp-surface border-r border-bp-border flex flex-col h-full">
      {/* Logo Header */}
      <div className="px-5 py-5 border-b border-bp-border">
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded border border-bp-green/50 flex items-center justify-center text-bp-green text-xs font-mono font-bold shadow-[0_0_10px_rgba(0,255,102,0.2)]">
            ◇
          </div>
          <div>
            <div className="text-xs font-bold text-bp-green tracking-widest font-mono">BORDERPULSE</div>
            <div className="text-[10px] text-bp-muted font-mono uppercase tracking-wider">COMMAND CENTER</div>
          </div>
        </div>
      </div>

      {/* System Status Indicator */}
      <div className="px-4 py-2 border-b border-bp-border bg-bp-surface/50 font-mono">
        <div className="flex items-center gap-2 text-[11px]">
          <span className={`w-2 h-2 rounded-full ${connected ? 'bg-bp-green shadow-[0_0_8px_#00FF66] animate-pulse' : 'bg-bp-danger shadow-[0_0_8px_#FF2A2A]'}`} />
          <span className={connected ? 'text-bp-green font-bold' : 'text-bp-danger font-bold'}>
            {connected ? '● SYSTEM LIVE' : '○ SYSTEM OFFLINE'}
          </span>
        </div>
      </div>

      {/* Nav links */}
      <nav className="flex-1 py-3 overflow-y-auto space-y-1 font-mono">
        {links.map(({ to, icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 text-xs transition-all mx-2 rounded border ${
                isActive
                  ? 'bg-bp-green/10 text-bp-green border-bp-green/40 shadow-[0_0_12px_rgba(0,255,102,0.15)] font-bold'
                  : 'text-bp-muted border-transparent hover:text-bp-text hover:bg-white/5 hover:border-bp-border'
              }`
            }
          >
            <span className="text-[10px] text-bp-dim font-bold">{icon}</span>
            <span className="tracking-wider">{label}</span>
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-bp-border text-[10px] font-mono text-bp-muted">
        <div className="text-bp-dim">MODEL: <span className="text-bp-green font-bold">YOLO26n</span></div>
        <div className="mt-0.5">GPIO26: <span className="text-bp-accent">REAL</span></div>
      </div>
    </aside>
  );
}
