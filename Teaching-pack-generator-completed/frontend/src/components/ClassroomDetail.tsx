import { useState, useEffect } from 'react';
import type { Classroom } from './ClassroomList';
import InputSection from './InputSection';
import GroupingSection from './GroupingSection';
import TeachingPackPreview from './TeachingPackPreview';
import Loading from './Loading';
import EmptyState from './EmptyState';
// Removed unused TheoryQnAView import
import type { LessonData, Skill, DiagnosticQuestion, InstructionGroup, TabType, TeachingPackStatus, GroupsData, GroupOverview, PracticeExercise } from '../types';
import { apiService, API_BASE_URL } from '../services/api';

type Group = InstructionGroup; // Alias for compatibility

interface ClassroomDetailProps {
  classroom: Classroom;
  onBack: () => void;
}

export default function ClassroomDetail({ classroom, onBack }: ClassroomDetailProps) {
  const [fileName, setFileName] = useState('');
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [studentListFileName, setStudentListFileName] = useState('');
  const [studentListFile, setStudentListFile] = useState<File | null>(null);
  const [grade, setGrade] = useState(classroom.grade);
  const [studentCount, setStudentCount] = useState(classroom.student_count.toString());
  const [result, setResult] = useState<LessonData | null>(null);
  const [selectedGroup, setSelectedGroup] = useState<InstructionGroup | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('slides_preview');
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('Processing...');
  const [skills, setSkills] = useState<Skill[]>([]);
  const [newSkillName, setNewSkillName] = useState('');
  const [diagnosticQuestions, setDiagnosticQuestions] = useState<DiagnosticQuestion[]>([]);
  const [newQuestion, setNewQuestion] = useState({ question: '', answer: '', skillId: '' });
  const [error, setError] = useState<string | null>(null);
  const [teachingPacks, setTeachingPacks] = useState<TeachingPackStatus[]>([]);
  const [selectedTeachingPackId, setSelectedTeachingPackId] = useState<string>('');

  const setSelectedTeachingPackIdWithLog = (id: string) => {
    console.log('Setting selectedTeachingPackId to:', id);
    setSelectedTeachingPackId(id);
  };
  const [groups, setGroups] = useState<GroupsData | null>(null);
  const [numGroups, setNumGroups] = useState(4);
  const [currentTab, setCurrentTab] = useState<'lessons' | 'groups' | 'students'>('lessons');
  const [creatingGroups, setCreatingGroups] = useState(false);

  // Auto-refresh data when selected teaching pack changes
  useEffect(() => {
    if (selectedTeachingPackId) {
      console.log('selectedTeachingPackId changed to:', selectedTeachingPackId, 'calling refreshData');
      refreshData();
    } else {
      console.log('selectedTeachingPackId is empty');
    }
  }, [selectedTeachingPackId]);

  // Helper function to convert file paths to HTTP URLs
  const convertFileUrlToHttp = (url?: string | null): string | null => {
    if (!url) {
      return null;
    }
    
    // Handle file:// URLs
    if (url.startsWith('file://')) {
      // Extract filename from file:// URL
      const pathParts = url.replace('file://', '').split('/');
      const filename = pathParts[pathParts.length - 1];
      return `${API_BASE_URL}/api/videos/${filename}`;
    }
    
    // Handle local paths starting with /outputs/
    if (url.startsWith('/outputs/')) {
      const filename = url.replace('/outputs/', '');
      if (filename.endsWith('.html')) {
          return `${API_BASE_URL}/api/outputs/${filename}`;
      }
      return `${API_BASE_URL}/api/videos/${filename}`;
    }
    
    // Handle local slides URLs
    if (url.includes('/api/slides/')) {
      return url; // Already a proper local URL
    }
    
    // Return as-is if already an HTTP URL or other format
    return url;
  };

  const normalizeSlides = (slides: any): { title: string; content: string }[] => {
    if (Array.isArray(slides)) {
      return slides.map((slide: any) => ({
        title: slide?.title || 'Untitled',
        content: slide?.content || '',
      }));
    }
    if (slides && Array.isArray(slides.slides)) {
      return slides.slides.map((slide: any) => ({
        title: slide?.title || 'Untitled',
        content: slide?.content || '',
      }));
    }
    return [];
  };

  const mapPracticeExercises = (items: any[]): PracticeExercise[] => {
    return items.map((ex: any) => ({
      exercise_id: ex?.exercise_id || `ex-${Math.random()}`,
      title: ex?.title || ex?.problem || 'Exercise',
      instructions: ex?.instructions || ex?.problem || ex?.description || '',
      problems: ex?.problems,
      answer_key: ex?.answer_key,
    }));
  };

  const mapTeachingPacksToGroups = (
    fullData: any,
    packMeta?: TeachingPackStatus
  ): InstructionGroup[] => {
    const teachingPacks = Array.isArray(fullData?.teaching_packs) ? fullData.teaching_packs : [];
    const rootPackId = packMeta?.id ?? fullData?.teaching_pack_id;

    return teachingPacks.map((pack: any, idx: number) => {
      const group = pack?.group || {};
      const groupId = String(group.group_id || `group-${idx}`);
      const packId = rootPackId ?? pack?.teaching_pack_id;

      const quizData = pack?.quiz || null;
      let practiceExercises: PracticeExercise[] = [];
      if (Array.isArray(quizData?.practice_exercises)) {
        practiceExercises = mapPracticeExercises(quizData.practice_exercises);
      } else if (Array.isArray(pack?.practice)) {
        practiceExercises = mapPracticeExercises(pack.practice);
      } else if (Array.isArray(pack?.pack_plan?.activities)) {
        practiceExercises = mapPracticeExercises(pack.pack_plan.activities);
      }

      const gaps =
        group?.gaps ??
        group?.common_misconceptions ??
        group?.missing_skills ??
        [];
      const missingSkills = Array.isArray(gaps) ? gaps.join(', ') : gaps || 'N/A';
      const recommended = group?.recommended_activities;
      const rationale =
        group?.instruction_strategy ||
        group?.rationale ||
        (Array.isArray(recommended) ? recommended.join(', ') : recommended || '');

      const flashcardUrl =
        pack?.flashcard_url ||
        (packMeta?.flashcard_urls ? packMeta.flashcard_urls[groupId] : undefined);

      return {
        id: groupId,
        groupName: group?.group_name || group?.group_id || `Group ${idx + 1}`,
        focus: group?.focus_area || group?.group_name || group?.focus || 'Focus Area',
        mastery: group?.mastery_level || group?.proficiency_level || group?.level || 'Medium',
        missing_skills: missingSkills,
        rationale,
        students: Array.isArray(group?.students) ? group.students : [],
        flashcard_url: convertFileUrlToHttp(flashcardUrl),
        pack: {
          id: packId,
          slides: normalizeSlides(pack?.slides),
          quiz: pack?.quiz || pack?.quiz_blueprint || null,
          practice: practiceExercises,
          verification: {
            quiz_valid: true,
            alignment: true,
            curriculum: true,
          },
          slides_url: pack?.slides_url || (pack?.slides as any)?.generated_url || undefined,
          video_url: convertFileUrlToHttp(
            pack?.video_url || (pack?.video as any)?.generated_url || (pack?.video as any)?.url || null
          ) || undefined,
          video_thumbnail:
            pack?.video_thumbnail || (pack?.video as any)?.thumbnail_url || (pack?.video as any)?.thumbnail || undefined,
          video: pack?.video ? (() => {
            const videoData = pack.video as any;
            let parsedScript = videoData?.script || '';
            let parsedTitle = videoData?.title || '';
            let parsedVisual = videoData?.visual_description || '';

            if (typeof parsedScript === 'string') {
              let scriptToParse = parsedScript.trim();
              if (scriptToParse.startsWith('```json')) {
                scriptToParse = scriptToParse.replace(/^```json\s*/, '').replace(/\s*```$/, '');
              }
              if (scriptToParse.startsWith('{')) {
                try {
                  const scriptObj = JSON.parse(scriptToParse);
                  parsedTitle = scriptObj.title || parsedTitle;
                  if (Array.isArray(scriptObj.script)) {
                    parsedScript = scriptObj.script.map((s: any) => s.text || s).join('\n\n');
                  } else {
                    parsedScript = scriptObj.script || parsedScript;
                  }
                  if (Array.isArray(scriptObj.visual_description)) {
                    parsedVisual = scriptObj.visual_description.join('\n\n');
                  } else {
                    parsedVisual = scriptObj.visual_description || parsedVisual;
                  }
                } catch (e) {
                  // Keep as-is if not JSON
                }
              }
            } else if (Array.isArray(parsedScript)) {
              parsedScript = parsedScript.map((s: any) => typeof s === 'string' ? s : s.text || JSON.stringify(s)).join('\n\n');
            }

            return {
              title: parsedTitle,
              script: parsedScript,
              visual_description: parsedVisual,
              generated_url: videoData?.generated_url,
              thumbnail_url: videoData?.thumbnail_url,
            };
          })() : { title: '', script: '', visual_description: '', generated_url: null, thumbnail_url: null },
        },
      };
    });
  };

  const applyFullData = (
    fullData: any,
    options: { jobId?: string; packMeta?: TeachingPackStatus }
  ) => {
    const mergedData = {
      lesson_summary: fullData?.lesson_summary ?? options.packMeta?.lesson_summary,
      skill_set: fullData?.skill_set ?? options.packMeta?.skill_set,
      diagnostic: fullData?.diagnostic ?? options.packMeta?.diagnostic,
      teaching_packs: fullData?.teaching_packs ?? options.packMeta?.teaching_pack_data?.teaching_packs ?? [],
      teaching_pack_id: fullData?.teaching_pack_id ?? options.packMeta?.id,
      lesson_id: fullData?.lesson_id ?? options.packMeta?.lesson?.id
    };

    const mappedSkills: Skill[] = (mergedData.skill_set?.skills || []).map((skill: unknown, idx: number) => {
      const s = skill as { skill_id?: string; name?: string; weight?: number; difficulty?: number };
      return {
        id: s.skill_id || idx,
        name: s.name || 'Unnamed Skill',
        rating: s.weight ? s.weight * 10 : (s.difficulty || 5),
      };
    });
    setSkills(mappedSkills);

    const diagnosticQs: DiagnosticQuestion[] = (mergedData.diagnostic?.questions || []).map((q: unknown, idx: number) => {
      const question = q as { question_id?: unknown; question_text?: string; question?: string; correct_answer?: string; skill_id?: string; options?: string[] };
      return {
        id: typeof question.question_id === 'number' ? question.question_id : idx,
        question: question.question_text || question.question || '',
        answer: question.correct_answer || '',
        skillId: String(question.skill_id || ''),
        options: question.options || [],
      };
    });
    setDiagnosticQuestions(diagnosticQs);

    const lessonTitle = mergedData.lesson_summary?.title || 'Lesson';
    const objectives = Array.isArray(mergedData.lesson_summary?.learning_objectives)
      ? mergedData.lesson_summary.learning_objectives.join(', ')
      : (mergedData.lesson_summary?.learning_objectives || '');

    const lessonData: LessonData = {
      lesson_summary: objectives ? `${lessonTitle}: ${objectives}` : lessonTitle,
      skills: mappedSkills.map(s => s.name),
      groups: mapTeachingPacksToGroups(mergedData, options.packMeta),
      job_id: options.jobId,
      teaching_pack_status: options.packMeta || (mergedData.lesson_id ? {
        id: mergedData.teaching_pack_id ? String(mergedData.teaching_pack_id) : '',
        status: 'completed',
        created_at: new Date().toISOString(),
        lesson: {
          id: mergedData.lesson_id,
          title: lessonTitle
        }
      } : undefined)
    };

    setResult(lessonData);
  };

  const refreshData = async () => {
    try {
      // Refresh teaching packs
      const packs = await apiService.getClassroomTeachingPacks(classroom.id);
      console.log('Loaded teaching packs for classroom', classroom.id, ':', packs.map(p => ({ id: p.id, title: p.title })));
      setTeachingPacks(packs);
      
      // Always refresh groups to ensure latest data from database
      const groupsData = await apiService.getClassroomGroups(classroom.id);
      if (groupsData.groups && Object.keys(groupsData.groups).length > 0) {
        setGroups(groupsData);
        
        // Process groups from API response (already merged with pack data)
        const apiGroups = groupsData.groups;
        const asFlashcardSet = (x: unknown): { groups: any[] } | undefined => {
          if (!x || typeof x !== 'object') return undefined;
          const obj = x as { groups?: unknown };
          return Array.isArray(obj.groups) ? (obj as { groups: any[] }) : undefined;
        };

        const mappedGroups: Group[] = Object.values(apiGroups).map((groupData: any, idx: number) => {
          const g = groupData as {
            group_id?: string;
            group_name?: string;
            mastery_level?: string;
            skill_mastery?: unknown;
            common_misconceptions?: string[];
            learning_pace?: string;
            students?: string[];
            description?: string;
            recommended_activities?: string[];
            video_url?: string;
            slides_url?: string;
            flashcard_url?: string;
            video_thumbnail?: string;
            pack_plan?: unknown;
            slides?: unknown;
            video?: unknown;
            quiz?: unknown;
            teaching_pack_id?: number;
            errors?: unknown[];
            flashcards?: unknown;
          };
          
          console.log(`Mapping group ${idx}: backend group_id=${g.group_id}, group_name=${g.group_name}, video_url=${g.video_url}`);
          
          // Map practice exercises if quiz exists
          const quizData = g.quiz as { practice_exercises?: unknown[] } | null;
          const practiceExercises = (quizData?.practice_exercises || []).map((ex: unknown) => {
            const e = ex as { problem?: string; hint?: string; title?: string; exercise_id?: string; instructions?: string };
            return {
              exercise_id: e.exercise_id || `ex-${Math.random()}`,
              title: e.title || e.problem || 'Exercise',
              instructions: e.instructions || e.problem || '',
              problem: e.problem || '',
              hint: e.hint || ''
            } as PracticeExercise;
          });
          
          return {
            id: g.group_id || `group-${idx}`,
            focus: g.group_name || 'Focus Area',
            mastery: g.mastery_level || 'Medium',
            missing_skills: (g.common_misconceptions || []).join(', ') || 'N/A',
            rationale: (g.recommended_activities || []).join(', ') || '',
            students: g.students || [],
            video_url: convertFileUrlToHttp(g.video_url) || undefined,
            slides_url: g.slides_url || undefined,
            video_thumbnail: g.video_thumbnail || undefined,
            pack: {
              id: g.teaching_pack_id,
              slides: Array.isArray((g.slides as { slides?: unknown[] })?.slides) 
                ? ((g.slides as { slides: unknown[] }).slides).map((slide: unknown) => {
                    const s = slide as { title?: string; content?: string };
                    return {
                      title: s.title || 'Untitled',
                      content: s.content || '',
                    };
                  })
                : [],
              quiz: g.quiz,
              practice: practiceExercises,
              verification: {
                quiz_valid: true,
                alignment: true,
                curriculum: true,
              },
              slides_url: g.slides_url || undefined,
              video_url: convertFileUrlToHttp(g.video_url) || undefined,
              flashcard_url: convertFileUrlToHttp(g.flashcard_url) || undefined,
              video_thumbnail: g.video_thumbnail || undefined,
              flashcards: asFlashcardSet(g.flashcards) as any,
            },
          };
        });

        console.log('Mapped groups with video URLs from API:', mappedGroups.map(g => ({ id: g.id, focus: g.focus, video_url: g.video_url })));

        // Build lesson summary (you may need to get this from elsewhere or set defaults)
        const lessonData: LessonData = {
          lesson_summary: 'Lesson Summary', // Placeholder
          skills: [], // Placeholder
          groups: mappedGroups,
        };

        // Attach teaching pack status if selected
        if (selectedTeachingPackId) {
            const currentPack = packs.find(p => p.id.toString() === selectedTeachingPackId);
            if (currentPack) {
                lessonData.teaching_pack_status = currentPack;
            }
        }

        setResult(lessonData);
        
        // Update selected group if it exists
        if (selectedGroup) {
          const updatedGroup = mappedGroups.find(g => g.id === selectedGroup.id || g.focus === selectedGroup.focus);
          if (updatedGroup) {
            setSelectedGroup(updatedGroup);
          }
        }
      }
    } catch (err) {
      console.error('Error refreshing data:', err);
    }
  };

  useEffect(() => {
    const fetchTeachingPacks = async () => {
      try {
        const packs = await apiService.getClassroomTeachingPacks(classroom.id);
        setTeachingPacks(packs);
        // Auto-select the first completed pack if available
        const completedPack = packs.find((pack: TeachingPackStatus) => pack.status === 'completed' && pack.teaching_pack_data);
        if (completedPack) {
          setSelectedTeachingPackId(completedPack.id.toString());
        }
      } catch (err) {
        console.error('Error fetching teaching packs:', err);
      }
    };

    fetchTeachingPacks();
  }, [classroom.id]);

  useEffect(() => {
    const fetchGroups = async () => {
      try {
        const groupsData = await apiService.getClassroomGroups(classroom.id);
        if (groupsData.groups && Object.keys(groupsData.groups).length > 0) {
          setGroups(groupsData);
        }
      } catch (err) {
        console.error('Error fetching groups:', err);
      }
    };

    if (currentTab === 'groups') {
      fetchGroups();
    }
  }, [classroom.id, currentTab]);

  const handleFileChange = (file: File | null) => {
    if (file) {
      setFileName(file.name);
      setUploadedFile(file);
      setError(null);
    }
  };

  const handleStudentListFileChange = (file: File | null) => {
    if (file) {
      setStudentListFileName(file.name);
      setStudentListFile(file);
    } else {
      setStudentListFileName('');
      setStudentListFile(null);
    }
  };

  const loadFromOutputFile = async () => {
    if (!selectedTeachingPackId) {
      setError('Please select a teaching pack to load.');
      return;
    }

    try {
      setLoading(true);
      setLoadingMessage('Loading data from teaching pack...');
      
      // Get the selected teaching pack data
      const selectedPack = teachingPacks.find(pack => pack.id.toString() === selectedTeachingPackId);
      
      if (!selectedPack || !selectedPack.teaching_pack_data) {
        throw new Error('Selected teaching pack not found or has no data');
      }
      
      console.log('Loading data from selected pack:', selectedPack.id);
      
      const fullData = selectedPack.teaching_pack_data;
      if (!fullData) {
        throw new Error('Selected teaching pack has no data');
      }

      applyFullData(fullData, { packMeta: selectedPack });
      setLoadingMessage('Completed!');
    } catch (err: unknown) {
      console.error('Error loading from output file:', err);
      setError(err instanceof Error ? err.message : 'An error occurred while loading data.');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateGroupsFromExisting = async () => {
    setCreatingGroups(true);
    setError(null);

    try {
      const result = await apiService.createGroupsFromExistingStudents(
        classroom.id,
        numGroups
      );

      setGroups(result);
      
      // Refresh classroom data
      alert(`Created ${result.num_groups} groups with ${result.num_students} students from the existing list.`);
    } catch (err: unknown) {
      console.error('Error creating groups from existing students:', err);
      setError(err instanceof Error ? err.message : 'An error occurred while creating groups.');
    } finally {
      setCreatingGroups(false);
    }
  };

  const handleGenerate = async () => {
    if (!uploadedFile) {
      setError('Please select a lesson file.');
      return;
    }

    setLoading(true);
    setError(null);
    setLoadingMessage('Uploading file and starting processing...');

    try {
      // Call API to generate teaching packs
      const numGroups = 4;
      const numStudents = parseInt(studentCount) || 30;

      const response = await apiService.generateTeachingPacks(
        uploadedFile,
        classroom.id,
        numGroups,
        numStudents,
        studentListFile
      );

      setLoadingMessage('Analyzing lesson and generating teaching packs...');

      // Poll for job status
      const jobResult = await apiService.pollJobStatus(
        response.job_id,
        (status) => {
          if (status.status === 'processing') {
            setLoadingMessage('Processing: ' + (status.message || 'Generating teaching packs...'));
          }
        }
      );

      // Transform backend result to match frontend types
      if (jobResult && jobResult.result) {
        const backendResult = jobResult.result;
        applyFullData(backendResult, { jobId: jobResult.job_id });
        if (backendResult.teaching_pack_id) {
          setSelectedTeachingPackId(String(backendResult.teaching_pack_id));
        }
        setLoadingMessage('Completed!');

        // Refresh teaching packs list
        try {
          const packs = await apiService.getClassroomTeachingPacks(classroom.id);
          setTeachingPacks(packs);
        } catch (err) {
          console.error('Error refreshing teaching packs:', err);
        }
      }
    } catch (err: unknown) {
      console.error('Error generating teaching packs:', err);
      setError(err instanceof Error ? err.message : 'An error occurred while generating teaching packs.');
    } finally {
      setLoading(false);
    }
  };

  const handleViewPack = async (group: InstructionGroup) => {
    // Refresh groups data to get latest video URLs from database
    try {
      const packIdRaw = group.pack?.id ?? selectedTeachingPackId;
      const packId = packIdRaw ? Number(packIdRaw) : NaN;
      if (!packId || Number.isNaN(packId)) {
        throw new Error('Missing teaching pack ID for group refresh');
      }
      const groupsData = await apiService.getClassroomGroups(classroom.id, packId);
      if (groupsData.groups && Object.keys(groupsData.groups).length > 0) {
        setGroups(groupsData);
        
        const groupKey = group.id;
        
        // Find the updated group data by matching group_id
        const updatedGroup = Object.values(groupsData.groups).find((g: any) => 
          g.group_id === groupKey
        );
        if (updatedGroup) {
          // Map the API group data to InstructionGroup format
          const g = updatedGroup as {
            group_id?: string;
            group_name?: string;
            mastery_level?: string;
            skill_mastery?: unknown;
            common_misconceptions?: string[];
            learning_pace?: string;
            students?: string[];
            description?: string;
            recommended_activities?: string[];
            video_url?: string;
            slides_url?: string;
            flashcard_url?: string;
            video_thumbnail?: string;
            pack_plan?: unknown;
            slides?: unknown;
            video?: unknown;
            quiz?: unknown;
            teaching_pack_id?: number;
            errors?: unknown[];
            flashcards?: unknown;
          };
          
          const mappedGroup: InstructionGroup = {
            id: g.group_id || group.id,
            focus: g.group_name || group.focus,
            mastery: g.mastery_level || group.mastery,
            missing_skills: (g.common_misconceptions || []).join(', ') || group.missing_skills,
            rationale: (g.recommended_activities || []).join(', ') || group.rationale,
            students: g.students || group.students,
            video_url: convertFileUrlToHttp(g.video_url) || group.video_url,
            slides_url: g.slides_url || group.slides_url,
            flashcard_url: convertFileUrlToHttp(g.flashcard_url) || group.flashcard_url,
            video_thumbnail: g.video_thumbnail || group.video_thumbnail,
            pack: group.pack, // Keep the existing pack data
          };
          
          setSelectedGroup(mappedGroup);
        } else {
          setSelectedGroup(group);
        }
      } else {
        setSelectedGroup(group);
      }
    } catch (error) {
      console.error('Error refreshing groups:', error);
      setSelectedGroup(group);
    }
    setActiveTab('slides_preview');
  };

  const handleSkillRatingChange = (id: number, newRating: number) => {
    const rating = Math.max(1, Math.min(10, newRating));
    setSkills(skills.map((skill) => (skill.id === id ? { ...skill, rating } : skill)));
  };

  const handleAddSkill = () => {
    if (newSkillName.trim()) {
      const newSkill = {
        id: skills.length > 0 ? Math.max(...skills.map((s) => s.id)) + 1 : 0,
        name: newSkillName.trim(),
        rating: 5,
      };
      setSkills([...skills, newSkill]);
      setNewSkillName('');
    }
  };

  const handleRemoveSkill = (id: number) => {
    setSkills(skills.filter((skill) => skill.id !== id));
    setDiagnosticQuestions(diagnosticQuestions.filter((q) => q.skillId !== id));
  };

  const handleQuestionChange = (field: string, value: string) => {
    setNewQuestion({ ...newQuestion, [field]: value });
  };

  const handleAddQuestion = () => {
    if (newQuestion.question.trim() && newQuestion.answer.trim() && newQuestion.skillId) {
      const question: DiagnosticQuestion = {
        id: diagnosticQuestions.length > 0 ? Math.max(...diagnosticQuestions.map((q) => q.id)) + 1 : 1,
        question: newQuestion.question.trim(),
        answer: newQuestion.answer.trim(),
        skillId: parseInt(newQuestion.skillId),
      };
      setDiagnosticQuestions([...diagnosticQuestions, question]);
      setNewQuestion({ question: '', answer: '', skillId: '' });
    }
  };

  const handleRemoveQuestion = (id: number) => {
    setDiagnosticQuestions(diagnosticQuestions.filter((q) => q.id !== id));
  };

  return (
    <div className="min-h-screen bg-stone-50">
      {/* Header */}
      <header className="bg-white border-b border-stone-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center gap-4">
            <button
              onClick={onBack}
              className="px-4 py-2 text-sm text-stone-600 hover:text-zinc-800 hover:bg-stone-100 rounded-lg transition-colors"
            >
              ? Back
            </button>
            <div className={`w-10 h-10 ${classroom.color} rounded-lg`} />
            <div>
              <h1 className="text-lg font-semibold text-zinc-800">{classroom.name}</h1>
              <p className="text-sm text-stone-600">{classroom.subject} - Grade {classroom.grade}</p>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex gap-1 border-b border-stone-200">
            <button
              onClick={() => setCurrentTab('lessons')}
              className={`px-6 py-3 font-medium text-sm transition-colors relative ${
                currentTab === 'lessons' 
                  ? 'text-yellow-600' 
                  : 'text-stone-600 hover:text-zinc-800'
              }`}
            >
              📚 Lessons
              {currentTab === 'lessons' && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-yellow-600"></div>
              )}
            </button>
            <button
              onClick={() => setCurrentTab('groups')}
              className={`px-6 py-3 font-medium text-sm transition-colors relative ${
                currentTab === 'groups' 
                  ? 'text-yellow-600' 
                  : 'text-stone-600 hover:text-zinc-800'
              }`}
            >
              👥 Groups
              {currentTab === 'groups' && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-yellow-600"></div>
              )}
            </button>
            <button
              onClick={() => setCurrentTab('students')}
              className={`px-6 py-3 font-medium text-sm transition-colors relative ${
                currentTab === 'students' 
                  ? 'text-yellow-600' 
                  : 'text-stone-600 hover:text-zinc-800'
              }`}
            >
              🎓 Student List
              {currentTab === 'students' && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-yellow-600"></div>
              )}
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto p-6">
        {/* Lessons Tab */}
        {currentTab === 'lessons' && (
          <>
        <InputSection
          fileName={fileName}
          studentListFileName={studentListFileName}
          grade={grade}
          studentCount={studentCount}
          onFileChange={handleFileChange}
          onStudentListFileChange={handleStudentListFileChange}
          onGradeChange={setGrade}
          onStudentCountChange={setStudentCount}
          onGenerate={handleGenerate}
          onLoadFromOutput={loadFromOutputFile}
          skills={skills}
          newSkillName={newSkillName}
          onSkillRatingChange={handleSkillRatingChange}
          onNewSkillNameChange={setNewSkillName}
          onAddSkill={handleAddSkill}
          onRemoveSkill={handleRemoveSkill}
          diagnosticQuestions={diagnosticQuestions}
          newQuestion={newQuestion}
          onQuestionChange={handleQuestionChange}
          onAddQuestion={handleAddQuestion}
          onRemoveQuestion={handleRemoveQuestion}
          teachingPacks={teachingPacks}
          selectedTeachingPackId={selectedTeachingPackId}
          onTeachingPackChange={setSelectedTeachingPackIdWithLog}
        />

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-2xl p-6 mt-6">
            <div className="flex items-start gap-3">
              <div className="text-red-500 text-xl">⚠️</div>
              <div>
                <h3 className="font-semibold text-red-800 mb-1">Error</h3>
                <p className="text-red-700 text-sm">{error}</p>
              </div>
            </div>
          </div>
        )}

        {loading && <Loading message={loadingMessage} />}

        {(result || selectedGroup) && (
          <div className="bg-white/70 backdrop-blur-lg rounded-3xl p-8 border border-black/5 transition-all duration-300 animate-slideUp hover:border-yellow-400/20 hover:-translate-y-0.5 mt-6">
            {result && (
              <>
                <GroupingSection
                  result={result}
                  onViewPack={handleViewPack}
                  selectedGroupId={selectedGroup?.id}
                />
              </>
            )}

            {selectedGroup && (
              <TeachingPackPreview
                group={selectedGroup}
                activeTab={activeTab}
                onTabChange={setActiveTab}
                jobId={result?.job_id} // Pass job ID for commits
                onRefresh={refreshData}
                lessonId={result?.teaching_pack_status?.lesson?.id} // Pass lesson ID for flashcards
              />
            )}
          </div>
        )}

        {!loading && !result && !selectedGroup && <EmptyState />}
        </>
        )}

        {/* Groups Tab */}
        {currentTab === 'groups' && (
          <div>
            {groups && groups.groups && (
              <div className="bg-white/70 backdrop-blur-lg rounded-3xl p-8 border border-black/5 mb-6">
                <div className="flex items-center gap-3 text-2xl font-semibold mb-6 text-zinc-900">
                  <div className="w-1 h-6 bg-linear-to-b from-green-400 to-green-600 rounded-sm" />
                  Generated Groups ({Object.keys(groups.groups).length} groups)
                </div>

                <div className="grid grid-cols-2 gap-4">
                  {Object.entries(groups.groups).map(([groupId, groupData]: [string, GroupOverview]) => (
                    <div key={groupId} className="border border-gray-200 rounded-xl p-4 bg-white/50">
                      <div className="flex items-center justify-between mb-3">
                        <h3 className="font-semibold text-lg text-zinc-800">{groupData.profile.group_name}</h3>
                        <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                          (groupData.profile.mastery_level || '').toLowerCase() === 'advanced' ? 'bg-purple-100 text-purple-700' :
                          (groupData.profile.mastery_level || '').toLowerCase() === 'high' ? 'bg-green-100 text-green-700' :
                          (groupData.profile.mastery_level || '').toLowerCase() === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                          'bg-red-100 text-red-700'
                        }`}>
                          {groupData.profile.mastery_level || 'Unknown'}
                        </span>
                      </div>
                      
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span className="text-zinc-600">Description:</span>
                          <span className="font-medium text-xs truncate max-w-[200px]" title={groupData.profile.description}>
                            {groupData.profile.description}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-zinc-600">Students:</span>
                          <span className="font-medium">{groupData.students.length}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-zinc-600">Style:</span>
                          <span className="font-medium">{groupData.profile.learning_style}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-zinc-600">Rationale:</span>
                          <span className="font-medium text-xs truncate max-w-[200px]" title={groupData.profile.rationale}>
                            {groupData.profile.rationale}
                          </span>
                        </div>
                      </div>

                      {groupData.students && groupData.students.length > 0 && (
                        <details className="mt-3 text-xs">
                          <summary className="cursor-pointer text-blue-600 hover:text-blue-700">
                            View list ({groupData.students.length} students)
                          </summary>
                          <ul className="mt-2 space-y-1 pl-4 max-h-32 overflow-y-auto">
                            {groupData.students.map((student: string, idx: number) => (
                              <li key={idx} className="list-disc text-zinc-600">{student}</li>
                            ))}
                          </ul>
                        </details>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {!groups && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-6">
                <div className="text-center mb-4">
                  <p className="text-yellow-800 mb-4">No groups have been created yet.</p>
                  <p className="text-sm text-yellow-700 mb-4">
                    Create smart groups from the existing student list in this class.
                  </p>
                </div>
                <div className="flex justify-center gap-4">
                  <div className="flex items-center gap-2">
                    <label className="text-sm font-medium text-yellow-800">Groups:</label>
                    <input
                      type="number"
                      min="2"
                      max="10"
                      value={numGroups}
                      onChange={(e) => setNumGroups(parseInt(e.target.value) || 4)}
                      className="w-16 px-2 py-1 border border-yellow-300 rounded text-center"
                    />
                  </div>
                  <button
                    onClick={handleCreateGroupsFromExisting}
                    disabled={creatingGroups}
                    className="bg-yellow-500 hover:bg-yellow-600 disabled:bg-yellow-300 text-white px-6 py-2 rounded-lg font-medium transition-colors disabled:cursor-not-allowed"
                  >
                    {creatingGroups ? 'Creating...' : 'Create AI Groups'}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Students Tab */}
        {currentTab === 'students' && (
          <div className="bg-white/70 backdrop-blur-lg rounded-3xl p-8 border border-black/5">
            <div className="flex items-center gap-3 text-2xl font-semibold mb-6 text-zinc-900">
              <div className="w-1 h-6 bg-linear-to-b from-blue-400 to-blue-600 rounded-sm" />
              Student List ({classroom.student_count} students)
            </div>
            <p className="text-zinc-600">The student list feature is under development...</p>
          </div>
        )}
      </div>
    </div>
  );
}
