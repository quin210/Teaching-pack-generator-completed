import type { InstructionGroup } from '../types';

interface GroupsTableProps {
  groups: InstructionGroup[];
  onViewPack: (group: InstructionGroup) => void;
}

export default function GroupsTable({ groups, onViewPack }: GroupsTableProps) {
  console.log('GroupsTable received groups:', groups);
  console.log('Number of groups in table:', groups.length);
  const getMasteryClass = (mastery: string) => {
    if (mastery.toLowerCase().includes('low') || mastery.toLowerCase().includes('low'))
      return 'bg-red-200/50 text-red-900 border-red-600/20';
    if (mastery.toLowerCase().includes('high'))
      return 'bg-emerald-300/60 text-emerald-900 border-emerald-500/20';
    return 'bg-yellow-100/60 text-yellow-900 border-yellow-400/20';
  };

  return (
    <table className="w-full border-separate border-spacing-y-3 mt-4">
      <thead>
        <tr>
          <th className="bg-stone-50/60 px-4 py-3.5 text-left font-semibold text-zinc-900 text-sm tracking-tight first:rounded-l-xl last:rounded-r-xl">Group</th>
          <th className="bg-stone-50/60 px-4 py-3.5 text-left font-semibold text-zinc-900 text-sm tracking-tight">Pack ID</th>
          <th className="bg-stone-50/60 px-4 py-3.5 text-left font-semibold text-zinc-900 text-sm tracking-tight">Students</th>
          <th className="bg-stone-50/60 px-4 py-3.5 text-left font-semibold text-zinc-900 text-sm tracking-tight">Focus</th>
          <th className="bg-stone-50/60 px-4 py-3.5 text-left font-semibold text-zinc-900 text-sm tracking-tight">Level</th>
          <th className="bg-stone-50/60 px-4 py-3.5 text-left font-semibold text-zinc-900 text-sm tracking-tight">Missing Skills</th>
          <th className="bg-stone-50/60 px-4 py-3.5 text-left font-semibold text-zinc-900 text-sm tracking-tight">Rationale</th>
          <th className="bg-stone-50/60 px-4 py-3.5 text-left font-semibold text-zinc-900 text-sm tracking-tight first:rounded-l-xl last:rounded-r-xl">Actions</th>
        </tr>
      </thead>
      <tbody>
        {groups.map((group) => (
          <tr key={group.id} className="group">
            <td className="px-4 py-4.5 text-sm bg-white/80 transition-all duration-300 first:rounded-l-xl group-hover:bg-white group-hover:shadow-md group-hover:scale-[1.01]">
              <strong>{group.groupName || group.id}</strong>
            </td>
            <td className="px-4 py-4.5 text-sm bg-white/80 transition-all duration-300 group-hover:bg-white group-hover:shadow-md group-hover:scale-[1.01]">
              {group.pack?.id || 'N/A'} {/* Extract pack ID from pack */}
            </td>
            <td className="px-4 py-4.5 text-sm bg-white/80 transition-all duration-300 group-hover:bg-white group-hover:shadow-md group-hover:scale-[1.01]">
              {group.students && group.students.length > 0 ? (
                <div className="flex flex-col gap-1">
                  <div className="font-semibold text-purple-700">{group.students.length} students</div>
                  <details className="text-xs text-zinc-600">
                    <summary className="cursor-pointer hover:text-purple-600">View list</summary>
                    <ul className="mt-2 space-y-1 pl-4">
                      {group.students.map((student, idx) => (
                        <li key={idx} className="list-disc">{student}</li>
                      ))}
                    </ul>
                  </details>
                </div>
              ) : (
                <span className="text-zinc-400 italic">None</span>
              )}
            </td>
            <td className="px-4 py-4.5 text-sm bg-white/80 transition-all duration-300 group-hover:bg-white group-hover:shadow-md group-hover:scale-[1.01]">{group.focus}</td>
            <td className="px-4 py-4.5 text-sm bg-white/80 transition-all duration-300 group-hover:bg-white group-hover:shadow-md group-hover:scale-[1.01]">
              <span className={`inline-block px-3.5 py-1.5 rounded-xl text-xs font-semibold tracking-tight border ${getMasteryClass(group.mastery)}`}>
                {group.mastery}
              </span>
            </td>
            <td className="px-4 py-4.5 text-sm bg-white/80 transition-all duration-300 group-hover:bg-white group-hover:shadow-md group-hover:scale-[1.01]">{group.missing_skills}</td>
            <td className="px-4 py-4.5 text-sm bg-white/80 transition-all duration-300 max-w-75 group-hover:bg-white group-hover:shadow-md group-hover:scale-[1.01]">{group.rationale}</td>
            <td className="px-4 py-4.5 text-sm bg-white/80 transition-all duration-300 last:rounded-r-xl group-hover:bg-white group-hover:shadow-md group-hover:scale-[1.01]">
              <button 
                className="bg-linear-to-r from-purple-400 to-purple-600 text-white px-5 py-2.5 rounded-xl text-sm font-semibold transition-all duration-300 border border-purple-600/30 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-purple-500/40"
                onClick={() => onViewPack(group)}
              >
                View Pack
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
