import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { 
  Home, 
  Briefcase, 
  GitBranch, 
  Cpu, 
  Save, 
  Bug, 
  Activity, 
  Settings,
  Upload,
  Search,
  PlayCircle
} from 'lucide-react';

const Navigation: React.FC = () => {
  const location = useLocation();
  
  const navItems = [
    { path: '/', icon: Home, label: 'Dashboard' },
    { path: '/jobs', icon: Briefcase, label: 'Jobs' },
    { path: '/workflows', icon: GitBranch, label: 'Workflows' },
    { path: '/agents', icon: Cpu, label: 'Agents' },
    { path: '/ingestion', icon: Upload, label: 'Ingestion' },
    { path: '/topics/discover', icon: Search, label: 'Topics' },
    { path: '/agents/test', icon: PlayCircle, label: 'Test' },
    { path: '/checkpoints', icon: Save, label: 'Checkpoints' },
    { path: '/debug', icon: Bug, label: 'Debug' },
    { path: '/flows', icon: Activity, label: 'Flows' },
    { path: '/config', icon: Settings, label: 'Config' },
  ];
  
  return (
    <nav className="bg-gray-900 text-white border-b border-gray-800">
      <div className="flex items-center justify-between px-4 py-3">
        {/* Logo/Brand */}
        <Link to="/" className="flex items-center gap-3">
          <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-lg">U</span>
          </div>
          <span className="text-xl font-bold">UCOP</span>
        </Link>
        
        {/* Navigation Links */}
        <div className="flex gap-1">
          {navItems.map(item => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`
                  flex items-center gap-2 px-4 py-2 rounded-md transition-colors
                  ${isActive 
                    ? 'bg-blue-600 text-white' 
                    : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                  }
                `}
              >
                <Icon size={18} />
                <span className="text-sm font-medium">{item.label}</span>
              </Link>
            );
          })}
        </div>
        
        {/* Right side - User/Settings */}
        <div className="flex items-center gap-4">
          <div className="text-sm text-gray-400">
            System Online
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navigation;
