import type { Skill, DiagnosticQuestion, TeachingPackStatus } from '../types';
import UploadArea from './UploadArea';
import SkillEditor from './SkillEditor';
import DiagnosticTest from './DiagnosticTest';

interface InputSectionProps {
  fileName: string;
  studentListFileName?: string;
  grade: string;
  studentCount: string;
  skills: Skill[];
  diagnosticQuestions: DiagnosticQuestion[];
  newSkillName: string;
  newQuestion: { question: string; answer: string; skillId: string };
  teachingPacks?: TeachingPackStatus[];
  selectedTeachingPackId: string;
  onFileChange: (file: File | null) => void;
  onStudentListFileChange?: (file: File | null) => void;
  onGradeChange: (grade: string) => void;
  onStudentCountChange: (count: string) => void;
  onGenerate: () => void;
  onLoadFromOutput?: () => void;
  onTeachingPackChange: (packId: string) => void;
  onSkillRatingChange: (id: number, rating: number) => void;
  onRemoveSkill: (id: number) => void;
  onNewSkillNameChange: (name: string) => void;
  onAddSkill: () => void;
  onQuestionChange: (field: string, value: string) => void;
  onAddQuestion: () => void;
  onRemoveQuestion: (id: number) => void;
}

export default function InputSection({
  fileName,
  studentListFileName,
  grade,
  studentCount,
  skills,
  diagnosticQuestions,
  newSkillName,
  newQuestion,
  teachingPacks = [],
  selectedTeachingPackId,
  onFileChange,
  // onStudentListFileChange,
  onGradeChange,
  onStudentCountChange,
  onGenerate,
  onLoadFromOutput,
  onTeachingPackChange,
  onSkillRatingChange,
  onRemoveSkill,
  onNewSkillNameChange,
  onAddSkill,
  onQuestionChange,
  onAddQuestion,
  onRemoveQuestion,
}: InputSectionProps) {
  return (
    <div className="bg-white/70 backdrop-blur-lg rounded-3xl p-8 border border-black/5 transition-all duration-300 animate-slideUp hover:border-yellow-400/20 hover:-translate-y-0.5">
      <div className="flex items-center gap-3 text-2xl font-semibold mb-6 text-zinc-900 tracking-tight">
        <div className="w-1 h-6 bg-linear-to-b from-yellow-400 to-yellow-600 rounded-sm" />
        Lesson & Class Input
      </div>
      <div className="grid gap-6">
        <div className="grid gap-2.5">
          <label className="font-medium text-zinc-600 text-sm tracking-tight">Upload lesson (PDF/Image)</label>
          <UploadArea 
            fileName={fileName} 
            studentListFileName={studentListFileName}
            onFileChange={onFileChange} 
            // onStudentListFileChange={onStudentListFileChange}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="grid gap-2.5">
            <label className="font-medium text-zinc-600 text-sm tracking-tight">Grade</label>
            <select 
              value={grade} 
              onChange={(e) => onGradeChange(e.target.value)}
              className="px-4 py-3 border border-black/10 rounded-xl text-[15px] transition-all duration-200 bg-white/80 focus:outline-none focus:border-yellow-400 focus:bg-white focus:ring-4 focus:ring-yellow-400/10"
            >
              <option value="">-- Select grade --</option>
              <option value="1">Grade 1</option>
              <option value="2">Grade 2</option>
              <option value="3">Grade 3</option>
              <option value="4">Grade 4</option>
              <option value="5">Grade 5</option>
              <option value="6">Grade 6</option>
              <option value="7">Grade 7</option>
              <option value="8">Grade 8</option>
              <option value="9">Grade 9</option>
              <option value="10">Grade 10</option>
              <option value="11">Grade 11</option>
              <option value="12">Grade 12</option>
            </select>
          </div>

          <div className="grid gap-2.5">
            <label className="font-medium text-zinc-600 text-sm tracking-tight">Student count</label>
            <input
              type="number"
              value={studentCount}
              onChange={(e) => onStudentCountChange(e.target.value)}
              placeholder="e.g., 30"
              min="1"
              className="px-4 py-3 border border-black/10 rounded-xl text-[15px] transition-all duration-200 bg-white/80 focus:outline-none focus:border-yellow-400 focus:bg-white focus:ring-4 focus:ring-yellow-400/10"
            />
          </div>
        </div>

        <SkillEditor
          skills={skills}
          onSkillRatingChange={onSkillRatingChange}
          onRemoveSkill={onRemoveSkill}
          newSkillName={newSkillName}
          onNewSkillNameChange={onNewSkillNameChange}
          onAddSkill={onAddSkill}
        />
        <DiagnosticTest
          questions={diagnosticQuestions}
          skills={skills}
          newQuestion={newQuestion}
          onQuestionChange={onQuestionChange}
          onAddQuestion={onAddQuestion}
          onRemoveQuestion={onRemoveQuestion}
        />

        <div className="flex gap-3">
          <button 
            className="flex-1 bg-linear-to-r from-yellow-400 to-yellow-600 text-yellow-900 px-8 py-3.5 rounded-2xl text-base font-semibold transition-all duration-300 border border-yellow-700/20 tracking-tight hover:-translate-y-0.5 hover:scale-[1.02] hover:shadow-xl hover:shadow-yellow-400/35 active:translate-y-0 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
            onClick={onGenerate}
            disabled={!fileName || !grade || !studentCount}
          >
            Generate Groups & Packs
          </button>
          {onLoadFromOutput && teachingPacks.length > 0 && (
            <>
              <select
                value={selectedTeachingPackId}
                onChange={(e) => onTeachingPackChange(e.target.value)}
                className="px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-yellow-500 focus:border-transparent"
              >
                <option value="">Select a teaching pack...</option>
                {teachingPacks.map((pack) => (
                  <option key={pack.id} value={pack.id}>
                    {pack.title || `Pack ${pack.id}`} ({new Date(pack.created_at).toLocaleDateString()})
                  </option>
                ))}
              </select>
              <button
                onClick={onLoadFromOutput}
                disabled={!selectedTeachingPackId}
                className="px-4 py-2.5 border border-yellow-300 text-yellow-700 hover:bg-yellow-50 disabled:opacity-50 disabled:cursor-not-allowed font-medium rounded-lg transition-colors"
              >
                📁 Load from Output File
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
