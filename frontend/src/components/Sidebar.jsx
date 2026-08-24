// BorderPulse — Sidebar Navigation
import { NavLink } from 'react-router-dom';
import { useStream } from '../contexts/StreamContext';

const links = [
  { to: '/',          icon: '⬡', label: 'Overview'      },
  { to: '/monitor',   icon: '◉', label: 'Live Monitor'   },
  { to: '/events',    icon: '⚡', label: 'Events'        },
  { to: '/zones',     icon: '⬟', label: 'Zones'         },
  { to: '/sensors',   icon: '◈', label: 'Sensors'        },
  { to: '/devices',   icon: '◎', label: 'Devices'        },
  { to: '/health',    icon: '♡', label: 'Camera Health'  },
  { to: '/analytics', icon: '▦', label: 'Analytics'      },
  { to: '/settings',  icon: '⚙', label: 'Settings'       },
];

export default function Sidebar() {
  const { connected } = useStream();

  return (
    <aside className="w-56 flex-shrink-0 bg-bp-surface border-r border-bp-border flex flex-col h-full">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-bp-border">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded bg-bp-accent/10 border border-bp-accent/40 flex items-center justify-center text-bp-accent text-lg font-bold">
            ⬡
          </div>
          <div>
            <div className="text-sm font-bold text-bp-text tracking-wide">BorderPulse</div>
            <div className="text-xs text-bp-muted">AI Surveillance</div>
          </div>
        </div>
      </div>

      {/* Backend status */}
      <div className="px-4 py-2 border-b border-bp-border">
        <div className="flex items-center gap-2 text-xs">
          <span className={`status-dot ${connected ? 'dot-online' : 'dot-offline'}`} />
          <span className={connected ? 'text-bp-safe' : 'text-bp-danger'}>
            {connected ? 'BACKEND LIVE' : 'BACKEND OFFLINE'}
          </span>
        </div>
      </div>

      {/* Nav links */}
      <nav className="flex-1 py-3 overflow-y-auto">
        {links.map(({ to, icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-2.5 text-sm transition-all mx-2 rounded-md mb-0.5 ${
                isActive
                  ? 'bg-bp-accent/10 text-bp-accent border border-bp-accent/20'
                  : 'text-bp-muted hover:text-bp-text hover:bg-white/5'
              }`
            }
          >
            <span className="text-base w-5 text-center">{icon}</span>
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-bp-border text-xs text-bp-muted">
        <div>v1.0.0-prototype</div>
        <div className="mt-0.5 text-yellow-600/80">Radar/Ground: SIMULATED</div>
      </div>
    </aside>
  );
}
