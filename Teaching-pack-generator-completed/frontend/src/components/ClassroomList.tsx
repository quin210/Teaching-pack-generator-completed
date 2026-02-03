import { useState, useEffect, useCallback } from 'react';
import apiService from '../services/api';
import { PlusIcon, SearchIcon, GridIcon, ListIcon } from './icons/Icons';

export interface Classroom {
  id: number;
  name: string;
  subject: string;
  grade: string;
  student_count: number;
  created_at: string;
  color?: string; // Optional for UI purposes
}

interface ClassroomListProps {
  onSelectClassroom: (classroom: Classroom) => void;
  onClassroomsLoad?: (classrooms: Classroom[]) => void;
}

export default function ClassroomList({ onSelectClassroom, onClassroomsLoad }: ClassroomListProps) {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newClassName, setNewClassName] = useState('');
  const [newSubject, setNewSubject] = useState('');
  const [newGrade, setNewGrade] = useState('');
  const [newStudentCount, setNewStudentCount] = useState(30);
  const [studentListFile, setStudentListFile] = useState<File | null>(null);
  const [numGroups, setNumGroups] = useState(4);
  const [classrooms, setClassrooms] = useState<Classroom[]>([]);
  const [filteredClassrooms, setFilteredClassrooms] = useState<Classroom[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterSubject, setFilterSubject] = useState('all');
  const [filterGrade, setFilterGrade] = useState('all');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

  const fetchClassrooms = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getClassrooms();
      // Add random colors for UI
      const colors = ['bg-blue-500', 'bg-green-500', 'bg-purple-500', 'bg-pink-500', 'bg-orange-500'];
      const classroomsWithColors = data.map((classroom: Classroom, index: number) => ({
        ...classroom,
        color: colors[index % colors.length],
      }));
      setClassrooms(classroomsWithColors);
      setFilteredClassrooms(classroomsWithColors);
      onClassroomsLoad?.(classroomsWithColors);
    } catch (err) {
      setError('Failed to load classrooms');
      console.error('Error fetching classrooms:', err);
    } finally {
      setLoading(false);
    }
  }, [onClassroomsLoad]);

  // Fetch classrooms on component mount
  useEffect(() => {
    fetchClassrooms();
  }, [fetchClassrooms]);

  const handleCreateClass = async () => {
    if (!newClassName.trim() || !newSubject.trim() || !newGrade.trim()) {
      return;
    }

    try {
      setCreating(true);
      setError(null);
      
      const classroom = await apiService.createClassroom(
        newClassName.trim(),
        newGrade.trim(),
        newSubject.trim(),
        newStudentCount
      );

      // If student list file is provided, upload and create groups
      if (studentListFile && classroom.id) {
        try {
          await apiService.uploadStudentsAndCreateGroups(
            classroom.id,
            studentListFile,
            numGroups
          );
        } catch (uploadErr) {
          console.error('Error uploading students:', uploadErr);
          // Continue even if upload fails - classroom is created
        }
      }

      // Reset form
      setNewClassName('');
      setNewSubject('');
      setNewGrade('');
      setNewStudentCount(30);
      setStudentListFile(null);
      setNumGroups(4);
      setShowCreateModal(false);

      // Refresh classrooms list
      await fetchClassrooms();
    } catch (err) {
      setError('Failed to create classroom');
      console.error('Error creating classroom:', err);
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteClassroom = async (classroomId: number) => {
    if (!confirm('Are you sure you want to delete this class?')) {
      return;
    }

    try {
      await apiService.deleteClassroom(classroomId);
      await fetchClassrooms();
    } catch (err) {
      setError('Failed to delete classroom');
      console.error('Error deleting classroom:', err);
    }
  };

  // Get unique subjects and grades for filters
  const uniqueSubjects = Array.from(new Set(classrooms.map((c) => c.subject)));
  const uniqueGrades = Array.from(new Set(classrooms.map((c) => c.grade))).sort();

  return (
    <div className="space-y-6">
      {/* Header Section */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-zinc-800">All classes</h2>
          <p className="text-sm text-stone-600 mt-1">
            {filteredClassrooms.length} classes found
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="px-5 py-2.5 bg-yellow-500 hover:bg-yellow-600 text-white font-medium rounded-lg transition-colors flex items-center gap-2"
        >
          <PlusIcon size={20} />
          Create new class
        </button>
      </div>

      {/* Search and Filters */}
      <div className="bg-white rounded-xl p-6 border border-stone-200">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Search */}
          <div className="md:col-span-2 relative">
            <div className="absolute left-3 top-1/2 -translate-y-1/2">
              <SearchIcon size={20} />
            </div>
            <input
              type="text"
              placeholder="Search by class name or subject..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-yellow-500 focus:border-transparent"
            />
          </div>

          {/* Subject Filter */}
          <select
            value={filterSubject}
            onChange={(e) => setFilterSubject(e.target.value)}
            className="px-4 py-2.5 border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-yellow-500 focus:border-transparent"
          >
            <option value="all">All subjects</option>
            {uniqueSubjects.map((subject) => (
              <option key={subject} value={subject}>
                {subject}
              </option>
            ))}
          </select>

          {/* Grade Filter */}
          <select
            value={filterGrade}
            onChange={(e) => setFilterGrade(e.target.value)}
            className="px-4 py-2.5 border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-yellow-500 focus:border-transparent"
          >
            <option value="all">All grades</option>
            {uniqueGrades.map((grade) => (
              <option key={grade} value={grade}>
                Grade {grade}
              </option>
            ))}
          </select>
        </div>

        {/* View Mode Toggle */}
        <div className="flex items-center gap-2 mt-4">
          <span className="text-sm text-stone-600">View:</span>
          <button
            onClick={() => setViewMode('grid')}
            className={`px-3 py-1.5 rounded-lg text-sm flex items-center gap-2 ${
              viewMode === 'grid'
                ? 'bg-yellow-100 text-yellow-600'
                : 'text-stone-600 hover:bg-stone-100'
            }`}
          >
            <GridIcon size={16} />
            Grid
          </button>
          <button
            onClick={() => setViewMode('list')}
            className={`px-3 py-1.5 rounded-lg text-sm flex items-center gap-2 ${
              viewMode === 'list'
                ? 'bg-yellow-100 text-yellow-600'
                : 'text-stone-600 hover:bg-stone-100'
            }`}
          >
            <ListIcon size={16} />
            List
          </button>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-600">{error}</p>
        </div>
      )}

      {/* Loading State */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="text-stone-600">Loading class list...</div>
        </div>
      ) : filteredClassrooms.length === 0 ? (
        <div className="bg-white rounded-xl p-12 border border-stone-200 text-center">
          <div className="flex justify-center mb-4">
            <SearchIcon size={64} className="opacity-20" />
          </div>
          <h3 className="text-lg font-semibold text-zinc-800 mb-2">
            No classes found
          </h3>
          <p className="text-stone-600">
            Try adjusting your filters or create a new class.
          </p>
        </div>
      ) : (
        /* Classroom Grid/List */
        <div
          className={
            viewMode === 'grid'
              ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6'
              : 'space-y-4'
          }
        >
          {filteredClassrooms.map((classroom) => (
            viewMode === 'grid' ? (
              <div
                key={classroom.id}
                className="bg-white rounded-xl border border-stone-200 overflow-hidden hover:shadow-lg hover:border-stone-300 transition-all group relative"
              >
                <div 
                  onClick={() => onSelectClassroom(classroom)}
                  className="cursor-pointer"
                >
                  <div className={`${classroom.color} h-24 relative`}>
                    <div className="absolute inset-0 bg-linear-to-br from-black/5 to-transparent" />
                  </div>
                  <div className="p-5">
                    <h3 className="text-lg font-semibold text-zinc-800 mb-1 group-hover:text-yellow-600 transition-colors">
                      {classroom.name}
                    </h3>
                    <p className="text-sm text-stone-600 mb-3">{classroom.subject}</p>
                    <div className="flex items-center justify-between text-sm text-stone-500">
                      <span>Grade {classroom.grade}</span>
                      <span>{classroom.student_count} students</span>
                    </div>
                  </div>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeleteClassroom(classroom.id);
                  }}
                  className="absolute top-2 right-2 w-8 h-8 bg-red-500/90 hover:bg-red-600 text-white rounded-lg opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center"
                  title="Delete class"
                >
                  🗑️
                </button>
              </div>
            ) : (
              <div
                key={classroom.id}
                className="bg-white rounded-xl border border-stone-200 p-5 hover:shadow-lg hover:border-stone-300 transition-all group flex items-center gap-4 relative"
              >
                <div 
                  onClick={() => onSelectClassroom(classroom)}
                  className="flex items-center gap-4 flex-1 cursor-pointer"
                >
                  <div className={`${classroom.color} w-16 h-16 rounded-lg shrink-0`} />
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-zinc-800 mb-1 group-hover:text-yellow-600 transition-colors">
                      {classroom.name}
                    </h3>
                    <p className="text-sm text-stone-600">{classroom.subject} - Grade {classroom.grade}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-2xl font-bold text-zinc-800">{classroom.student_count}</p>
                    <p className="text-xs text-stone-500">students</p>
                  </div>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeleteClassroom(classroom.id);
                  }}
                  className="w-8 h-8 bg-red-500/90 hover:bg-red-600 text-white rounded-lg opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center shrink-0"
                  title="Delete class"
                >
                  🗑️
                </button>
              </div>
            )
          ))}
        </div>
      )}

      {/* Create Classroom Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl">
            <h3 className="text-xl font-semibold text-zinc-800 mb-4">Create a new class</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-zinc-800 mb-1.5">
                  Class name
                </label>
                <input
                  type="text"
                  value={newClassName}
                  onChange={(e) => setNewClassName(e.target.value)}
                  className="w-full px-4 py-2.5 border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-yellow-500 focus:border-transparent"
                  placeholder="e.g., Math 10A1"
                  disabled={creating}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-zinc-800 mb-1.5">
                  Subject
                </label>
                <input
                  type="text"
                  value={newSubject}
                  onChange={(e) => setNewSubject(e.target.value)}
                  className="w-full px-4 py-2.5 border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-yellow-500 focus:border-transparent"
                  placeholder="e.g., Mathematics"
                  disabled={creating}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-zinc-800 mb-1.5">
                  Grade
                </label>
                <input
                  type="text"
                  value={newGrade}
                  onChange={(e) => setNewGrade(e.target.value)}
                  className="w-full px-4 py-2.5 border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-yellow-500 focus:border-transparent"
                  placeholder="VD: 10"
                  disabled={creating}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-zinc-800 mb-1.5">
                  Student count
                </label>
                <input
                  type="number"
                  value={newStudentCount}
                  onChange={(e) => setNewStudentCount(parseInt(e.target.value) || 30)}
                  className="w-full px-4 py-2.5 border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-yellow-500 focus:border-transparent"
                  placeholder="VD: 30"
                  min="1"
                  max="100"
                  disabled={creating}
                />
              </div>

              <div className="border-t border-stone-200 pt-4">
                <label className="block text-sm font-medium text-zinc-800 mb-1.5">
                  📋 Student list (Optional)
                  <span className="text-xs text-zinc-500 ml-2">Excel/CSV with scores</span>
                </label>
                <input
                  type="file"
                  accept=".xlsx,.xls,.csv"
                  onChange={(e) => setStudentListFile(e.target.files?.[0] || null)}
                  className="w-full px-4 py-2.5 border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-yellow-500 focus:border-transparent text-sm"
                  disabled={creating}
                />
                {studentListFile && (
                  <p className="text-xs text-green-600 mt-1">✓ {studentListFile.name}</p>
                )}
              </div>

              {studentListFile && (
                <div>
                  <label className="block text-sm font-medium text-zinc-800 mb-1.5">
                    Number of groups
                  </label>
                  <input
                    type="number"
                    min="2"
                    max="10"
                    value={numGroups}
                    onChange={(e) => setNumGroups(parseInt(e.target.value) || 4)}
                    className="w-full px-4 py-2.5 border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-yellow-500 focus:border-transparent"
                    disabled={creating}
                  />
                </div>
              )}
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowCreateModal(false)}
                className="flex-1 px-4 py-2.5 border border-stone-300 text-stone-600 hover:bg-stone-50 rounded-lg transition-colors disabled:opacity-50"
                disabled={creating}
              >
                Cancel
              </button>
              <button
                onClick={handleCreateClass}
                disabled={creating || !newClassName.trim() || !newSubject.trim() || !newGrade.trim()}
                className="flex-1 px-4 py-2.5 bg-yellow-500 hover:bg-yellow-600 disabled:bg-yellow-300 text-white font-medium rounded-lg transition-colors disabled:cursor-not-allowed"
              >
                {creating ? 'Creating...' : 'Create class'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
