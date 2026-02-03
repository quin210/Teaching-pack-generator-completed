import { useState } from 'react';
import './App.css';
import Login from './components/Login';
import Register from './components/Register';
import Sidebar from './components/Sidebar';
import Dashboard from './components/Dashboard';
import ClassroomList from './components/ClassroomList';
import ClassroomDetail from './components/ClassroomDetail';
import CalendarView from './components/CalendarView';
import Notifications, { NotificationBell } from './components/Notifications';
import type { Classroom } from './components/ClassroomList';
import { apiService } from './services/api';
import StudentTheoryPage from './components/StudentTheoryPage';
import { SearchIcon, HamburgerIcon } from './components/icons/Icons';

type ViewType = 'dashboard' | 'classrooms' | 'calendar' | 'settings';

function App() {
  // Check for student mode
  if (window.location.search.includes('mode=student_theory')) {
      return <StudentTheoryPage />;
  }

  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [showRegister, setShowRegister] = useState(false);
  const [userEmail, setUserEmail] = useState('');
  const [activeView, setActiveView] = useState<ViewType>('dashboard');
  const [selectedClassroom, setSelectedClassroom] = useState<Classroom | null>(null);
  const [showNotifications, setShowNotifications] = useState(false);
  const [classrooms, setClassrooms] = useState<Classroom[]>([]);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  const handleLogin = (email: string) => {
    setUserEmail(email);
    setIsLoggedIn(true);
    setShowRegister(false);
  };

  const handleRegister = (email: string) => {
    setUserEmail(email);
    setIsLoggedIn(true);
    setShowRegister(false);
  };

  const handleLogout = () => {
    apiService.logout();
    setIsLoggedIn(false);
    setUserEmail('');
    setActiveView('dashboard');
    setSelectedClassroom(null);
  };

  const handleSelectClassroom = (classroom: Classroom) => {
    setSelectedClassroom(classroom);
  };

  const handleBackToClassrooms = () => {
    setSelectedClassroom(null);
    setActiveView('classrooms');
  };

  if (!isLoggedIn) {
    if (showRegister) {
      return (
        <Register 
          onRegister={handleRegister}
          onSwitchToLogin={() => setShowRegister(false)}
        />
      );
    }
    return (
      <Login 
        onLogin={handleLogin}
        onSwitchToRegister={() => setShowRegister(true)}
      />
    );
  }

  if (selectedClassroom) {
    return (
      <div className="flex min-h-screen bg-stone-50">
        <Sidebar
          activeView={activeView}
          onViewChange={setActiveView}
          userEmail={userEmail}
          onLogout={handleLogout}
          isOpen={isSidebarOpen}
        />
        <div className={`flex-1 transition-all duration-500 ease-in-out ${isSidebarOpen ? 'ml-64' : 'ml-16'}`}>
          <ClassroomDetail
            classroom={selectedClassroom}
            onBack={handleBackToClassrooms}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-stone-50">
      {/* Sidebar */}
      <Sidebar
        activeView={activeView}
        onViewChange={setActiveView}
        userEmail={userEmail}
        onLogout={handleLogout}
        isOpen={isSidebarOpen}
      />

      {/* Main Content */}
      <div className={`flex-1 transition-all duration-500 ease-in-out ${isSidebarOpen ? 'ml-64' : 'ml-16'}`}>
        {/* Top Bar */}
        <header className="bg-white border-b border-stone-200 sticky top-0 z-40">
          <div className="px-8 py-4 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                className="p-2 rounded-lg hover:bg-stone-100 transition-colors border border-stone-300"
                title={isSidebarOpen ? "Collapse sidebar" : "Expand sidebar"}
              >
                <HamburgerIcon size={20} isOpen={isSidebarOpen} />
              </button>
              <div className="flex-1 relative max-w-md">
                <div className="absolute left-3 top-1/2 -translate-y-1/2">
                  <SearchIcon size={20} />
                </div>
                <input
                  type="text"
                  placeholder="Search classrooms, lessons..."
                  className="w-full pl-10 pr-4 py-2 border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                />
              </div>
            </div>
            <div className="flex items-center gap-4">
              <NotificationBell onClick={() => setShowNotifications(!showNotifications)} count={2} />
            </div>
          </div>
        </header>

        {/* Content Area */}
        <main className="p-8">
          {activeView === 'dashboard' && (
            <Dashboard userEmail={userEmail} onSelectClassroom={handleSelectClassroom} />
          )}
          {activeView === 'classrooms' && (
            <ClassroomList
              onSelectClassroom={handleSelectClassroom}
              onClassroomsLoad={setClassrooms}
            />
          )}
          {activeView === 'calendar' && (
            <CalendarView classrooms={classrooms} onSelectClassroom={handleSelectClassroom} />
          )}
          {activeView === 'settings' && (
            <div className="bg-white rounded-xl p-8 border border-stone-200">
              <h2 className="text-2xl font-semibold text-zinc-800 mb-4">Settings</h2>
              <p className="text-stone-600">This feature is under development...</p>
            </div>
          )}
        </main>
      </div>

      {/* Notifications Panel */}
      {showNotifications && <Notifications onClose={() => setShowNotifications(false)} />}
    </div>
  );
}

export default App;
