import { useState, useEffect } from 'react';
import { apiService } from '../services/api';
import type { Classroom } from './ClassroomList';
import { BookIcon, UsersIcon, PackageIcon, ActivityIcon, SparklesIcon, PlusIcon, UploadIcon, SettingsIcon, InfoCircleIcon, ReportIcon } from './icons/Icons';
import './icons/icon-animations.css';

interface DashboardProps {
  userEmail: string;
  onSelectClassroom: (classroom: Classroom) => void;
}

interface Stats {
  totalClassrooms: number;
  totalStudents: number;
  totalTeachingPacks: number;
  recentActivity: number;
}

interface RecentActivity {
  id: number;
  type: 'created' | 'updated' | 'generated';
  classroom: string;
  description: string;
  time: string;
}

export default function Dashboard({ userEmail, onSelectClassroom }: DashboardProps) {
  const [stats, setStats] = useState<Stats>({
    totalClassrooms: 0,
    totalStudents: 0,
    totalTeachingPacks: 0,
    recentActivity: 0,
  });
  const [recentActivities, setRecentActivities] = useState<RecentActivity[]>([]);
  const [recentClassrooms, setRecentClassrooms] = useState<Classroom[]>([]);
  const [allClassrooms, setAllClassrooms] = useState<Classroom[]>([]);
  const [loading, setLoading] = useState(true);
  const [showClassSelector, setShowClassSelector] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState('');
  
  // Create Class Modal State
  const [showCreateClassModal, setShowCreateClassModal] = useState(false);
  const [creatingClass, setCreatingClass] = useState(false);
  const [newClassData, setNewClassData] = useState({
    name: '',
    subject: '',
    grade: '',
    studentCount: 30
  });

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const classrooms = await apiService.getClassrooms();
      setAllClassrooms(classrooms);
      
      // Calculate stats
      const totalStudents = classrooms.reduce((sum: number, c: Classroom) => sum + c.student_count, 0);
      
      setStats({
        totalClassrooms: classrooms.length,
        totalStudents,
        totalTeachingPacks: classrooms.length * 3, // Estimate
        recentActivity: 12, // Mock data
      });

      // Get recent classrooms (last 4)
      const colors = ['bg-blue-500', 'bg-green-500', 'bg-purple-500', 'bg-pink-500'];
      const recent = classrooms.slice(0, 4).map((c: Classroom, idx: number) => ({
        ...c,
        color: colors[idx % colors.length],
      }));
      setRecentClassrooms(recent);

      // Mock recent activities
      setRecentActivities([
        {
          id: 1,
          type: 'generated',
          classroom: classrooms[0]?.name || 'Math 10A1',
          description: 'Created a new teaching pack',
          time: '5 minutes ago',
        },
        {
          id: 2,
          type: 'created',
          classroom: classrooms[1]?.name || 'Literature 11A2',
          description: 'Created a new class',
          time: '2 hours ago',
        },
        {
          id: 3,
          type: 'updated',
          classroom: classrooms[0]?.name || 'Math 10A1',
          description: 'Updated class info',
          time: '1 day ago',
        },
      ]);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateClass = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newClassData.name || !newClassData.subject || !newClassData.grade) {
      alert('Please fill in all required fields.');
      return;
    }

    setCreatingClass(true);
    try {
      await apiService.createClassroom(
        newClassData.name,
        newClassData.grade,
        newClassData.subject,
        newClassData.studentCount
      );
      
      // Refresh dashboard data
      await fetchDashboardData();
      
      // Close modal and reset form
      setShowCreateClassModal(false);
      setNewClassData({
        name: '',
        subject: '',
        grade: '',
        studentCount: 30
      });
      alert('Class created successfully!');
    } catch (error) {
      console.error('Error creating classroom:', error);
      alert('An error occurred while creating the class.');
    } finally {
      setCreatingClass(false);
    }
  };

  const getActivityIcon = (type: RecentActivity['type']) => {
    switch (type) {
      case 'created':
        return <PlusIcon size={24} />;
      case 'updated':
        return <SettingsIcon size={24} />;
      case 'generated':
        return <SparklesIcon size={24} />;
      default:
        return <InfoCircleIcon size={24} />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-stone-600">Loading...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Welcome Section */}
      <div className="bg-gradient-to-r from-yellow-400 to-yellow-500 rounded-2xl p-8 text-white relative overflow-hidden">
        <div className="absolute top-4 right-4 opacity-20 icon-float">
          <SparklesIcon size={80} className="text-white" />
        </div>
        <div className="relative z-10">
          <h2 className="text-3xl font-bold mb-2">Hello!</h2>
          <p className="text-yellow-50">Welcome back, {userEmail}</p>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white rounded-xl p-6 border border-stone-200 hover:shadow-lg transition-all group">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-stone-600">Total classes</h3>
            <div className="p-2 icon-container-amber rounded-lg icon-hover-scale">
              <BookIcon size={28} />
            </div>
          </div>
          <p className="text-3xl font-bold text-zinc-800">{stats.totalClassrooms}</p>
          <p className="text-xs text-stone-500 mt-1">+2 classes this week</p>
        </div>

        <div className="bg-white rounded-xl p-6 border border-stone-200 hover:shadow-lg transition-all group">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-stone-600">Total students</h3>
            <div className="p-2 icon-container-blue rounded-lg icon-hover-scale">
              <UsersIcon size={28} />
            </div>
          </div>
          <p className="text-3xl font-bold text-zinc-800">{stats.totalStudents}</p>
          <p className="text-xs text-stone-500 mt-1">Average {Math.round(stats.totalStudents / stats.totalClassrooms)} students/class</p>
        </div>

        <div className="bg-white rounded-xl p-6 border border-stone-200 hover:shadow-lg transition-all group">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-stone-600">Teaching Packs</h3>
            <div className="p-2 icon-container-purple rounded-lg icon-hover-scale">
              <PackageIcon size={28} />
            </div>
          </div>
          <p className="text-3xl font-bold text-zinc-800">{stats.totalTeachingPacks}</p>
          <p className="text-xs text-stone-500 mt-1">3 new packs today</p>
        </div>

        <div className="bg-white rounded-xl p-6 border border-stone-200 hover:shadow-lg transition-all group">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-stone-600">Activity</h3>
            <div className="p-2 icon-container-green rounded-lg icon-hover-scale">
              <ActivityIcon size={28} />
            </div>
          </div>
          <p className="text-3xl font-bold text-zinc-800">{stats.recentActivity}</p>
          <p className="text-xs text-stone-500 mt-1">Last 7 days</p>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Classrooms */}
        <div className="lg:col-span-2 bg-white rounded-xl p-6 border border-stone-200">
          <h3 className="text-lg font-semibold text-zinc-800 mb-4">Recent classes</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {recentClassrooms.map((classroom) => (
              <div
                key={classroom.id}
                onClick={() => onSelectClassroom(classroom)}
                className="border border-stone-200 rounded-lg overflow-hidden cursor-pointer hover:shadow-md hover:border-stone-300 transition-all group"
              >
                <div className={`${classroom.color} h-16 relative`}>
                  <div className="absolute inset-0 bg-gradient-to-br from-black/5 to-transparent" />
                </div>
                <div className="p-4">
                  <h4 className="font-semibold text-zinc-800 mb-1 group-hover:text-yellow-600 transition-colors">
                    {classroom.name}
                  </h4>
                  <p className="text-sm text-stone-600">{classroom.subject}</p>
                  <div className="flex items-center justify-between text-xs text-stone-500 mt-2">
                    <span>Grade {classroom.grade}</span>
                    <span>{classroom.student_count} HS</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Activity */}
        <div className="bg-white rounded-xl p-6 border border-stone-200">
          <h3 className="text-lg font-semibold text-zinc-800 mb-4">Recent activity</h3>
          <div className="space-y-4">
            {recentActivities.map((activity) => (
              <div key={activity.id} className="flex items-start gap-3 pb-4 border-b border-stone-100 last:border-0">
                <div className="mt-0.5">{getActivityIcon(activity.type)}</div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-zinc-800">{activity.description}</p>
                  <p className="text-xs text-stone-500">{activity.classroom}</p>
                  <p className="text-xs text-stone-400 mt-1">{activity.time}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-white rounded-xl p-6 border border-stone-200">
        <h3 className="text-lg font-semibold text-zinc-800 mb-4">Quick actions</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <button 
            onClick={() => setShowCreateClassModal(true)}
            className="p-4 border border-stone-200 rounded-lg hover:bg-stone-50 hover:border-yellow-500 transition-all group"
          >
            <div className="flex justify-center mb-2">
              <PlusIcon size={32} className="group-hover:scale-110 transition-transform" />
            </div>
            <span className="text-sm font-medium text-zinc-800 group-hover:text-yellow-600">Create new class</span>
          </button>
          <div className="relative">
            <input
              type="file"
              id="dashboard-upload"
              accept=".pdf,.png,.jpg,.jpeg"
              className="hidden"
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  setSelectedFile(e.target.files[0]);
                  setShowClassSelector(true);
                  e.target.value = ''; // Reset
                }
              }}
            />
            <button 
              onClick={() => document.getElementById('dashboard-upload')?.click()}
              className="w-full p-4 border border-stone-200 rounded-lg hover:bg-stone-50 hover:border-yellow-500 transition-all group"
            >
              <div className="flex justify-center mb-2">
                <UploadIcon size={32} className="group-hover:scale-110 transition-transform" />
              </div>
              <span className="text-sm font-medium text-zinc-800 group-hover:text-yellow-600">Upload lesson</span>
            </button>
          </div>
          <button className="p-4 border border-stone-200 rounded-lg hover:bg-stone-50 hover:border-yellow-500 transition-all group">
            <div className="flex justify-center mb-2">
              <ReportIcon size={32} className="group-hover:scale-110 transition-transform" />
            </div>
            <span className="text-sm font-medium text-zinc-800 group-hover:text-yellow-600">View reports</span>
          </button>
          <button className="p-4 border border-stone-200 rounded-lg hover:bg-stone-50 hover:border-yellow-500 transition-all group">
            <div className="flex justify-center mb-2">
              <SettingsIcon size={32} className="group-hover:scale-110 transition-transform" />
            </div>
            <span className="text-sm font-medium text-zinc-800 group-hover:text-yellow-600">Settings</span>
          </button>
        </div>
      </div>

      {/* Class Selector Modal */}
      {showClassSelector && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl p-6 max-w-md w-full shadow-2xl">
            <h3 className="text-xl font-bold mb-4">Choose a class to create a lesson</h3>
            <p className="text-stone-600 mb-4 text-sm">
              File: <span className="font-semibold">{selectedFile?.name}</span>
            </p>
            
            <div className="max-h-60 overflow-y-auto space-y-2 mb-6">
              {allClassrooms.length === 0 ? (
                <div className="text-center py-4 text-stone-500">
                  No classes yet. Please create a class first.
                </div>
              ) : (
                allClassrooms.map(cls => (
                  <button
                    key={cls.id}
                    onClick={async () => {
                      if (!selectedFile) return;
                      setShowClassSelector(false);
                      setUploading(true);
                      setUploadMessage('Uploading file and starting processing...');
                      
                      try {
                        // Generate using API
                        const numGroups = 4;
                        const numStudents = cls.student_count || 30;
                        
                        await apiService.generateTeachingPacks(
                          selectedFile,
                          cls.id,
                          numGroups,
                          numStudents
                        );
                        
                        setUploadMessage('Analyzing lesson... (Redirecting to class)');
                        
                        // Short delay then navigate
                        setTimeout(() => {
                           setUploading(false);
                           onSelectClassroom(cls);
                        }, 1000);
                        
                      } catch (err) {
                        console.error(err);
                        alert('Error: ' + (err instanceof Error ? err.message : 'Upload failed'));
                        setUploading(false);
                      }
                    }}
                    className="w-full text-left p-3 rounded-lg border border-stone-200 hover:border-yellow-500 hover:bg-yellow-50 transition-colors flex justify-between items-center group"
                  >
                    <div>
                        <div className="font-semibold text-zinc-800 group-hover:text-yellow-700">{cls.name}</div>
                        <div className="text-xs text-stone-500">{cls.subject} - Grade {cls.grade}</div>
                    </div>
                    <div className="text-stone-400 group-hover:text-yellow-600">
                        <PlusIcon size={20} />
                    </div>
                  </button>
                ))
              )}
            </div>
            
            <button
              onClick={() => {
                setShowClassSelector(false);
                setSelectedFile(null);
              }}
              className="w-full py-2 text-stone-500 font-medium hover:text-zinc-800 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Loading Overlay */}
      {uploading && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
           <div className="bg-white rounded-xl p-8 flex flex-col items-center">
              <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-yellow-500 mb-4"></div>
              <p className="text-zinc-800 font-medium">{uploadMessage}</p>
           </div>
        </div>
      )}

      {/* Create Class Modal */}
      {showCreateClassModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl p-6 max-w-md w-full shadow-2xl">
            <h3 className="text-xl font-bold mb-4 text-zinc-800">Created a new class</h3>
            
            <form onSubmit={handleCreateClass} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-stone-700 mb-1">Class name</label>
                <input
                  type="text"
                  required
                  placeholder="Example: Math 10A1"
                  className="w-full px-3 py-2 border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-yellow-500"
                  value={newClassData.name}
                  onChange={(e) => setNewClassData({...newClassData, name: e.target.value})}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-stone-700 mb-1">Subject</label>
                <input
                  type="text"
                  required
                  placeholder="Example: Mathematics"
                  className="w-full px-3 py-2 border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-yellow-500"
                  value={newClassData.subject}
                  onChange={(e) => setNewClassData({...newClassData, subject: e.target.value})}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-stone-700 mb-1">Grade</label>
                  <select
                    className="w-full px-3 py-2 border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-yellow-500"
                    value={newClassData.grade}
                    onChange={(e) => setNewClassData({...newClassData, grade: e.target.value})}
                    required
                  >
                    <option value="">Select grade</option>
                    {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map(g => (
                      <option key={g} value={g.toString()}>Grade {g}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-stone-700 mb-1">Student count</label>
                  <input
                    type="number"
                    min="1"
                    max="100"
                    required
                    className="w-full px-3 py-2 border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-yellow-500"
                    value={newClassData.studentCount}
                    onChange={(e) => setNewClassData({...newClassData, studentCount: parseInt(e.target.value) || 0})}
                  />
                </div>
              </div>

              <div className="flex gap-3 mt-6 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreateClassModal(false)}
                  className="flex-1 py-2 px-4 border border-stone-300 rounded-lg text-stone-700 hover:bg-stone-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creatingClass}
                  className="flex-1 py-2 px-4 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 transition-colors disabled:opacity-50 flex justify-center items-center gap-2"
                >
                  {creatingClass ? (
                    'Creating...'
                  ) : (
                    <>
                      <PlusIcon size={20} />
                      <span>Create class</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
