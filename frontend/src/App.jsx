// BorderPulse — Root App with routing
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { StreamProvider } from './contexts/StreamContext';
import Sidebar from './components/Sidebar';
import StatusBar from './components/StatusBar';
import Overview from './pages/Overview';
import LiveMonitor from './pages/LiveMonitor';
import Events from './pages/Events';
import EventDetail from './pages/EventDetail';
import Zones from './pages/Zones';
import Sensors from './pages/Sensors';
import Devices from './pages/Devices';
import CameraHealth from './pages/CameraHealth';
import Analytics from './pages/Analytics';
import Settings from './pages/Settings';

export default function App() {
  return (
    <BrowserRouter>
      <StreamProvider>
        <div className="flex h-screen overflow-hidden bg-bp-bg">
          <Sidebar />
          <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
            <StatusBar />
            <main className="flex-1 overflow-hidden flex flex-col">
              <Routes>
                <Route path="/"           element={<Overview />} />
                <Route path="/monitor"    element={<LiveMonitor />} />
                <Route path="/events"     element={<Events />} />
                <Route path="/events/:id" element={<EventDetail />} />
                <Route path="/zones"      element={<Zones />} />
                <Route path="/sensors"    element={<Sensors />} />
                <Route path="/devices"    element={<Devices />} />
                <Route path="/health"     element={<CameraHealth />} />
                <Route path="/analytics"  element={<Analytics />} />
                <Route path="/settings"   element={<Settings />} />
              </Routes>
            </main>
          </div>
        </div>
      </StreamProvider>
    </BrowserRouter>
  );
}
