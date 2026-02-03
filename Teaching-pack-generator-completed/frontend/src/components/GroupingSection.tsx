import type { InstructionGroup, LessonData } from '../types';
import GroupsTable from './GroupsTable';

interface GroupingSectionProps {
  result: LessonData;
  onViewPack: (group: InstructionGroup) => void;
  selectedGroupId?: string;
}

export default function GroupingSection({ result, onViewPack }: GroupingSectionProps) {
  console.log('GroupingSection result.groups:', result.groups);
  console.log('Number of groups in GroupingSection:', result.groups.length);
  return (
    <div className="mt-8">
      <div className="flex items-center gap-3 text-2xl font-semibold mb-6 text-zinc-900 tracking-tight">
        <div className="w-1 h-6 bg-linear-to-b from-yellow-400 to-yellow-600 rounded-sm" />
        Grouping Result
      </div>
      <GroupsTable groups={result.groups} onViewPack={onViewPack} />
    </div>
  );
}
