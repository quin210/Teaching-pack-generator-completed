import type { Skill } from '../types';
import { useState } from 'react';

interface SkillEditorProps {
  skills: Skill[];
  onSkillRatingChange: (id: number, rating: number) => void;
  onRemoveSkill: (id: number) => void;
  newSkillName: string;
  onNewSkillNameChange: (name: string) => void;
  onAddSkill: () => void;
}

export default function SkillEditor({
  skills,
  onSkillRatingChange,
  onRemoveSkill,
  newSkillName,
  onNewSkillNameChange,
  onAddSkill,
}: SkillEditorProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="bg-stone-50/60 p-6 rounded-2xl mt-5 border border-black/5 backdrop-blur-lg">
      <button 
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-2 w-full text-left"
      >
        <strong className="text-base text-gray-800">
          Extracted skills (importance rated 1?10):
        </strong>
        <span className="text-gray-500 text-sm">{isExpanded ? '▼' : '▶'}</span>
      </button>
      {isExpanded && (
        <>
          <div className="mt-4">
            {skills.map((skill) => (
              <div key={skill.id} className="flex items-center gap-4 p-4 bg-white/80 rounded-2xl mb-3 border border-black/5 transition-all duration-300 hover:bg-white hover:translate-x-1 hover:border-yellow-400/20">
                <div className="flex-1 font-medium text-zinc-900 tracking-tight">{skill.name}</div>
                <div className="flex items-center gap-3">
                  <label className="text-sm text-zinc-500 whitespace-nowrap font-medium">Level:</label>
                  <input
                    type="number"
                    min="1"
                    max="10"
                    value={skill.rating}
                    onChange={(e) => onSkillRatingChange(skill.id, parseInt(e.target.value) || 1)}
                    className="w-17.5 px-3 py-2 border border-black/10 rounded-xl text-[15px] text-center font-semibold transition-all duration-200 focus:outline-none focus:border-yellow-400 focus:ring-4 focus:ring-yellow-400/10"
                  />
                  <span className="text-sm text-zinc-500">/10</span>
                </div>
                <button 
                  className="bg-red-200/50 text-red-900 px-3.5 py-2 rounded-xl text-xs font-medium cursor-pointer transition-all duration-200 border border-red-600/10 hover:bg-red-200/80 hover:scale-105"
                  onClick={() => onRemoveSkill(skill.id)}
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
          <div className="flex gap-3 mt-4">
            <input
              type="text"
              className="flex-1 px-4 py-3 border border-black/10 rounded-xl text-[15px] transition-all duration-200 bg-white/80 focus:outline-none focus:border-yellow-400 focus:bg-white focus:ring-4 focus:ring-yellow-400/10"
              placeholder="Enter custom skill name..."
              value={newSkillName}
              onChange={(e) => onNewSkillNameChange(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && onAddSkill()}
            />
            <button 
              className="bg-linear-to-r from-lime-400 to-lime-500 text-lime-900 px-6 py-3 rounded-xl text-sm font-semibold cursor-pointer transition-all duration-300 whitespace-nowrap border border-lime-600/20 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-lime-400/30 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
              onClick={onAddSkill}
              disabled={!newSkillName.trim()}
            >
              Add skill
            </button>
          </div>
        </>
      )}
    </div>
  );
}
