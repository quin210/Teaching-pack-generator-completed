import { useState, useEffect } from 'react';
import { apiService } from '../services/api';
import type { TheoryQuestion, GroupTheoryQuestionSet } from '../types';
import Loading from './Loading';
import { generateFlashcardHtml } from '../utils/exportHtml';

interface TheoryQnAViewProps {
  lessonId: number;
  onClose: () => void;
  isStandalone?: boolean;
}

function FlashcardItem({ 
  question, 
  flipped, 
  onFlip 
}: { 
  question: TheoryQuestion; 
  flipped: boolean; 
  onFlip: () => void; 
}) {
  return (
    <div 
      className="h-[400px] w-full max-w-2xl mx-auto cursor-pointer group hover:-translate-y-1 transition-transform duration-300"
      onClick={onFlip}
      style={{ perspective: '1000px' }}
    >
      <div 
        className="relative w-full h-full transition-all duration-500 shadow-xl hover:shadow-2xl rounded-3xl"
        style={{ 
          transformStyle: 'preserve-3d',
          transform: flipped ? 'rotateY(180deg)' : 'rotateY(0deg)'
        }}
      >
        {/* Front Face */}
        <div 
          className="absolute inset-0 bg-white border-2 border-slate-100 rounded-3xl p-8 flex flex-col items-center justify-center text-center shadow-lg backface-hidden"
          style={{ backfaceVisibility: 'hidden' }}
        >
            <div className="flex-1 flex flex-col items-center justify-center w-full">
                <span className="text-xs font-bold text-blue-500 uppercase tracking-widest mb-6 bg-blue-50 px-3 py-1 rounded-full">Question</span>
                <h3 className="text-2xl font-medium text-slate-800 leading-snug px-4 overflow-y-auto max-h-[220px] custom-scrollbar">
                    {question.question}
                </h3>
            </div>

            <div className="mt-4 text-slate-400 text-sm flex items-center justify-center gap-2 w-full pt-4 border-t border-slate-50">
               <span>Tap to flip</span>
               <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12a9 9 0 0 1-9 9m9-9a9 9 0 0 0-9-9m9 9H3m9 9a9 9 0 0 1-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9"/></svg>
            </div>
        </div>

        {/* Back Face */}
        <div 
          className="absolute inset-0 bg-gradient-to-br from-blue-600 to-indigo-700 text-white rounded-3xl p-8 flex flex-col items-center justify-center text-center shadow-lg backface-hidden overflow-hidden"
          style={{ 
            backfaceVisibility: 'hidden', 
            transform: 'rotateY(180deg)' 
          }}
        >
            <div className="w-full h-full overflow-y-auto no-scrollbar flex flex-col items-center justify-center">
                <span className="text-xs font-bold text-blue-200 uppercase tracking-widest mb-6 bg-white/20 px-3 py-1 rounded-full shrink-0">Answer</span>
                <p className="text-xl leading-relaxed font-medium">
                    {question.answer}
                </p>
            </div>
        </div>
      </div>
    </div>
  );
}

export default function TheoryQnAView({ lessonId, onClose, isStandalone = false }: TheoryQnAViewProps) {
  const [groups, setGroups] = useState<GroupTheoryQuestionSet[]>([]);
  const [groupIndex, setGroupIndex] = useState(0);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(false);
  const [isFlipped, setIsFlipped] = useState(false);
  const [learnedIds, setLearnedIds] = useState<Set<number>>(new Set());

  // Derived state
  const currentGroup = groups[groupIndex];
  const questions = currentGroup?.questions || [];

  useEffect(() => {
    loadQuestions();
  }, [lessonId]);

  const loadQuestions = async () => {
    setLoading(true);
    try {
      const data: any = await apiService.getTheoryQuestions(lessonId);
      // Backend guarantees { groups: [...] }
      setGroups(data.groups || []);
      setGroupIndex(0);
      setCurrentIndex(0);
      setIsFlipped(false);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async () => {
    setLoading(true);
    try {
      const data: any = await apiService.generateTheoryQuestions(lessonId);
      setGroups(data.groups || []);
      setGroupIndex(0);
      setCurrentIndex(0);
      setIsFlipped(false);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleNext = () => {
    if (currentIndex < questions.length - 1) {
      setIsFlipped(false);
      setTimeout(() => setCurrentIndex(prev => prev + 1), 150);
    }
  };

  const handlePrev = () => {
    if (currentIndex > 0) {
      setIsFlipped(false);
      setTimeout(() => setCurrentIndex(prev => prev - 1), 150);
    }
  };

  const handleExport = () => {
    const html = generateFlashcardHtml(questions, `Flashcards - Lesson ${lessonId}`);
    const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `flashcards_lesson_${lessonId}.html`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleMarkLearned = (e: React.MouseEvent) => {
    e.stopPropagation();
    const currentQ = questions[currentIndex];
    
    // Create new set
    const newLearned = new Set(learnedIds);
    // Add current ID
    newLearned.add(currentQ.id);
    // Update state
    setLearnedIds(newLearned);
    
    // Auto advance if not last card
    if (currentIndex < questions.length - 1) {
        handleNext();
    }
  };

  const handleMarkNotLearned = (e: React.MouseEvent) => {
    e.stopPropagation();
    const currentQ = questions[currentIndex];
    
    // Create new set
    const newLearned = new Set(learnedIds);
    // Delete current ID
    newLearned.delete(currentQ.id);
    // Update state
    setLearnedIds(newLearned);

    // Auto advance if not last card
    if (currentIndex < questions.length - 1) {
        handleNext();
    }
  };

  const isLearned = questions.length > 0 ? learnedIds.has(questions[currentIndex].id) : false;

  const Container = isStandalone ? 'div' : 'div';
  const containerClasses = isStandalone
    ? "min-h-screen bg-stone-100 flex flex-col items-center justify-center p-4"
    : "fixed inset-0 bg-black/90 flex items-center justify-center z-50 p-4 animate-in fade-in duration-200";

  const contentClasses = isStandalone
    ? "max-w-4xl w-full"
    : "w-full max-w-5xl h-[90vh] flex flex-col relative";

  if (loading) {
      return isStandalone ? <Loading message="Loading questions..." /> : (
          <Container className={containerClasses}>
              <div className="bg-white p-8 rounded-xl"><Loading message="Loading..." /></div>
          </Container>
      );
  }

  // Check if we have any groups with questions
  const hasQuestions = groups.length > 0 && groups.some(g => g.questions.length > 0);

  if (!hasQuestions) {
    return (
      <Container className={containerClasses}>
        <div className="bg-white p-8 rounded-xl max-w-lg w-full mx-auto relative shadow-xl">
          {!isStandalone && <button onClick={onClose} className="absolute top-4 right-4 text-gray-400 hover:text-gray-700">✕</button>}
          <div className="text-center">
            <div className="bg-blue-100 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4 text-3xl">🗂️</div>
            <h2 className="text-2xl font-bold mb-2 text-gray-800">No Questions Yet</h2>
            <p className="mb-6 text-gray-600">This lesson doesn't have any theoretical questions generated yet.</p>
            <div className="flex gap-3 justify-center">
              {!isStandalone && <button onClick={onClose} className="px-5 py-2.5 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200 font-medium transition-colors">Close</button>}
              <button 
                onClick={handleGenerate} 
                className="px-5 py-2.5 bg-blue-600 text-white rounded-xl hover:bg-blue-700 font-medium shadow-lg shadow-blue-200 transition-all hover:scale-105 active:scale-95"
              >
                Generate Questions AI
              </button>
            </div>
          </div>
        </div>
      </Container>
    );
  }

  return (
    <Container className={containerClasses}>
      <div className={contentClasses}>
        {!isStandalone && (
          <button onClick={onClose} className="absolute top-4 right-4 z-10 p-2 bg-white/10 hover:bg-white/20 rounded-full text-white transition-colors">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
          </button>
        )}

        {/* Group Selector */}
        <div className={`flex flex-col items-center mb-6 px-4`}>
             <div className="flex flex-wrap gap-2 justify-center bg-white/10 p-1.5 rounded-xl backdrop-blur-sm border border-white/20">
                  {groups.map((group, idx) => (
                      <button
                          key={idx}
                          onClick={() => {
                              setGroupIndex(idx);
                              setCurrentIndex(0);
                              setIsFlipped(false);
                          }}
                          className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                              idx === groupIndex
                              ? 'bg-white text-blue-600 shadow-sm transform scale-105' 
                              : 'text-white/70 hover:text-white hover:bg-white/10'
                          }`}
                      >
                          {group.group_name}
                      </button>
                  ))}
            </div>
            {currentGroup?.group_description && (
                <div className="mt-3 text-sm text-white/80 font-medium bg-black/20 px-4 py-1 rounded-full backdrop-blur-md">
                    Target: {currentGroup.group_description}
                </div>
            )}
        </div>

        {/* Progress Header */}
        <div className={`flex justify-between items-center mb-8 px-4 ${isStandalone ? 'text-zinc-800' : 'text-white'}`}>
             <div className="flex flex-col">
                <h2 className="text-2xl font-bold">Flashcards</h2>
                <div className={`flex items-center gap-2 text-sm ${isStandalone ? 'text-zinc-500' : 'text-white/60'}`}>
                  <span>{currentIndex + 1} / {questions.length}</span>
                  <span className={`w-1 h-1 rounded-full ${isStandalone ? 'bg-zinc-300' : 'bg-white/40'}`}></span>
                  <span>{questions.length} terms</span>
                </div>
             </div>
             <div className="flex items-center gap-6">
                 <button 
                    onClick={handleExport}
                    className={`px-3 py-1.5 rounded-lg transition-colors flex items-center gap-2 text-sm font-medium border ${
                       isStandalone 
                         ? 'bg-blue-50 hover:bg-blue-100 text-blue-600 border-blue-200' 
                         : 'bg-white/10 hover:bg-white/20 text-white border-white/10'
                    }`}
                    title="Download offline flashcards"
                 >
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                    <span>Download</span>
                 </button>
                 <div className="flex flex-col items-end">
                     <div className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-green-400"></span>
                        <span className="text-sm font-medium text-green-400">{learnedIds.size} Known</span>
                     </div>
                     <div className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-orange-400"></span>
                        <span className="text-sm font-medium text-orange-400">{questions.length - learnedIds.size} Still learning</span>
                     </div>
                 </div>
                 {questions.length > 0 && (
                   <div className="w-12 h-12 rounded-full border-4 border-white/10 flex items-center justify-center text-xs font-bold relative">
                      {Math.round((learnedIds.size / questions.length) * 100)}%
                      <svg className="absolute inset-0 w-full h-full -rotate-90 pointer-events-none" viewBox="0 0 36 36">
                          <path
                              className="text-green-500 transition-all duration-1000 ease-out"
                              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                              fill="none"
                              stroke="currentColor"
                              strokeWidth="4"
                              strokeDasharray={`${(learnedIds.size / questions.length) * 100}, 100`}
                          />
                      </svg>
                   </div>
                 )}
             </div>
        </div>

        {/* Card Area */}
        <div className="flex-1 flex flex-col items-center justify-center w-full max-w-5xl mx-auto px-4">
            <FlashcardItem 
                question={questions[currentIndex]} 
                flipped={isFlipped} 
                onFlip={() => setIsFlipped(!isFlipped)} 
            />

            {/* Navigation & Actions */}
            <div className="mt-12 flex items-center justify-center gap-8 w-full max-w-3xl">
                <button 
                    onClick={handlePrev}
                    disabled={currentIndex === 0}
                    className="p-4 rounded-full bg-slate-800 text-white hover:bg-slate-700 disabled:opacity-30 disabled:cursor-not-allowed transition-all active:scale-95 shadow-lg border border-white/5"
                    title="Previous Card"
                >
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6"/></svg>
                </button>

                <div className="flex items-center gap-4 bg-slate-900/80 p-2.5 rounded-2xl backdrop-blur-md border border-white/10 shadow-2xl">
                    <button 
                        onClick={handleMarkNotLearned}
                        className={`px-8 py-3.5 rounded-xl font-bold transition-all flex flex-col items-center min-w-[140px] ${
                            !isLearned && learnedIds.has(questions[currentIndex].id) === false
                             ? 'bg-orange-500/20 text-orange-400 border border-orange-500/50 shadow-[0_0_15px_rgba(249,115,22,0.15)]' 
                             : 'bg-transparent text-slate-400 hover:bg-white/5 hover:text-orange-300'
                        }`}
                        title="Mark as reviewing"
                    >
                        <span className="text-sm">Still Learning</span>
                    </button>

                    <div className="h-10 w-[1px] bg-white/10 mx-2"></div>

                    <button 
                        onClick={handleMarkLearned}
                        className={`px-8 py-3.5 rounded-xl font-bold transition-all flex flex-col items-center min-w-[140px] ${
                            isLearned 
                             ? 'bg-green-500/20 text-green-400 border border-green-500/50 shadow-[0_0_15px_rgba(74,222,128,0.2)]' 
                             : 'bg-transparent text-slate-400 hover:bg-white/5 hover:text-green-300'
                        }`}
                        title="Mark as learned"
                    >
                         <span className="text-sm">Know it</span>
                    </button>
                </div>

                <button 
                    onClick={handleNext}
                    disabled={currentIndex === questions.length - 1}
                    className="p-4 rounded-full bg-slate-800 text-white hover:bg-slate-700 disabled:opacity-30 disabled:cursor-not-allowed transition-all active:scale-95 shadow-lg border border-white/5"
                    title="Next Card"
                >
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="m9 18 6-6-6-6"/></svg>
                </button>
            </div>
            
            <div className="mt-8 flex gap-2">
                {questions.map((_, idx) => ( 
                    <button 
                        key={idx}
                        onClick={() => {
                            setCurrentIndex(idx);
                            setIsFlipped(false);
                        }}
                        className={`w-2 h-2 rounded-full transition-all ${
                            idx === currentIndex 
                                ? 'bg-white scale-125' 
                                : learnedIds.has(questions[idx].id) 
                                    ? 'bg-green-500/50 hover:bg-green-400' 
                                    : 'bg-white/20 hover:bg-white/40'
                        }`}
                    />
                ))}
            </div>
        </div>
      </div>
    </Container>
  );
}
