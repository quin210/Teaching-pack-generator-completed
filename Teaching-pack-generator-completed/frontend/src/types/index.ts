export interface Slide {
  title: string;
  content: string;
}

export interface Quiz {
  question: string;
  options: string[];
  correct: number;
  hint?: string;
}

export interface QuizData {
  questions?: QuizQuestion[];
  total_questions?: number;
  estimated_time?: string;
  practice_exercises?: PracticeExercise[];
}

export interface Practice {
  problem: string;
  hint: string;
}

export interface Verification {
  quiz_valid: boolean;
  alignment: boolean;
  curriculum: boolean;
}

export interface TeachingPackStatus {
  id: string;
  status: string;
  title?: string;
  lesson_summary?: any;
  skill_set?: any;
  diagnostic?: any;
  groups?: any;
  teaching_pack_data?: any;
  video_urls?: Record<string, string>;
  slides_urls?: Record<string, string>;
  flashcard_urls?: Record<string, string>;
  created_at: string;
  completed_at?: string;
  classroom?: {
    id: number;
    name: string;
  };
  lesson?: {
    id: number;
    title: string;
  };
}

export interface Classroom {
  id: number;
  name: string;
  grade: string;
  subject: string;
  student_count: number;
  teacher_id: number;
  created_at: string;
  groups_configuration?: unknown;
}

export interface GroupsData {
  groups: Record<string, GroupOverview>;
  num_groups: number;
  num_students: number;
}

export type TabType = 'slides_preview' | 'quiz_preview' | 'groups_overview' | 'simulation' | 'video_preview' | 'video' | 'quiz' | 'practice' | 'verification' | 'flashcards' | 'evaluation';

export interface GroupProfile {
  group_name: string;
  description: string;
  mastery_level: string;
  learning_style: string;
  rationale: string;
}

export interface GroupOverview {
  group_id: string;
  students: string[];
  profile: GroupProfile;
}

export interface QuizQuestion {
  question_text?: string;
  question_id: string;
  skill_id: string;
  difficulty?: string;
  options?: string[];
  correct_answer?: string;
  hint?: string;
  explanation?: string;
}

export interface PracticeExercise {
  title: string;
  exercise_id: string;
  difficulty?: string;
  instructions: string;
  problems?: string[];
  answer_key?: string[];
}

export interface TeachingPack {
  id?: string | number; // Added specific ID for reference
  slides: Slide[];
  quiz: QuizData | QuizQuestion[] | unknown; // Full quiz object with questions, practice_exercises, etc.
  practice: PracticeExercise[];
  verification: Verification;
  slides_url?: string; // URL to generated slides
  video_url?: string; // URL to generated video
  video_thumbnail?: string; // Thumbnail for video
  flashcards?: { groups: FlashcardGroup[] }; // Flashcards for this specific pack
  flashcard_url?: string; // URL to generated flashcards HTML
  video?: {
      title?: string;
      script?: string;
      visual_description?: string;
      duration_seconds?: number;
  };
}

export interface InstructionGroup {
  id: string;
  groupName?: string; // Display name for the group
  focus: string;
  mastery: string;
  missing_skills: string;
  rationale: string;
  pack: TeachingPack;
  students?: string[];  // List of student IDs/names in this group
  video_url?: string | null;
  slides_url?: string | null;
  flashcard_url?: string | null;
  video_thumbnail?: string | null;
}

export interface Student {
  id: number;
  student_code: string;
  full_name: string;
  email: string;
  classroom_id: number;
  created_at: string;
}

export interface Skill {
  id: number;
  name: string;
  rating: number;
}

export interface DiagnosticQuestion {
  id: number;
  question: string;
  answer: string;
  skillId: string | number;
  options?: string[];
}

export interface LessonData {
  lesson_summary: string;
  skills: string[];
  groups: InstructionGroup[];
  job_id?: string;
  teaching_pack_id?: number;
  teaching_pack_status?: TeachingPackStatus;
}

export interface Flashcard {
  type: 'definition' | 'term' | 'principle' | 'purpose' | 'classification';
  front: string;
  back: string;
  difficulty?: 'easy' | 'medium' | 'hard' | 'advanced';
}

export interface GroupFlashcardSet {
  group_id: string;
  group_name: string;
  proficiency_level: string;
  flashcards: Flashcard[];
}

export interface TheoryQuestion {
  id: number;
  question: string;
  answer: string;
}

export interface GroupTheoryQuestionSet {
    group_name: string;
    group_description?: string;
    questions: TheoryQuestion[];
}

export interface TheoryQuestionsResponse {
    groups: GroupTheoryQuestionSet[];
}

export interface FlashcardSet {
  flashcards: Flashcard[];
  group_flashcards?: GroupFlashcardSet[];
}

export interface Flashcard {
  id?: number;
  type: 'definition' | 'term' | 'principle' | 'purpose' | 'classification';
  front: string;
  back: string;
  difficulty?: 'easy' | 'medium' | 'hard' | 'advanced';
}

export interface FlashcardGroup {
  group_name: string;
  proficiency_level?: string;
  flashcards: Flashcard[];
}

export interface FlashcardSet {
  groups: FlashcardGroup[];
}

export interface TeachingPackPreviewProps {
  group: InstructionGroup;
  activeTab: TabType;
  onTabChange: (tab: TabType) => void;
  jobId?: string;
  onRefresh?: () => void;
}
