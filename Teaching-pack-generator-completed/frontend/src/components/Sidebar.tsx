import { HomeIcon, BookIcon, CalendarIcon, SettingsIcon } from './icons/Icons';

interface SidebarProps {
  activeView: 'dashboard' | 'classrooms' | 'calendar' | 'settings';
  onViewChange: (view: 'dashboard' | 'classrooms' | 'calendar' | 'settings') => void;
  userEmail: string;
  onLogout: () => void;
  isOpen: boolean;
}

export default function Sidebar({ activeView, onViewChange, userEmail, onLogout, isOpen }: SidebarProps) {
  const menuItems = [
    { id: 'dashboard', label: 'Dashboard', IconComponent: HomeIcon },
    { id: 'classrooms', label: 'Classrooms', IconComponent: BookIcon },
    { id: 'calendar', label: 'Calendar', IconComponent: CalendarIcon },
    { id: 'settings', label: 'Settings', IconComponent: SettingsIcon },
  ] as const;

  return (
    <div className={`bg-white border-r border-stone-200 h-screen flex flex-col fixed left-0 top-0 transition-all duration-500 ease-in-out z-50 ${isOpen ? 'w-64' : 'w-16'}`}>
      {/* Logo & Brand */}
      <div className={`p-6 border-b border-stone-200 transition-all duration-300 ${isOpen ? '' : 'px-4'}`}>
        <h1 className={`text-xl font-bold text-zinc-800 ${isOpen ? '' : 'hidden'}`}>Teaching Packs</h1>
        <p className={`text-xs text-stone-500 mt-1 ${isOpen ? '' : 'hidden'}`}>Pro Builder</p>
        {!isOpen && (
          <div className="flex justify-center transition-all duration-300">
            <div className="w-8 h-8 bg-linear-to-br from-yellow-400 to-yellow-600 rounded-full flex items-center justify-center text-white font-bold text-sm">
              TP
            </div>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className={`flex-1 p-4 space-y-2 transition-all duration-300 ${isOpen ? '' : 'px-2'}`}>
        {menuItems.map((item) => (
          <button
            key={item.id}
            onClick={() => onViewChange(item.id)}
            className={`
              w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-300
              ${
                activeView === item.id
                  ? 'bg-yellow-50 text-yellow-600 font-medium'
                  : 'text-stone-600 hover:bg-stone-50 hover:text-zinc-800'
              }
              ${isOpen ? '' : 'px-3 justify-center'}
            `}
            title={!isOpen ? item.label : undefined}
          >
            <item.IconComponent size={20} />
            <span className={`${isOpen ? '' : 'hidden'}`}>{item.label}</span>
          </button>
        ))}
      </nav>

      {/* User Section */}
      <div className={`p-4 border-t border-stone-200 transition-all duration-300 ${isOpen ? '' : 'px-2'}`}>
        <div className={`flex items-center gap-3 mb-3 transition-all duration-300 ${isOpen ? '' : 'justify-center'}`}>
          <div className="w-10 h-10 bg-linear-to-br from-yellow-400 to-yellow-600 rounded-full flex items-center justify-center text-white font-semibold">
            {userEmail.charAt(0).toUpperCase()}
          </div>
          <div className={`flex-1 min-w-0 ${isOpen ? '' : 'hidden'}`}>
            <p className="text-sm font-medium text-zinc-800 truncate">{userEmail}</p>
            <p className="text-xs text-stone-500">Teacher</p>
          </div>
        </div>
        <button
          onClick={onLogout}
          className={`w-full px-4 py-2 text-sm text-stone-600 hover:text-zinc-800 hover:bg-stone-100 rounded-lg transition-all duration-300 ${isOpen ? '' : 'px-3 justify-center'}`}
          title={!isOpen ? 'Sign out' : undefined}
        >
          <svg className={`w-5 h-5 transition-all duration-300 ${isOpen ? 'mr-3' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
          </svg>
          <span className={`${isOpen ? '' : 'hidden'}`}>Sign out</span>
        </button>
      </div>
    </div>
  );
}
