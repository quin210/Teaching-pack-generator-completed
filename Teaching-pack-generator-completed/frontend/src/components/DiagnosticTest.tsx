import type { DiagnosticQuestion, Skill } from '../types';
import { useState } from 'react';

interface DiagnosticTestProps {
  questions: DiagnosticQuestion[];
  skills: Skill[];
  newQuestion: { question: string; answer: string; skillId: string };
  onQuestionChange: (field: string, value: string) => void;
  onAddQuestion: () => void;
  onRemoveQuestion: (id: number) => void;
}

export default function DiagnosticTest({
  questions,
  skills,
  newQuestion,
  onQuestionChange,
  onAddQuestion,
  onRemoveQuestion,
}: DiagnosticTestProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const getSkillName = (skillId: string | number) => {
    const skill = skills.find((s) => s.id === Number(skillId) || s.id.toString() === skillId.toString());
    return skill ? skill.name : String(skillId);
  };

  if (skills.length === 0) return null;

  return (
    <div className="bg-purple-100/30 p-6 rounded-2xl mt-5 border border-purple-300/15 backdrop-blur-lg">
      <button 
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-2 w-full text-left"
      >
        <strong className="text-base text-gray-800">
          Mini-Diagnostic Test (Fill-in answers):
        </strong>
        <span className="text-gray-500 text-sm">{isExpanded ? '▼' : '▶'}</span>
      </button>
      <p className="text-sm text-zinc-500 mt-1 mb-4">
        Create initial assessment questions for students, linked to each skill
      </p>
      {isExpanded && (
        <>
          {questions.length > 0 && (
            <div className="mb-5">
              {questions.map((q, idx) => (
                <div key={q.id} className="bg-white/90 p-4.5 rounded-2xl mb-4 border border-black/5 transition-all duration-300 animate-slideIn hover:bg-white hover:border-purple-300/20 hover:translate-x-1">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2.5">
                      <span className="font-semibold text-zinc-900 text-[15px] tracking-tight">Question {idx + 1}</span>
                      <span className="inline-block bg-emerald-200/40 text-emerald-900 px-3 py-1.5 rounded-xl text-xs border border-emerald-500/20 font-medium">
                        {getSkillName(q.skillId)}
                      </span>
                    </div>
                    <button 
                      className="bg-red-200/50 text-red-900 px-3.5 py-2 rounded-xl text-xs font-medium border border-red-600/10 hover:bg-red-200/80 hover:scale-105 transition-all duration-200"
                      onClick={() => onRemoveQuestion(q.id)}
                    >
                      Remove
                    </button>
                  </div>
                  <div className="text-zinc-600 text-sm mb-3 leading-relaxed">{q.question}</div>
                  
                  {q.options && q.options.length > 0 && (
                    <div className="mb-3 space-y-1.5">
                      {q.options.map((option, optIdx) => (
                        <div key={optIdx} className={`px-3 py-2 rounded-lg text-sm ${option === q.answer ? 'bg-green-100/60 text-green-900 border border-green-300/30 font-medium' : 'bg-gray-50/60 text-gray-700'}`}>
                          {String.fromCharCode(65 + optIdx)}. {option}
                          {option === q.answer && <span className="ml-2 text-xs">✓</span>}
                        </div>
                      ))}
                    </div>
                  )}
                  
                  <div>
                    <strong className="text-sm text-zinc-500">Answer: </strong>
                    <span className="bg-yellow-100/40 px-3.5 py-2.5 rounded-xl text-yellow-900 inline-block font-medium border border-yellow-400/20">
                      {q.answer}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="bg-white/70 p-6 rounded-2xl border-2 border-dashed border-purple-300/20 mt-4 backdrop-blur-lg">
            <strong className="text-sm text-gray-800 block mb-4">
              Add new question
            </strong>

            <div className="grid gap-2.5 mb-4">
              <label className="font-medium text-zinc-600 text-sm tracking-tight">Question:</label>
              <textarea
                value={newQuestion.question}
                onChange={(e) => onQuestionChange('question', e.target.value)}
                placeholder="Example: Solve x + 5 = 12. The value of x = ?"
                className="px-4 py-3 border border-black/10 rounded-xl text-sm resize-y min-h-22.5 transition-all duration-200 bg-white/80 focus:outline-none focus:border-purple-500 focus:bg-white focus:ring-4 focus:ring-purple-500/10"
              />
            </div>

            <div className="grid grid-cols-2 gap-4 mb-4">
              <div className="grid gap-2.5">
                <label className="font-medium text-zinc-600 text-sm tracking-tight">Correct answer:</label>
                <input
                  type="text"
                  value={newQuestion.answer}
                  onChange={(e) => onQuestionChange('answer', e.target.value)}
                  placeholder="Example: 7"
                  className="px-4 py-3 border border-black/10 rounded-xl text-[15px] transition-all duration-200 bg-white/80 focus:outline-none focus:border-purple-500 focus:bg-white focus:ring-4 focus:ring-purple-500/10"
                />
              </div>
              <div className="grid gap-2.5">
                <label className="font-medium text-zinc-600 text-sm tracking-tight">Related skill:</label>
                <select
                  value={newQuestion.skillId}
                  onChange={(e) => onQuestionChange('skillId', e.target.value)}
                  className="px-4 py-3 border border-black/10 rounded-xl text-[15px] transition-all duration-200 bg-white/80 focus:outline-none focus:border-purple-500 focus:bg-white focus:ring-4 focus:ring-purple-500/10"
                >
                  <option value="">-- Select skill --</option>
                  {skills.map((skill) => (
                    <option key={skill.id} value={skill.id}>
                      {skill.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <button
              className="w-full bg-linear-to-r from-lime-400 to-lime-500 text-lime-900 px-6 py-3 rounded-xl text-sm font-semibold transition-all duration-300 border border-lime-600/20 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-lime-400/30 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
              onClick={onAddQuestion}
              disabled={!newQuestion.question.trim() || !newQuestion.answer.trim() || !newQuestion.skillId}
            >
              Add question
            </button>
          </div>
        </>
      )}
    </div>
  );
}
