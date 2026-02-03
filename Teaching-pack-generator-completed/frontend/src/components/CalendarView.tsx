import type { Classroom } from './ClassroomList';
import { CalendarIcon } from './icons/Icons';

interface CalendarViewProps {
  classrooms: Classroom[];
  onSelectClassroom: (classroom: Classroom) => void;
}

export default function CalendarView({ classrooms }: CalendarViewProps) {
  // Suppress unused parameters warning
  void classrooms;

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-xl p-12 border border-stone-200">
        <div className="text-center">
          <div className="flex justify-center mb-6">
            <CalendarIcon size={80} className="opacity-20" />
          </div>
          <h2 className="text-2xl font-semibold text-zinc-800 mb-3">Schedule</h2>
          <p className="text-lg text-stone-600 mb-2">This feature is under development...</p>
          <p className="text-sm text-stone-500">We are building the schedule feature so you can manage timetables and events easily.</p>
        </div>
      </div>
    </div>
  );
}
