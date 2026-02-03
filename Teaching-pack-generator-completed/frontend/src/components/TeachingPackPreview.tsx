import { useState, useEffect, Fragment } from 'react';
import type { InstructionGroup, TabType, QuizQuestion, PracticeExercise, Slide } from '../types';
import { apiService } from '../services/api';

import FlashcardView from './FlashcardView';

function mapMasteryToFlashcardGroupName(mastery?: string) {
  const m = (mastery || '').toLowerCase();
  
  // Mapping for Low/Beginner
  if (['low', 'foundation', 'beginner'].some(key => m.includes(key))) return 'Beginner';
  
  // Mapping for Medium/Intermediate
  if (['medium', 'intermediate'].some(key => m.includes(key))) return 'Intermediate';
  
  // Mapping for High/Advanced
  if (['high', 'advanced'].some(key => m.includes(key))) return 'Advanced';
  
  // Default fallback
  return 'General';
}

const normalizeGroupKey = (value?: string | number | null) =>
  (value == null ? '' : String(value)).trim().toLowerCase().replace(/[_-]+/g, ' ');

const buildGroupKeySet = (group: InstructionGroup) => {
  const keys: string[] = [];
  if (group.id) keys.push(group.id);
  if (group.groupName) keys.push(group.groupName);
  if (group.focus) keys.push(group.focus);
  if (group.id?.startsWith('pack-')) {
    const parts = group.id.split('-');
    if (parts.length >= 3) {
      keys.push(parts.slice(2).join('-'));
    }
  }
  return new Set(keys.map(normalizeGroupKey).filter(Boolean));
};

const pickPackForGroup = (result: any, group: InstructionGroup) => {
  const packs = Array.isArray(result?.teaching_packs) ? result.teaching_packs : [];
  if (!packs.length) return null;
  const wanted = buildGroupKeySet(group);
  if (!wanted.size) return null;
  return (
    packs.find((pack: any) => {
      const packGroup = pack?.group || {};
      const candidates = [
        pack?.group_id,
        pack?.focus,
        packGroup?.group_id,
        packGroup?.group_name,
        packGroup?.focus,
        packGroup?.focus_area,
      ].filter(Boolean);
      return candidates.some((candidate) => wanted.has(normalizeGroupKey(candidate)));
    }) || null
  );
};

const resolveSlidesUrlFromGroup = (group: InstructionGroup): string | null => {
  const packSlides = group.pack?.slides_url || (group.pack?.slides as any)?.generated_url;
  return group.slides_url || packSlides || null;
};

const resolveVideoUrlFromGroup = (group: InstructionGroup): string | null => {
  const packVideo =
    group.pack?.video_url || (group.pack?.video as any)?.generated_url || (group.pack?.video as any)?.url;
  return group.video_url || packVideo || null;
};

const resolveAssetUrlFromResult = (
  result: any,
  group: InstructionGroup,
  type: 'slides' | 'video'
): string | null => {
  if (!result) return null;
  const rootUrl = type === 'slides' ? result?.slides_url : result?.video_url;
  if (rootUrl) return rootUrl;
  const pack = pickPackForGroup(result, group);
  if (!pack) return null;
  if (type === 'slides') {
    return pack.slides_url || (pack.slides as any)?.generated_url || null;
  }
  return pack.video_url || (pack.video as any)?.generated_url || (pack.video as any)?.url || null;
};

const EVALUATION_SECTIONS = [
  {
    id: 'T',
    title: 'Teacher Evaluation Metrics',
    items: [
      { code: 'USE', label: 'Usefulness', question: 'Dung duoc ngay khong?', reverse: false },
      { code: 'EDIT', label: 'Edit ratio', question: 'Phai sua bao nhieu %?', reverse: false },
      { code: 'TIME', label: 'Time saved', question: 'Giam bao nhieu phut cho soan noi dung?', reverse: false },
      { code: 'PED', label: 'Pedagogical fit', question: 'Phu hop lua tuoi, pace, vi du de hieu?', reverse: false },
      { code: 'TRUST', label: 'Trust', question: 'Co dam dung quiz do khong?', reverse: false },
    ],
  },
] as const;

interface TeachingPackPreviewProps {
  group: InstructionGroup;
  activeTab: TabType;
  onTabChange: (tab: TabType) => void;
  jobId?: string; // Add jobId prop to enable commit
  onRefresh?: () => void; // Add onRefresh callback
  lessonId?: number; // Add lessonId for flashcard context
  packId?: number; // Needed to generate group specific assets
}

export default function TeachingPackPreview({ group, activeTab, onTabChange, jobId, onRefresh, lessonId }: TeachingPackPreviewProps) {
  const [generating, setGenerating] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [downloadingQuiz, setDownloadingQuiz] = useState(false);
  
  // Local state for editing draft content
  const [localSlides, setLocalSlides] = useState<Slide[]>(group.pack.slides || []);
  const [localVideo, setLocalVideo] = useState(group.pack.video || { title: '', script: '', visual_description: '' });
  const [slidesUrl, setSlidesUrl] = useState<string | null>(() => resolveSlidesUrlFromGroup(group));
  const [videoUrl, setVideoUrl] = useState<string | null>(() => resolveVideoUrlFromGroup(group));
  const [flashcardUrl, setFlashcardUrl] = useState<string | null>(group.flashcard_url || null);
  const [flashcardData, setFlashcardData] = useState<any>(group.pack.flashcards || null);
  const [evaluationRatings, setEvaluationRatings] = useState<Record<string, number>>({});
  const [evaluationNotes, setEvaluationNotes] = useState('');
  const [evaluationSaving, setEvaluationSaving] = useState(false);
  const [evaluationMessage, setEvaluationMessage] = useState<string | null>(null);
  const [evaluationUrl, setEvaluationUrl] = useState<string | null>(null);
  
  // Local pack ID state (starts as group.pack.id, but updateable after commit)
  const [currentPackId, setCurrentPackId] = useState<string | number | undefined>(group.pack.id);

  // Sync state with props when group changes
  useEffect(() => {
    console.log('TeachingPackPreview useEffect triggered for group:', group.id, 'group.video_url:', group.video_url);
    
    // Handle slides data structure (array or object wrapper)
    const slidesData = group.pack.slides as any;
    let slidesArray: Slide[] = [];
    
    if (Array.isArray(slidesData)) {
      slidesArray = slidesData;
    } else if (slidesData && Array.isArray(slidesData.slides)) {
      slidesArray = slidesData.slides;
    }
    
    setLocalSlides(slidesArray);
    setLocalVideo(group.pack.video || { title: '', script: '', visual_description: '' });
    setCurrentPackId(group.pack.id);
    setFlashcardData(group.pack.flashcards || null);
    
    // Reset URLs when group changes
    const resolvedSlidesUrl = resolveSlidesUrlFromGroup(group);
    const resolvedVideoUrl = resolveVideoUrlFromGroup(group);
    console.log('Setting slidesUrl to:', resolvedSlidesUrl, 'videoUrl to:', resolvedVideoUrl);
    setSlidesUrl(resolvedSlidesUrl);
    setVideoUrl(resolvedVideoUrl);
    setFlashcardUrl(group.flashcard_url || null);
    setEvaluationRatings({});
    setEvaluationNotes('');
    setEvaluationMessage(null);
    setEvaluationUrl(null);
  }, [group]);

  // Ensure pack is committed before action
  const ensurePackCommitted = async (): Promise<string | number | null> => {
     if (currentPackId) return currentPackId;
     
     if (!jobId) {
         setMessage("Cannot commit: Missing Job ID context.");
         return null;
     }

     setMessage("Committing Teaching Pack to database...");
     try {
         const res = await apiService.commitTeachingPack(jobId, group.id); 
         if (res && res.teaching_pack_id) {
             setCurrentPackId(res.teaching_pack_id);
             // Update prop reference too if possible, but local state handles it for now
             return res.teaching_pack_id;
         }
     } catch(e) {
         setMessage("Commit failed: " + (e instanceof Error ? e.message : String(e)));
     }
     return null;
  };

  // Toggle to show/hide generation buttons
  const SHOW_GENERATION_BUTTONS = true; //flag

  const handleGenerateAssets = async (type: 'slides' | 'video') => {
    // Use current pack ID directly since packs are already committed
    const packId = currentPackId || group.pack.id;
    if (!packId) {
        alert("Teaching Pack ID missing. Cannot generate.");
        return;
    }
    
    try {
        setGenerating(true);
        setMessage(`Sending request for ${type}...`);
        
        // Prepare content
        const slidesContent = {
            slides: localSlides
        };
        
        const res = await apiService.generatePackAssets(
            packId,
            slidesContent,
            localVideo,
            type === 'video', // generateVideo
            type === 'slides', // generateSlides
            group.id // Use actual group.id instead of debug
        );
        console.log('Calling generatePackAssets with group.id:', group.id, 'group object:', group);
        
        if (!group.id) {
            console.error('Group ID is missing!', group);
            setMessage('Error: Group ID is missing. Cannot generate assets.');
            return;
        }
        
        console.log(`Generating ${type} for group ${group.id}, packId ${packId}`);
        setMessage(`Success! Job started: ${res.job_id}. Waiting for completion...`);
        
        // Poll job status until completion
        const pollInterval = setInterval(async () => {
            try {
                const jobStatus = await apiService.getJobStatus(res.job_id);
                
                if (jobStatus.status === 'completed') {
                    clearInterval(pollInterval);
                    
                    // Extract URLs from job result
                    const result = jobStatus.result;
                    const resolvedUrl = resolveAssetUrlFromResult(result, group, type);
                    if (type === 'slides' && resolvedUrl) {
                        setSlidesUrl(resolvedUrl);
                        setMessage('Slides generated! Download button is now available.');
                        onTabChange('slides_preview'); // Switch to slides tab to show immediately
                        // Refresh parent to sync with database after a longer delay
                        setTimeout(() => {
                            if (onRefresh) onRefresh();
                        }, 3000);
                    } else if (type === 'video' && resolvedUrl) {
                        console.log('Setting videoUrl to:', resolvedUrl);
                        setVideoUrl(resolvedUrl);
                        setMessage('Video generated! Download button is now available.');
                        console.log('Switching to video tab');
                        onTabChange('video'); // Switch to video tab to show immediately
                        // Refresh parent to sync with database after a longer delay
                        setTimeout(() => {
                            if (onRefresh) onRefresh();
                        }, 3000);
                    } else {
                        setMessage(`${type === 'slides' ? 'Slides' : 'Video'} generation completed!`);
                        // Refresh parent for other cases
                        if (onRefresh) onRefresh();
                    }
                } else if (jobStatus.status === 'failed') {
                    clearInterval(pollInterval);
                    setMessage(`Generation failed: ${jobStatus.error || 'Unknown error'}`);
                }
                // Continue polling if status is 'pending' or 'processing'
            } catch (err) {
                console.error('Error polling job status:', err);
                // Don't clear interval on error, keep trying
            }
        }, 2000); // Poll every 2 seconds
        
        // Clear interval after 5 minutes to prevent infinite polling
        setTimeout(() => {
            clearInterval(pollInterval);
            if (onRefresh) onRefresh(); // Final refresh regardless
        }, 300000);
    } catch (e) {
        console.error(e);
        setMessage("Error starting generation: " + (e instanceof Error ? e.message : String(e)));
    } finally {
        setGenerating(false);
    }
  };

  const handleDownloadQuiz = async () => {
    // Cast to number because packId in downloadQuiz must be number
    const packId = Number(currentPackId || group.pack.id);
    if (!packId || isNaN(packId)) {
      alert("Teaching Pack ID missing or invalid. Cannot download quiz.");
      return;
    }

    try {
      setDownloadingQuiz(true);
      await apiService.downloadQuiz(packId, group.id);
    } catch (e) {
      console.error(e);
      alert("Error downloading quiz: " + (e instanceof Error ? e.message : String(e)));
    } finally {
      setDownloadingQuiz(false);
    }
  };

  const handleDraftContent = async (type: 'slides' | 'video') => {
      setGenerating(true);
      const packId = await ensurePackCommitted();
      
      if (!packId) {
          setGenerating(false);
          return; 
      }
      
      apiService.draftPackContent(packId, type)
        .then((data) => {
            if (type === 'slides') setLocalSlides(data.slides || []);
            if (type === 'video') setLocalVideo(data || {});
            setMessage("Draft created successfully!");
        })
        .catch((err) => setMessage("Error creating draft: " + err.message))
        .finally(() => setGenerating(false));
  };

  const evaluationItems = EVALUATION_SECTIONS.flatMap((section) =>
    section.items.map((item) => ({
      ...item,
      section: section.title,
    }))
  );
  const ratedCount = evaluationItems.filter((item) => evaluationRatings[item.code]).length;
  const ratingSum = evaluationItems.reduce(
    (sum, item) => sum + (evaluationRatings[item.code] || 0),
    0
  );
  const averageRating = ratedCount ? (ratingSum / ratedCount).toFixed(2) : null;
  const allRated = ratedCount === evaluationItems.length;

  const handleSubmitEvaluation = async () => {
    const packId = await ensurePackCommitted();
    if (!packId) return;

    const items = evaluationItems.map((item) => ({
      code: item.code,
      label: item.label,
      question: item.question,
      rating: evaluationRatings[item.code] || 0,
      section: item.section,
      reverse: Boolean(item.reverse),
    }));

    const missing = items.filter((item) => !item.rating);
    if (missing.length > 0) {
      setEvaluationMessage('Please rate all items before submitting.');
      return;
    }

    try {
      setEvaluationSaving(true);
      setEvaluationMessage('Saving evaluation...');
      const result = await apiService.submitGroupEvaluation(packId, group.id, {
        items,
        notes: evaluationNotes,
      });
      setEvaluationUrl(result?.evaluation_url || null);
      setEvaluationMessage(
        `Saved. Average rating: ${result?.average_rating ?? averageRating ?? 'N/A'}`
      );
    } catch (e) {
      setEvaluationMessage(
        `Save failed: ${e instanceof Error ? e.message : String(e)}`
      );
    } finally {
      setEvaluationSaving(false);
    }
  };

  const renderTabContent = () => {
    switch (activeTab) {
      case 'slides_preview':
        return (
          <div>
            {slidesUrl ? (
              <div className="bg-linear-to-br from-purple-50 to-pink-50 p-8 rounded-3xl border border-purple-200/50 shadow-lg shadow-purple-500/10 transition-all duration-300 hover:shadow-xl hover:shadow-purple-500/20">
                <div className="text-center mb-8">
                  <h4 className="mb-2 text-xl font-semibold tracking-tight bg-linear-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">
                    Slides generated
                  </h4>
                  <p className="text-zinc-600 text-sm">Download to use in class</p>
                </div>

                <div className="flex flex-col items-center gap-6">
                  <div className="relative">
                    <div className="w-24 h-24 rounded-2xl bg-white flex items-center justify-center shadow-xl border border-purple-100">
                      <svg className="w-12 h-12 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                    </div>
                    <div className="absolute -top-1 -right-1 w-6 h-6 bg-green-500 rounded-full flex items-center justify-center border-2 border-white">
                      <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                    </div>
                  </div>
                  
                  <a
                    href={slidesUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-3 px-8 py-4 bg-linear-to-r from-purple-600 to-pink-600 text-white text-base font-semibold rounded-xl hover:from-purple-700 hover:to-pink-700 transition-all duration-200 shadow-lg shadow-purple-500/25 hover:shadow-xl hover:shadow-purple-500/40 transform hover:-translate-y-0.5"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                    Download Slides
                  </a>
                  
                  <p className="text-sm text-zinc-500">File PowerPoint (.pptx)</p>
                </div>
              </div>
            ) : (
              <div className="space-y-6">
                <div className="bg-white p-6 rounded-2xl border border-stone-200 shadow-sm">
                  <div className="flex items-center justify-between mb-4">
                    <h4 className="text-lg font-semibold text-stone-800">Slide Content (Draft)</h4>
                    <span className="text-xs font-medium px-2 py-1 bg-yellow-100 text-yellow-800 rounded-full">Not Generated Yet</span>
                  </div>
                  
                  {/* Generation Controls */}
                  {SHOW_GENERATION_BUTTONS && (
                  <div className="mb-6 p-4 bg-blue-50 rounded-xl border border-blue-100 flex flex-col gap-3">
                    {localSlides.length > 0 ? (
                        <>
                        <p className="text-sm text-blue-800 mb-2">
                            Draft looks good? Confirm to generate the actual PowerPoint file.
                        </p>
                        <button
                            onClick={() => handleGenerateAssets('slides')}
                            disabled={generating}
                            className={`px-4 py-2 rounded-lg text-white font-medium text-sm transition-colors ${
                                generating 
                                ? 'bg-stone-400 cursor-not-allowed' 
                                : 'bg-blue-600 hover:bg-blue-700 shadow-sm'
                            }`}
                        >
                            {generating ? 'Starting Generation...' : 'Generate Slides (PowerPoint)'}
                        </button>
                        </>
                    ) : (
                        <>
                        <p className="text-sm text-blue-800 mb-2">
                            No content yet. Create draft content with AI first.
                        </p>
                        <button
                            onClick={() => handleDraftContent('slides')}
                            disabled={generating}
                            className={`px-4 py-2 rounded-lg text-white font-medium text-sm transition-colors ${
                                generating 
                                ? 'bg-stone-400 cursor-not-allowed' 
                                : 'bg-indigo-600 hover:bg-indigo-700 shadow-sm'
                            }`}
                        >
                            {generating ? 'Creating Draft...' : 'Create Content Draft (AI)'}
                        </button>
                        </>
                    )}
                    {slidesUrl && (
                        <div className="mt-2 pt-2 border-t border-blue-100 flex justify-center">
                            <a 
                                href={slidesUrl} 
                                download 
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm font-medium transition-colors shadow-sm"
                            >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                                </svg>
                                Download Slides (PPTX)
                            </a>
                        </div>
                    )}
                    {message && (
                        <p className={`text-xs ${message.includes('Error') ? 'text-red-600' : 'text-green-600'}`}>
                            {message}
                        </p>
                    )}
                  </div>
                  )}

                  <div className="space-y-4">

                    {localSlides.map((slide, idx) => (
                      <div key={idx} className="p-4 bg-stone-50 rounded-xl border border-stone-200">
                        <div className="flex items-center gap-3 mb-2">
                          <span className="w-6 h-6 flex items-center justify-center bg-stone-200 text-xs font-bold rounded-full text-stone-600">
                            {idx + 1}
                          </span>
                          <input 
                             type="text"
                             value={slide.title}
                             onChange={(e) => {
                               const newSlides = [...localSlides];
                               newSlides[idx] = { ...newSlides[idx], title: e.target.value };
                               setLocalSlides(newSlides);
                             }}
                             className="font-medium text-stone-900 bg-transparent border-b border-transparent hover:border-stone-300 focus:border-blue-500 focus:outline-none flex-grow"
                           />
                        </div>
                        <textarea
                           value={slide.content}
                           onChange={(e) => {
                               const newSlides = [...localSlides];
                               newSlides[idx] = { ...newSlides[idx], content: e.target.value };
                               setLocalSlides(newSlides);
                           }}
                           className="text-sm text-stone-600 w-full bg-transparent border border-transparent hover:border-stone-300 focus:border-blue-500 focus:outline-none rounded-md p-2 ml-7 min-h-[100px]"
                        />
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        );

      case 'video':
        return (
          <div>
            {videoUrl ? (
              <div className="bg-linear-to-br from-blue-50 to-indigo-50 p-8 rounded-3xl border border-blue-200/50 shadow-lg shadow-blue-500/10 transition-all duration-300 hover:shadow-xl hover:shadow-blue-500/20">
                <div className="text-center mb-6">
                  <h4 className="mb-2 text-xl font-semibold tracking-tight bg-linear-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
                    🎬 Educational Video
                  </h4>
                  <p className="text-zinc-600 text-sm">Watch the generated educational content</p>
                </div>

                <div className="relative max-w-4xl mx-auto">
                  <div className="absolute -inset-1 bg-linear-to-r from-blue-600 to-indigo-600 rounded-2xl blur opacity-20"></div>
                  <div className="relative bg-white rounded-2xl p-2 shadow-2xl">
                    <video
                      controls
                      className="w-full rounded-xl shadow-lg"
                      poster={group.pack.video_thumbnail}
                      preload="metadata"
                    >
                      <source src={videoUrl} type="video/mp4" />
                      Your browser does not support the video tag.
                    </video>
                  </div>
                </div>

                <div className="mt-6 flex justify-center gap-3">
                  <a
                    href={videoUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 px-6 py-3 bg-linear-to-r from-blue-600 to-indigo-600 text-white text-sm font-medium rounded-xl hover:from-blue-700 hover:to-indigo-700 transition-all duration-200 shadow-lg shadow-blue-500/25 hover:shadow-xl hover:shadow-blue-500/40 transform hover:-translate-y-0.5"
                  >
                    <span>📥</span>
                    Download Video
                  </a>
                  {group.pack.video_thumbnail && (
                    <div className="inline-flex items-center gap-2 px-4 py-3 bg-white/80 text-zinc-700 text-sm font-medium rounded-xl border border-zinc-200 hover:bg-white hover:border-zinc-300 transition-all duration-200">
                      <span>🖼️</span>
                      Thumbnail Available
                    </div>
                  )}
                </div>
              </div>
            ) : (
                <div className="bg-white p-6 rounded-2xl border border-stone-200 shadow-sm">
                  <div className="flex items-center justify-between mb-4">
                    <h4 className="text-lg font-semibold text-stone-800">Video Script & Visuals (Draft)</h4>
                    <span className="text-xs font-medium px-2 py-1 bg-yellow-100 text-yellow-800 rounded-full">Not Generated Yet</span>
                  </div>

                  {/* Generation Controls */}
                  <div className="mb-6 p-4 bg-blue-50 rounded-xl border border-blue-100 flex flex-col gap-3">
                     {localVideo.script && localVideo.script !== "Video script not generated yet." ? (
                        <>
                        <p className="text-sm text-blue-800 mb-2">
                            Script looks good? Confirm to generate the educational video.
                        </p>
                        <button
                            onClick={() => handleGenerateAssets('video')}
                            disabled={generating}
                            className={`px-4 py-2 rounded-lg text-white font-medium text-sm transition-colors ${
                                generating 
                                ? 'bg-stone-400 cursor-not-allowed' 
                                : 'bg-blue-600 hover:bg-blue-700 shadow-sm'
                            }`}
                        >
                            {generating ? 'Starting Generation...' : 'Generate Video (MP4)'}
                        </button>
                        </>
                     ) : (
                        <>
                        <p className="text-sm text-blue-800 mb-2">
                            No script yet. Draft the script with AI first.
                        </p>
                        <button
                            onClick={() => handleDraftContent('video')}
                            disabled={generating}
                            className={`px-4 py-2 rounded-lg text-white font-medium text-sm transition-colors ${
                                generating 
                                ? 'bg-stone-400 cursor-not-allowed' 
                                : 'bg-purple-600 hover:bg-purple-700 shadow-sm'
                            }`}
                        >
                            {generating ? 'Creating Draft...' : 'Create Video Script (AI)'}
                        </button>
                        </>
                     )}
                    {videoUrl && (
                        <div className="mt-2 pt-2 border-t border-blue-100 flex justify-center">
                            <a 
                                href={videoUrl} 
                                download 
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium transition-colors shadow-sm"
                            >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                                </svg>
                                Download Video (MP4)
                            </a>
                        </div>
                    )}
                    {message && (
                        <p className={`text-xs ${message.includes('Error') ? 'text-red-600' : 'text-green-600'}`}>
                            {message}
                        </p>
                    )}
                  </div>

                  {localVideo ? (
                    <div className="space-y-6">
                       <div>
                         <h5 className="text-sm font-semibold text-stone-700 mb-1">Title</h5>
                         <input
                            type="text" 
                            value={localVideo.title || ''}
                            onChange={(e) => setLocalVideo({...localVideo, title: e.target.value})}
                            className="w-full p-2 border border-stone-300 rounded-md focus:border-blue-500 focus:outline-none"
                            placeholder="Video Title"
                         />
                       </div>
                       <div>
                         <h5 className="text-sm font-semibold text-stone-700 mb-1">Script</h5>
                         <textarea
                           value={localVideo.script || ''}
                           onChange={(e) => setLocalVideo({...localVideo, script: e.target.value})}
                           className="w-full p-4 bg-stone-50 rounded-xl border border-stone-200 text-sm text-stone-700 min-h-[150px] focus:border-blue-500 focus:outline-none"
                           placeholder="Video script..."
                         />
                       </div>
                       <div>
                         <h5 className="text-sm font-semibold text-stone-700 mb-1">Visual Description</h5>
                         <textarea
                           value={localVideo.visual_description || ''}
                           onChange={(e) => setLocalVideo({...localVideo, visual_description: e.target.value})}
                           className="w-full p-4 bg-stone-50 rounded-xl border border-stone-200 text-sm text-stone-700 min-h-[100px] focus:border-blue-500 focus:outline-none"
                            placeholder="Visual description..."
                         />
                       </div>
                    </div>
                  ) : (
                    <div className="text-center py-8">
                       <p className="text-stone-500">No video draft available.</p>
                    </div>
                  )}
                </div>
            )}
          </div>
        );

      case 'quiz':
        return (
          <div>
            {(() => {
              const quiz = group.pack.quiz;
              
              // Handle quiz data - can be object with questions array or direct array
              let questions: any[] = [];
              if (quiz && typeof quiz === 'object') {
                if ('questions' in quiz && Array.isArray(quiz.questions)) {
                  questions = quiz.questions;
                } else if (Array.isArray(quiz)) {
                  questions = quiz;
                }
              }
              
              const quizData = (quiz && typeof quiz === 'object' && !Array.isArray(quiz)) ? quiz as { total_questions?: number; estimated_time?: string; questions?: any[] } : null;
              
              return questions && questions.length > 0 ? (
                <div className="space-y-6">
                  <div className="text-center mb-8">
                    <h4 className="mb-2 text-xl font-semibold tracking-tight bg-linear-to-r from-emerald-600 to-teal-600 bg-clip-text text-transparent">
                      🧠 Knowledge Assessment
                    </h4>
                    <p className="text-zinc-600 text-sm">Test your understanding with these questions</p>
                    {quizData?.total_questions && (
                      <p className="text-zinc-500 text-xs mt-2">
                        Total: {quizData.total_questions} questions • Estimated time: {quizData.estimated_time || 'N/A'} minutes
                      </p>
                    )}
                  </div>

                  {/* Questions Section */}
                  <div className="space-y-4">
                    <h5 className="text-lg font-semibold text-zinc-900 mb-4">📝 Questions</h5>
                    {questions.map((q: QuizQuestion, idx: number) => (
                    <div key={idx} className="bg-linear-to-br from-emerald-50 to-teal-50 p-6 rounded-2xl border border-emerald-200/50 shadow-lg shadow-emerald-500/10 transition-all duration-300 hover:shadow-xl hover:shadow-emerald-500/20">
                      <div className="flex items-center justify-between mb-4">
                        <div>
                          <h4 className="text-zinc-900 text-lg font-medium tracking-tight mb-2">
                            {q.question_text || `Question ${idx + 1}`}
                          </h4>
                          <div className="flex items-center gap-3 text-sm text-zinc-600">
                            <span className="flex items-center gap-1">
                              <span className="font-medium">ID:</span>
                              <span>{q.question_id}</span>
                            </span>
                            <span className="flex items-center gap-1">
                              <span className="font-medium">Skill:</span>
                              <span>{q.skill_id}</span>
                            </span>
                          </div>
                        </div>
                        <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                          (q.difficulty || '').toLowerCase() === 'easy' ? 'bg-green-100 text-green-800' :
                          (q.difficulty || '').toLowerCase() === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                          (q.difficulty || '').toLowerCase() === 'hard' ? 'bg-red-100 text-red-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {(q.difficulty || 'medium').toLowerCase()}
                        </span>
                      </div>

                      {q.options && q.options.length > 0 ? (
                        <div className="space-y-3 mb-4">
                          {q.options.map((opt: string, optIdx: number) => (
                            <div
                              key={optIdx}
                              className={`px-4 py-3 rounded-xl text-sm border transition-all duration-200 ${
                                opt === q.correct_answer
                                  ? 'bg-emerald-500 text-white font-medium border-emerald-500 shadow-lg shadow-emerald-500/25'
                                  : 'bg-white/80 border-gray-200 hover:bg-white hover:border-emerald-300 hover:shadow-md'
                              }`}
                            >
                              <span className="font-semibold mr-2">{String.fromCharCode(65 + optIdx)}.</span>
                              {opt}
                              {opt === q.correct_answer && <span className="ml-2 text-emerald-200">✓</span>}
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
                          <p className="text-sm text-blue-800">
                            📝 Question content needs to be developed.
                          </p>
                        </div>
                      )}

                      {q.hint && (
                        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-3">
                          <p className="text-sm text-blue-800 font-medium">
                            💡 Hint: {q.hint}
                          </p>
                        </div>
                      )}

                      {q.explanation && (
                        <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                          <p className="text-sm text-green-800 font-medium">
                            ✅ Explanation: {q.explanation}
                          </p>
                        </div>
                      )}
                    </div>
                  ))}
                </div>

                {/* Download Quiz Button */}
                <div className="mt-6 flex justify-center">
                  <button
                    onClick={handleDownloadQuiz}
                    disabled={downloadingQuiz}
                    className="inline-flex items-center gap-2 px-6 py-3 bg-linear-to-r from-blue-600 to-indigo-600 text-white text-sm font-medium rounded-xl hover:from-blue-700 hover:to-indigo-700 transition-all duration-200 shadow-lg shadow-blue-500/25 hover:shadow-xl hover:shadow-blue-500/40 transform hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
                  >
                    <span>📄</span>
                    {downloadingQuiz ? 'Downloading...' : 'Download Quiz (Word)'}
                  </button>
                </div>

                {/* Practice Exercises Section
                {group.pack.quiz.practice_exercises && group.pack.quiz.practice_exercises.length > 0 && (
                  <div className="space-y-4 mt-8">
                    <h5 className="text-lg font-semibold text-zinc-900 mb-4">🎯 Practice Exercises</h5>
                    {group.pack.quiz.practice_exercises.map((exercise: unknown, idx: number) => {
                      const ex = exercise as { title?: string; instructions?: string; problems?: string[]; answer_key?: string[] };
                      return (
                        <div key={idx} className="bg-gradient-to-br from-orange-50 to-red-50 p-6 rounded-2xl border border-orange-200/50 shadow-lg shadow-orange-500/10 transition-all duration-300 hover:shadow-xl hover:shadow-orange-500/20">
                          <div className="flex items-start gap-3 mb-4">
                            <div className="w-8 h-8 bg-gradient-to-r from-orange-500 to-red-500 rounded-full flex items-center justify-center text-white font-bold text-sm">
                              {idx + 1}
                            </div>
                            <div className="flex-1">
                              <h4 className="text-zinc-900 text-lg font-medium tracking-tight mb-2">
                                {ex.title}
                            </h4>
                            <div className="flex items-center gap-3 text-sm text-zinc-600 mb-3">
                              <span className="flex items-center gap-1">
                                <span className="font-medium">ID:</span>
                                <span>{ex.exercise_id}</span>
                              </span>
                              <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                                (ex.difficulty || '').toLowerCase() === 'easy' ? 'bg-green-100 text-green-800' :
                                (ex.difficulty || '').toLowerCase() === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                                (ex.difficulty || '').toLowerCase() === 'hard' ? 'bg-red-100 text-red-800' :
                                'bg-gray-100 text-gray-800'
                              }`}>
                                {(ex.difficulty || 'medium').toLowerCase()}
                              </span>
                            </div>
                          </div>
                        </div>

                        <div className="bg-white/80 border border-orange-200 rounded-lg p-4 mb-4">
                          <p className="text-sm text-zinc-800 font-medium mb-3">
                            📋 Instructions: {ex.instructions}
                          </p>
                          {ex.problems && ex.problems.length > 0 && (
                            <div className="space-y-2">
                              <p className="text-sm font-medium text-zinc-700">Problems:</p>
                              <ol className="list-decimal list-inside space-y-1 text-sm text-zinc-600">
                                {ex.problems.map((problem: string, pIdx: number) => (
                                  <li key={pIdx}>{problem}</li>
                                ))}
                              </ol>
                            </div>
                          )}
                        </div>

                        {ex.answer_key && ex.answer_key.length > 0 && (
                          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                            <p className="text-sm font-medium text-green-800 mb-2">Answer Key:</p>
                            <ol className="list-decimal list-inside space-y-1 text-sm text-green-700">
                              {ex.answer_key.map((answer: string, aIdx: number) => (
                                <li key={aIdx}>{answer}</li>
                              ))}
                            </ol>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )} */}
              </div>
            ) : (
              <div className="bg-linear-to-br from-gray-50 to-slate-50 p-8 rounded-3xl border border-gray-200/50 shadow-lg">
                <div className="text-center">
                  <div className="w-16 h-16 bg-gray-200 rounded-full mx-auto mb-4 flex items-center justify-center">
                    <span className="text-lg font-semibold text-gray-600">🧠</span>
                  </div>
                  <h4 className="text-zinc-900 mb-2 text-lg font-semibold">No Quiz Available</h4>
                  <p className="text-zinc-600 text-sm">Quiz content will appear here once generated</p>
                  {/* Generation Controls */}
                  {SHOW_GENERATION_BUTTONS && (
                  <div className="mt-6 p-4 bg-blue-50 rounded-xl border border-blue-100 flex flex-col gap-3 mx-auto max-w-md text-left">
                    <p className="text-sm text-blue-800 mb-2">
                        Generate a video based on the pack plan?
                    </p>
                    <button
                        onClick={() => handleGenerateAssets('video')}
                        disabled={generating}
                        className={`px-4 py-2 rounded-lg text-white font-medium text-sm transition-colors ${
                            generating 
                            ? 'bg-stone-400 cursor-not-allowed' 
                            : 'bg-blue-600 hover:bg-blue-700 shadow-sm'
                        }`}
                    >
                        {generating ? 'Starting Generation...' : 'Generate Video (MP4)'}
                    </button>
                    {message && (
                        <p className={`text-xs ${message.includes('Error') ? 'text-red-600' : 'text-green-600'}`}>
                            {message}
                        </p>
                    )}
                  </div>
                  )}                </div>
              </div>
            );
            })()}
          </div>
        );

      case 'practice':
        return (
          <div className="space-y-6">
            <div className="text-center mb-8">
              <h4 className="mb-2 text-xl font-semibold tracking-tight bg-linear-to-r from-orange-600 to-red-600 bg-clip-text text-transparent">
                Practice Exercises
              </h4>
              <p className="text-zinc-600 text-sm">Apply your knowledge with these hands-on activities</p>
            </div>

            {group.pack.practice && Array.isArray(group.pack.practice) && group.pack.practice.length > 0 ? (
              group.pack.practice.map((exercise: PracticeExercise, idx: number) => (
                <div key={idx} className="bg-linear-to-br from-orange-50 to-red-50 p-6 rounded-2xl border border-orange-200/50 shadow-lg shadow-orange-500/10 transition-all duration-300 hover:shadow-xl hover:shadow-orange-500/20">
                  <div className="flex items-start gap-3 mb-4">
                    <div className="w-8 h-8 bg-linear-to-r from-orange-500 to-red-500 rounded-full flex items-center justify-center text-white font-bold text-sm">
                      {idx + 1}
                    </div>
                    <div className="flex-1">
                      <h4 className="text-zinc-900 mb-3 text-lg font-medium tracking-tight">
                        {exercise.title}
                      </h4>
                      <div className="flex items-center gap-3 text-sm text-zinc-600 mb-3">
                        <span className="flex items-center gap-1">
                          <span className="font-medium">ID:</span>
                          <span>{exercise.exercise_id}</span>
                        </span>
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                          (exercise.difficulty || '').toLowerCase() === 'easy' ? 'bg-green-100 text-green-800' :
                          (exercise.difficulty || '').toLowerCase() === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                          (exercise.difficulty || '').toLowerCase() === 'hard' ? 'bg-red-100 text-red-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {(exercise.difficulty || 'medium').toLowerCase()}
                        </span>
                      </div>
                      <div className="bg-white/80 p-4 rounded-lg border border-orange-200/30">
                        <p className="text-zinc-800 text-sm leading-relaxed font-medium mb-3">
                          📋 {exercise.instructions}
                        </p>
                        {exercise.problems && exercise.problems.length > 0 && (
                          <div className="space-y-2">
                            <p className="text-sm font-medium text-zinc-700">Problems:</p>
                            <ol className="list-decimal list-inside space-y-1 text-sm text-zinc-600">
                              {exercise.problems.map((problem: string, pIdx: number) => (
                                <li key={pIdx}>{problem}</li>
                              ))}
                            </ol>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  {exercise.answer_key && exercise.answer_key.length > 0 && (
                    <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                      <p className="text-sm font-medium text-green-800 mb-2">Answer Key:</p>
                      <ol className="list-decimal list-inside space-y-1 text-sm text-green-700">
                        {exercise.answer_key.map((answer: string, aIdx: number) => (
                          <li key={aIdx}>{answer}</li>
                        ))}
                      </ol>
                    </div>
                  )}
                </div>
              ))
            ) : (
              <div className="bg-linear-to-br from-gray-50 to-slate-50 p-8 rounded-3xl border border-gray-200/50 shadow-lg">
                <div className="text-center">
                  <div className="w-16 h-16 bg-gray-200 rounded-full mx-auto mb-4 flex items-center justify-center">
                    <span className="text-lg font-semibold text-gray-600">🎯</span>
                  </div>
                  <h4 className="text-zinc-900 mb-2 text-lg font-semibold">No Practice Exercises</h4>
                  <p className="text-zinc-600 text-sm">Practice exercises will appear here once generated</p>
                </div>
              </div>
            )}
          </div>
        );

      case 'evaluation':
        return (
          <div className="space-y-6">
            <div className="bg-white p-6 rounded-2xl border border-stone-200 shadow-sm">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <h4 className="text-lg font-semibold text-stone-800">Teacher Evaluation</h4>
                  <p className="text-sm text-stone-500">
                    Rate each metric from 1-5 for this group. We will compute the average.
                  </p>
                </div>
                <div className="text-sm text-stone-600">
                  Group: <span className="font-medium">{group.groupName || group.id}</span>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-sm border-separate border-spacing-0">
                  <thead>
                    <tr className="bg-stone-50">
                      <th className="text-left px-3 py-2 border-b border-stone-200">Metric</th>
                      <th className="text-left px-3 py-2 border-b border-stone-200">Question</th>
                      {[1, 2, 3, 4, 5].map((score) => (
                        <th key={score} className="text-center px-2 py-2 border-b border-stone-200">
                          {score}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {EVALUATION_SECTIONS.map((section) => (
                      <Fragment key={section.id}>
                        <tr>
                          <td
                            colSpan={7}
                            className="px-3 py-2 text-xs font-semibold uppercase text-stone-500 bg-stone-100/70 border-b border-stone-200"
                          >
                            {section.title}
                          </td>
                        </tr>
                        {section.items.map((item) => (
                          <tr key={item.code} className="bg-white">
                            <td className="px-3 py-2 border-b border-stone-100 font-medium text-stone-700">
                              {item.code} - {item.label}
                              {item.reverse && (
                                <span className="ml-2 text-xs text-amber-600">(dao chieu)</span>
                              )}
                            </td>
                            <td className="px-3 py-2 border-b border-stone-100 text-stone-600">
                              {item.question}
                            </td>
                            {[1, 2, 3, 4, 5].map((score) => (
                              <td key={score} className="px-2 py-2 border-b border-stone-100 text-center">
                                <input
                                  type="radio"
                                  name={`rating-${item.code}`}
                                  value={score}
                                  checked={evaluationRatings[item.code] === score}
                                  onChange={() =>
                                    setEvaluationRatings((prev) => ({
                                      ...prev,
                                      [item.code]: score,
                                    }))
                                  }
                                />
                              </td>
                            ))}
                          </tr>
                        ))}
                      </Fragment>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="mt-4 grid gap-4 md:grid-cols-3">
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-stone-700 mb-1">Notes</label>
                  <textarea
                    className="w-full border border-stone-200 rounded-lg p-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-200"
                    rows={3}
                    placeholder="Optional notes from the teacher..."
                    value={evaluationNotes}
                    onChange={(e) => setEvaluationNotes(e.target.value)}
                  />
                </div>
                <div className="flex flex-col justify-between">
                  <div className="text-sm text-stone-600">
                    Rated: {ratedCount}/{evaluationItems.length}
                    <div className="mt-1 font-semibold text-stone-800">
                      Average: {averageRating || '--'} / 5
                    </div>
                  </div>
                  <button
                    onClick={handleSubmitEvaluation}
                    disabled={evaluationSaving || !allRated}
                    className={`mt-3 px-4 py-2 rounded-lg text-white text-sm font-medium transition-colors ${
                      evaluationSaving || !allRated
                        ? 'bg-stone-400 cursor-not-allowed'
                        : 'bg-blue-600 hover:bg-blue-700'
                    }`}
                  >
                    {evaluationSaving ? 'Saving...' : 'Submit Evaluation'}
                  </button>
                  {evaluationUrl && (
                    <a
                      href={evaluationUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-2 text-xs text-blue-600 hover:underline"
                    >
                      View saved evaluation
                    </a>
                  )}
                </div>
              </div>

              {evaluationMessage && (
                <div className="mt-3 text-sm text-stone-600">{evaluationMessage}</div>
              )}
            </div>
          </div>
        );

      case 'verification': {
        const checks = [
          {
            label: 'Quiz is valid (clear questions, correct answers)',
            pass: group.pack.verification.quiz_valid,
            icon: '🧠',
            color: 'emerald',
          },
          {
            label: 'Teaching content aligns with assessment',
            pass: group.pack.verification.alignment,
            icon: '🎯',
            color: 'blue',
          },
          {
            label: 'Complies with curriculum',
            pass: group.pack.verification.curriculum,
            icon: '📚',
            color: 'purple',
          },
        ];

        const passedCount = checks.filter(check => check.pass).length;
        const totalCount = checks.length;

        return (
          <div className="space-y-6">
            <div className="text-center mb-8">
              <h4 className="mb-2 text-xl font-semibold tracking-tight bg-linear-to-r from-gray-600 to-slate-600 bg-clip-text text-transparent">
                ✅ Quality Verification
              </h4>
              <p className="text-zinc-600 text-sm">Content quality and compliance checks</p>
              <div className="mt-3 inline-flex items-center gap-2 px-4 py-2 bg-gray-100 rounded-full">
                <span className="text-sm font-medium text-gray-700">
                  {passedCount}/{totalCount} checks passed
                </span>
              </div>
            </div>

            <div className="grid gap-4">
              {checks.map((check, idx) => (
                <div key={idx} className={`p-5 rounded-2xl border transition-all duration-300 hover:shadow-lg ${
                  check.pass
                    ? 'bg-linear-to-r from-emerald-50 to-green-50 border-emerald-200/50 hover:shadow-emerald-500/10'
                    : 'bg-linear-to-r from-red-50 to-pink-50 border-red-200/50 hover:shadow-red-500/10'
                }`}>
                  <div className="flex items-center gap-4">
                    <div className={`w-12 h-12 rounded-full flex items-center justify-center text-lg border-2 ${
                      check.pass
                        ? 'bg-emerald-500 text-white border-emerald-500 shadow-lg shadow-emerald-500/25'
                        : 'bg-red-500 text-white border-red-500 shadow-lg shadow-red-500/25'
                    }`}>
                      {check.pass ? '✓' : '✗'}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-lg">{check.icon}</span>
                        <span className={`text-sm font-medium ${
                          check.pass ? 'text-emerald-800' : 'text-red-800'
                        }`}>
                          {check.pass ? 'Passed' : 'Failed'}
                        </span>
                      </div>
                      <p className="text-zinc-700 text-sm leading-relaxed">{check.label}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      }

      // Add Flashcards Case
      case 'flashcards': {
        if (lessonId == null) {
          return (
            <div className="bg-white p-6 rounded-2xl border border-stone-200">
              <h4 className="text-lg font-semibold text-stone-800 mb-2">Flashcards</h4>
              <p className="text-stone-600 text-sm">
                Missing <code>lessonId</code>. Please pass lessonId into TeachingPackPreview to load flashcards.
              </p>
            </div>
          );
        }


        // Robust mastery extraction
        // Check local state or group specific
        // But here we want a specific Generate button
        
        const mastery =
          (group as any).mastery_level ??
          (group as any).proficiency_level ??
          (group as any).level ??
          (group as any).pack?.group?.mastery_level ??
          '';

        const defaultFlashcardGroup = mapMasteryToFlashcardGroupName(mastery);

        const handleGenerateFlashcards = async () => {
            setGenerating(true);
            setMessage(`Generating ${defaultFlashcardGroup} Flashcards...`);
            try {
                const pId = await ensurePackCommitted();
                if (!pId) {
                    setGenerating(false);
                    return;
                }
                
                // Call the new group-specific flashcard endpoint
                const res = await apiService.generatePackGroupFlashcards(Number(pId), group.id);
                
                setMessage("Flashcards Generated!");
                
                // Update Local State for immediate feedback
                if (res && res.groups) {
                     setFlashcardData(res);
                     if (res.flashcard_url) {
                        setFlashcardUrl(res.flashcard_url);
                     }
                }

                if (onRefresh) onRefresh();
            } catch (e: any) {
                setMessage("Error: " + e.message);
            } finally {
                setGenerating(false);
            }
        };

        if (lessonId == null) {
          // Fallback UI if lessonId missing, BUT teaching pack context might allow manual generation
          return (
            <div className="bg-white p-6 rounded-2xl border border-stone-200">
                <div className="flex justify-between items-center mb-4">
                  <div>
                    <h4 className="text-lg font-semibold text-stone-800">Flashcards ({defaultFlashcardGroup})</h4>
                    <p className="text-stone-500 text-sm">Target Level: {mastery || 'Standard'}</p>
                  </div>
                  <button 
                    onClick={handleGenerateFlashcards}
                    disabled={generating}
                    className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
                  >
                    {generating ? 'Generating...' : 'Generate New Flashcards'}
                  </button>
                </div>
                {message && <div className="text-sm text-blue-600 mb-4">{message}</div>}
                <div className="p-8 text-center text-gray-400">
                    No flashcards specific for {defaultFlashcardGroup} yet.
                </div>
            </div>
          );
        }

        console.log('Flashcards Debug:', { 
            lessonId, 
            rawMastery: mastery, 
            mappedGroup: defaultFlashcardGroup 
        });

        // Check if flashcards are already generated for this group (use local state)
        const hasFlashcards = flashcardData && Array.isArray(flashcardData.groups) && flashcardData.groups.length > 0;

        return (
          <div className="relative">
              <div className="absolute top-2 right-2 z-10 flex gap-2">
                  {lessonId && (
                      <button
                          onClick={() => window.open(`/?mode=student_theory&lessonId=${lessonId}`, '_blank')}
                          className="px-3 py-1 text-xs font-bold rounded-full bg-green-100 text-green-700 hover:bg-green-200 transition-colors flex items-center gap-1 shadow-sm border border-green-200"
                          title="Open Student View"
                      >
                          🔗 Student View
                      </button>
                  )}
                  {(!hasFlashcards || !flashcardUrl) && (
                       <button 
                        onClick={handleGenerateFlashcards}
                        disabled={generating}
                        className={`px-3 py-1 text-xs font-bold rounded-full transition-colors shadow-sm border ${
                            hasFlashcards ? 'bg-blue-100 text-blue-700 border-blue-200 hover:bg-blue-200' : 'bg-purple-100 text-purple-700 border-purple-200 hover:bg-purple-200'
                        }`}
                        title={hasFlashcards ? "Regenerate flashcards and create HTML download" : "Generate specific flashcards for this level"}
                      >
                        {generating ? '...' : (hasFlashcards ? 'Regenerate HTML' : `Generate ${defaultFlashcardGroup}`)}
                      </button>
                  )}
              </div>
              {message && generating && (
                <div className="absolute top-10 right-2 z-10 bg-white p-2 shadow rounded text-xs text-purple-600">
                    {message}
                </div>
              )}
              
             <FlashcardView
                lessonId={lessonId || 0}
                initialData={flashcardData}
                onClose={() => {}}
                isStandalone={true}
                defaultGroup={defaultFlashcardGroup} // ✅ Beginner/Intermediate/Advanced/General
                targetMastery={group.mastery}
                skipFetch={false} // Allow fetch if initialData is missing (fallback behavior)
                downloadUrl={flashcardUrl || undefined}
              />
          </div>
        );
      }

      default:
        return null;
    }
  };

  return (
    <div className="mt-8">
      <div className="flex items-center gap-3 text-2xl font-semibold mb-6 text-zinc-900 tracking-tight">
        <div className="w-1 h-6 bg-linear-to-b from-yellow-400 to-yellow-600 rounded-sm" />
        Teaching Pack Preview - Group {group.id}
      </div>

      <div className="flex gap-1 border-b border-gray-200 mb-8 pb-1 bg-gray-50/50 rounded-t-2xl p-2">
        <button
          className={`px-6 py-3 rounded-xl text-sm font-medium transition-all duration-300 ${
            activeTab === 'slides_preview'
              ? 'text-blue-700 bg-white shadow-lg shadow-blue-500/20 border border-blue-200'
              : 'text-zinc-500 bg-transparent hover:text-blue-600 hover:bg-white/50'
          }`}
          onClick={() => onTabChange('slides_preview')}
        >
          Preview
        </button>
        <button
          className={`px-6 py-3 rounded-xl text-sm font-medium transition-all duration-300 ${
            activeTab === 'video'
              ? 'text-indigo-700 bg-white shadow-lg shadow-indigo-500/20 border border-indigo-200'
              : 'text-zinc-500 bg-transparent hover:text-indigo-600 hover:bg-white/50'
          }`}
          onClick={() => onTabChange('video')}
        >
          Video
        </button>
        <button
          className={`px-6 py-3 rounded-xl text-sm font-medium transition-all duration-300 ${
            activeTab === 'quiz'
              ? 'text-emerald-700 bg-white shadow-lg shadow-emerald-500/20 border border-emerald-200'
              : 'text-zinc-500 bg-transparent hover:text-emerald-600 hover:bg-white/50'
          }`}
          onClick={() => onTabChange('quiz')}
        >
          Quiz
        </button>
        <button
          className={`px-6 py-3 rounded-xl text-sm font-medium transition-all duration-300 ${
            activeTab === 'practice'
              ? 'text-orange-700 bg-white shadow-lg shadow-orange-500/20 border border-orange-200'
              : 'text-zinc-500 bg-transparent hover:text-orange-600 hover:bg-white/50'
          }`}
          onClick={() => onTabChange('practice')}
        >
          Practice
        </button>
        <button
          className={`px-6 py-3 rounded-xl text-sm font-medium transition-all duration-300 ${
            activeTab === 'flashcards'
              ? 'text-purple-700 bg-white shadow-lg shadow-purple-500/20 border border-purple-200'
              : 'text-zinc-500 bg-transparent hover:text-purple-600 hover:bg-white/50'
          }`}
          onClick={() => onTabChange('flashcards')}
        >
          Flashcards
        </button>  
        <button
          className={`px-6 py-3 rounded-xl text-sm font-medium transition-all duration-300 ${
            activeTab === 'evaluation'
              ? 'text-teal-700 bg-white shadow-lg shadow-teal-500/20 border border-teal-200'
              : 'text-zinc-500 bg-transparent hover:text-teal-600 hover:bg-white/50'
          }`}
          onClick={() => onTabChange('evaluation')}
        >
          Evaluation
        </button>
        <button
          className={`px-6 py-3 rounded-xl text-sm font-medium transition-all duration-300 ${
            activeTab === 'verification'
              ? 'text-gray-700 bg-white shadow-lg shadow-gray-500/20 border border-gray-200'
              : 'text-zinc-500 bg-transparent hover:text-gray-600 hover:bg-white/50'
          }`}
          onClick={() => onTabChange('verification')}
        >
          Verify
        </button>
      </div>

      <div className="bg-stone-50/40 p-6 rounded-2xl min-h-75 backdrop-blur-lg">
        {renderTabContent()}
      </div>
    </div>
  );
}
