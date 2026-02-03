// API Service for Teaching Pack Generator Backend

import type { TeachingPackStatus, Classroom, GroupsData, Student } from '../types';

export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Token management
const TOKEN_KEY = 'teaching_pack_access_token';

export const getToken = (): string | null => {
  return localStorage.getItem(TOKEN_KEY);
};

export const setToken = (token: string): void => {
  localStorage.setItem(TOKEN_KEY, token);
};

export const removeToken = (): void => {
  localStorage.removeItem(TOKEN_KEY);
};

export const isAuthenticated = (): boolean => {
  return !!getToken();
};

export interface LessonSummary {
  title: string;
  subject: string;
  grade_level: string;
  key_concepts: string[];
  learning_objectives: string[];
  difficulty_level: string;
}

export interface Skill {
  skill_id: string;
  name: string;
  description: string;
  difficulty: number;
  prerequisites: string[];
}

export interface SkillSet {
  lesson_title: string;
  skills: Skill[];
  skill_graph: Record<string, string[]>;
}

export interface DiagnosticQuestion {
  question_id: string;
  skill_id: string;
  question_text: string;
  answer_key: string;
  difficulty: number;
  time_estimate: number;
}

export interface Diagnostic {
  title: string;
  questions: DiagnosticQuestion[];
  total_time: number;
  instructions: string;
}

export interface JobStatusResponse {
  job_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'completed_with_errors';
  message?: string;
  result?: any;
  error?: string;
}

export interface GeneratePacksResponse {
  job_id: string;
  status: string;
  message: string;
}

class ApiService {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  /**
   * Get authorization headers
   */
  private getAuthHeaders(): HeadersInit {
    const token = getToken();
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };
    
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    return headers;
  }

  /**
   * Get headers for file upload
   */
  private getFileUploadHeaders(): HeadersInit {
    const token = getToken();
    const headers: HeadersInit = {};
    
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    return headers;
  }

  /**
   * Login user
   */
  async login(email: string, password: string): Promise<{ access_token: string; token_type: string }> {
    const response = await fetch(`${this.baseUrl}/api/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Login failed');
    }

    const data = await response.json();
    setToken(data.access_token);
    return data;
  }

  /**
   * Register a new user
   */
  async register(email: string, password: string, full_name: string): Promise<{ id: number; email: string; full_name: string; role: string; is_active: boolean }> {
    const formData = new FormData();
    formData.append('email', email);
    formData.append('password', password);
    formData.append('full_name', full_name);

    const response = await fetch(`${this.baseUrl}/api/auth/register`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      console.error('Register error response:', error);
      
      // Handle FastAPI validation error format
      if (error.detail) {
        if (Array.isArray(error.detail)) {
          // Pydantic validation errors
          const messages = error.detail.map((err: { loc?: string[]; msg?: string }) => 
            err.msg || JSON.stringify(err)
          ).join(', ');
          throw new Error(messages);
        }
        throw new Error(error.detail);
      }
      throw new Error(JSON.stringify(error) || 'Registration failed');
    }

    return response.json();
  }

  /**
   * Logout user
   */
  logout(): void {
    removeToken();
  }

  /**
   * Get current user info
   */
  async getCurrentUser(): Promise<{ email: string; full_name: string; role: string }> {
    const response = await fetch(`${this.baseUrl}/api/auth/me`, {
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      if (response.status === 401) {
        removeToken();
      }
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get user info');
    }

    return response.json();
  }

  /**
   * Parse a lesson file
   */
  async parseLesson(file: File): Promise<{ lesson_summary: LessonSummary; job_id: string }> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${this.baseUrl}/api/lesson/parse`, {
      method: 'POST',
      headers: this.getFileUploadHeaders(),
      body: formData,
    });

    if (!response.ok) {
      if (response.status === 401) {
        removeToken();
        throw new Error('Authentication required. Please login again.');
      }
      const error = await response.json();
      throw new Error(error.detail || 'Failed to parse lesson');
    }

    return response.json();
  }

  /**
   * Map skills from lesson summary
   */
  async mapSkills(lessonSummary: LessonSummary): Promise<{ skill_set: SkillSet; job_id: string }> {
    const response = await fetch(`${this.baseUrl}/api/skills/map`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify(lessonSummary),
    });

    if (!response.ok) {
      if (response.status === 401) {
        removeToken();
        throw new Error('Authentication required. Please login again.');
      }
      const error = await response.json();
      throw new Error(error.detail || 'Failed to map skills');
    }

    return response.json();
  }

  /**
   * Build diagnostic assessment
   */
  async buildDiagnostic(skillSet: SkillSet): Promise<{ diagnostic: Diagnostic; job_id: string }> {
    const response = await fetch(`${this.baseUrl}/api/diagnostic/build`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify(skillSet),
    });

    if (!response.ok) {
      if (response.status === 401) {
        removeToken();
        throw new Error('Authentication required. Please login again.');
      }
      const error = await response.json();
      throw new Error(error.detail || 'Failed to build diagnostic');
    }

    return response.json();
  }

  /**
   * Generate Flashcards for a specific group in a Teaching Pack
   */
  async generatePackGroupFlashcards(teachingPackId: number, groupId: string) {
    const response = await fetch(`${this.baseUrl}/api/teaching-packs/${teachingPackId}/groups/${groupId}/flashcards`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      if (response.status === 401) {
        removeToken();
        throw new Error('Authentication required. Please login again.');
      }
      const error = await response.json();
      throw new Error(error.detail || 'Failed to generate group flashcards');
    }
    return response.json();
  }

  async getPackGroupFlashcards(teachingPackId: number, groupId: string) {
    const response = await fetch(`${this.baseUrl}/api/teaching-packs/${teachingPackId}/groups/${groupId}/flashcards`, {
      method: 'GET',
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
        // Handle 404 silently (return empty) or throw
        if (response.status === 404) return { groups: [] };
        if (response.status === 401) {
            removeToken();
            throw new Error('Authentication required.');
        }
        const error = await response.json();
        throw new Error(error.detail || 'Failed to get group flashcards');
    }
    return response.json();
  }

  /**
   * Generate complete teaching packs (full workflow)
   */
  async generateTeachingPacks(
    file: File,
    classroomId: number,
    numGroups: number = 4,
    numStudents: number = 30,
    studentListFile?: File | null
  ): Promise<GeneratePacksResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('classroom_id', classroomId.toString());
    formData.append('num_groups', numGroups.toString());
    formData.append('num_students', numStudents.toString());
    
    // Add student list file if provided
    if (studentListFile) {
      formData.append('student_list_file', studentListFile);
    }

    const response = await fetch(`${this.baseUrl}/api/packs/generate`, {
      method: 'POST',
      headers: this.getFileUploadHeaders(),
      body: formData,
    });

    if (!response.ok) {
      if (response.status === 401) {
        removeToken();
        throw new Error('Authentication required. Please login again.');
      }
      const error = await response.json();
      throw new Error(error.detail || 'Failed to generate teaching packs');
    }

    return response.json();
  }

  /**
   * Get job status
   */
  async getJobStatus(jobId: string): Promise<JobStatusResponse> {
    const response = await fetch(`${this.baseUrl}/api/jobs/${jobId}`, {
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      if (response.status === 401) {
        removeToken();
        throw new Error('Authentication required. Please login again.');
      }
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get job status');
    }

    return response.json();
  }

  /**
   * Poll job status until completion
   */
  async pollJobStatus(
    jobId: string,
    onProgress?: (status: JobStatusResponse) => void,
    pollInterval: number = 2000
  ): Promise<JobStatusResponse> {
    return new Promise((resolve, reject) => {
      const poll = async () => {
        try {
          const status = await this.getJobStatus(jobId);
          
          if (onProgress) {
            onProgress(status);
          }

          if (status.status === 'completed' || status.status === 'completed_with_errors') {
            resolve(status);
          } else if (status.status === 'failed') {
            reject(new Error(status.error || 'Job failed'));
          } else {
            // Continue polling
            setTimeout(poll, pollInterval);
          }
        } catch (error) {
          reject(error);
        }
      };

      poll();
    });
  }

  /**
   * Health check
   */
  async healthCheck(): Promise<{ status: string; gemini_api_configured: boolean }> {
    const response = await fetch(`${this.baseUrl}/health`);

    if (!response.ok) {
      throw new Error('Health check failed');
    }

    return response.json();
  }

  /**
   * Get output file content
   */
  async getOutputFile(filename: string): Promise<any> {
    const response = await fetch(`${this.baseUrl}/api/outputs/${filename}`);

    if (!response.ok) {
      throw new Error(`Failed to load output file: ${filename}`);
    }

    return response.json();
  }

  // ============= CLASSROOM MANAGEMENT =============

  /**
   * Get all classrooms for current user
   */
  async getClassrooms(): Promise<Classroom[]> {
    const response = await fetch(`${this.baseUrl}/api/classrooms`, {
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      throw new Error('Failed to fetch classrooms');
    }

    return response.json();
  }

  /**
   * Create a new classroom
   */
  async createClassroom(name: string, grade: string, subject: string, studentCount: number): Promise<Classroom> {
    const response = await fetch(`${this.baseUrl}/api/classrooms`, {
      method: 'POST',
      headers: {
        ...this.getAuthHeaders(),
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        name,
        grade,
        subject,
        student_count: studentCount.toString(),
      }),
    });

    if (!response.ok) {
      throw new Error('Failed to create classroom');
    }

    return response.json();
  }

  /**
   * Delete a classroom
   */
  async deleteClassroom(classroomId: number): Promise<void> {
    const response = await fetch(`${this.baseUrl}/api/classrooms/${classroomId}`, {
      method: 'DELETE',
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      throw new Error('Failed to delete classroom');
    }
  }

  /**
   * Update a classroom
   */
  async updateClassroom(classroomId: number, updates: { name?: string; grade?: string; subject?: string; student_count?: number }): Promise<Classroom> {
    const params = new URLSearchParams();
    if (updates.name) params.append('name', updates.name);
    if (updates.grade) params.append('grade', updates.grade);
    if (updates.subject) params.append('subject', updates.subject);
    if (updates.student_count !== undefined) params.append('student_count', updates.student_count.toString());

    const response = await fetch(`${this.baseUrl}/api/classrooms/${classroomId}`, {
      method: 'PUT',
      headers: {
        ...this.getAuthHeaders(),
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: params,
    });

    if (!response.ok) {
      throw new Error('Failed to update classroom');
    }

    return response.json();
  }

  /**
   * Get students in a classroom
   */
  async getClassroomStudents(classroomId: number): Promise<Student[]> {
    const response = await fetch(`${this.baseUrl}/api/classrooms/${classroomId}/students`, {
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      throw new Error('Failed to fetch classroom students');
    }

    return response.json();
  }

  /**
   * Add student to classroom
   */
  async addStudentToClassroom(classroomId: number, studentId: string, fullName: string, email: string): Promise<unknown> {
    const response = await fetch(`${this.baseUrl}/api/classrooms/${classroomId}/students`, {
      method: 'POST',
      headers: {
        ...this.getAuthHeaders(),
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        student_id: studentId,
        full_name: fullName,
        email,
      }),
    });

    if (!response.ok) {
      throw new Error('Failed to add student to classroom');
    }

    return response.json();
  }

  /**
   * Update student
   */
  async updateStudent(studentId: number, updates: { student_code?: string; full_name?: string; email?: string }): Promise<unknown> {
    const params = new URLSearchParams();
    if (updates.student_code) params.append('student_code', updates.student_code);
    if (updates.full_name) params.append('full_name', updates.full_name);
    if (updates.email) params.append('email', updates.email);

    const response = await fetch(`${this.baseUrl}/api/students/${studentId}`, {
      method: 'PUT',
      headers: {
        ...this.getAuthHeaders(),
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: params,
    });

    if (!response.ok) {
      throw new Error('Failed to update student');
    }

    return response.json();
  }

  /**
   * Get teaching packs for a specific classroom
   */
  async getClassroomTeachingPacks(classroomId: number): Promise<TeachingPackStatus[]> {
    const response = await fetch(`${this.baseUrl}/api/classrooms/${classroomId}/teaching-packs`, {
      method: 'GET',
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      throw new Error('Failed to fetch classroom teaching packs');
    }

    return response.json();
  }

  /**
   * Upload student list with scores and create groups
   */
  async uploadStudentsAndCreateGroups(
    classroomId: number,
    studentListFile: File,
    numGroups: number = 4
  ): Promise<GroupsData> {
    const formData = new FormData();
    formData.append('student_list_file', studentListFile);
    formData.append('num_groups', numGroups.toString());

    const response = await fetch(`${this.baseUrl}/api/classrooms/${classroomId}/upload-students-and-group`, {
      method: 'POST',
      headers: this.getFileUploadHeaders(),
      body: formData,
    });

    if (!response.ok) {
      if (response.status === 401) {
        removeToken();
        throw new Error('Authentication required. Please login again.');
      }
      const error = await response.json();
      throw new Error(error.detail || 'Failed to upload students and create groups');
    }

    return response.json();
  }

  /**
   * Create groups from existing students in classroom
   */
  async createGroupsFromExistingStudents(classroomId: number, numGroups: number = 4): Promise<GroupsData> {
    const response = await fetch(`${this.baseUrl}/api/classrooms/${classroomId}/create-groups`, {
      method: 'POST',
      headers: {
        ...this.getAuthHeaders(),
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        num_groups: numGroups.toString(),
      }),
    });

    if (!response.ok) {
      if (response.status === 401) {
        removeToken();
        throw new Error('Authentication required. Please login again.');
      }
      const error = await response.json();
      throw new Error(error.detail || 'Failed to create groups from existing students');
    }

    return response.json();
  }

  /**
   * Get groups configuration for a classroom
   */
  async getClassroomGroups(classroomId: number, packId?: number): Promise<GroupsData> {
    const url = new URL(`${this.baseUrl}/api/classrooms/${classroomId}/groups`);
    if (packId) {
      url.searchParams.append('pack_id', packId.toString());
    }
    const response = await fetch(url.toString(), {
      method: 'GET',
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      if (response.status === 401) {
        removeToken();
        throw new Error('Authentication required. Please login again.');
      }
      throw new Error('Failed to fetch classroom groups');
    }

    return response.json();
  }

  /**
   * Generate assets (slides, video) for a teaching pack
   */
  async generatePackAssets(
    teachingPackId: string | number,
    slidesContent: unknown,
    videoContent: unknown | null,
    generateVideo: boolean,
    generateSlides: boolean = true,
    groupId?: string
  ): Promise<{ job_id: string; status: string; message: string }> {
    const response = await fetch(`${this.baseUrl}/api/teaching-packs/${teachingPackId}/generate-assets`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify({
        slides_content: slidesContent,
        video_content: videoContent,
        generate_video: generateVideo,
        generate_slides: generateSlides,
        group_id: groupId
      }),
    });

    if (!response.ok) {
        if (response.status === 401) {
            removeToken();
            throw new Error('Authentication required. Please login again.');
        }
        const error = await response.json();
        throw new Error(error.detail || 'Failed to start asset generation');
    }

    return response.json();
  }

  /**
   * Draft content for teaching pack
   */
  async draftPackContent(
    teachingPackId: string | number,
    type: 'slides' | 'video'
  ): Promise<any> {
    const response = await fetch(`${this.baseUrl}/api/teaching-packs/${teachingPackId}/draft-content`, {
      method: 'POST',
      headers: {
        ...this.getAuthHeaders(),
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ type, id: Number(teachingPackId) }),
    });

    if (!response.ok) {
      if (response.status === 401) {
        removeToken();
        throw new Error('Authentication required. Please login again.');
      }
      const error = await response.json();
      throw new Error(error.detail || 'Failed to draft content');
    }

    return response.json();
  }

  /**
   * Submit teacher evaluation for a group
   */
  async submitGroupEvaluation(
    teachingPackId: string | number,
    groupId: string,
    payload: unknown
  ): Promise<any> {
    const response = await fetch(
      `${this.baseUrl}/api/teaching-packs/${teachingPackId}/groups/${groupId}/evaluation`,
      {
        method: 'POST',
        headers: {
          ...this.getAuthHeaders(),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      }
    );

    if (!response.ok) {
      if (response.status === 401) {
        removeToken();
        throw new Error('Authentication required. Please login again.');
      }
      const error = await response.json();
      throw new Error(error.detail || 'Failed to submit evaluation');
    }

    return response.json();
  }

  /**
   * Commit all teaching packs from a job as a single record
   */
  async commitAllTeachingPacks(jobId: string): Promise<{teaching_pack_id: number; status: string}> {
    const response = await fetch(`${this.baseUrl}/api/teaching-packs/commit-all`, {
      method: 'POST',
      headers: {
        ...this.getAuthHeaders(),
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ job_id: jobId }),
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to commit all teaching packs');
    }
    return response.json();
  }

  /**
   * Commit a preview teaching pack to database
   */
  async commitTeachingPack(jobId: string, groupId: string): Promise<{teaching_pack_id: number; status: string}> {
    // Only attempt if we have a valid jobId. 
    // If output was loaded from file list (not fresh gen), jobId might be missing or we need to derive it?
    // For now assume user flows from Generation.
    
    const response = await fetch(`${this.baseUrl}/api/teaching-packs/commit`, {
      method: 'POST',
       headers: {
        ...this.getAuthHeaders(),
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ job_id: jobId, group_id: groupId }),
    });
    
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to commit teaching pack');
    }
    return response.json();
  }

  /**
   * Download quiz as Word document
   */
  async downloadQuiz(packId: number, groupId: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/api/teaching-packs/download-quiz/${packId}?group_id=${groupId}`, {
      method: 'GET',
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to download quiz');
    }

    // Create download link
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `quiz_${packId}.docx`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  }

  // Flashcards
  async generateFlashcards(lessonId: number): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/api/lessons/${lessonId}/flashcards`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      throw new Error('Failed to generate flashcards');
    }
    return response.json();
  }

  async getFlashcards(lessonId: number): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/api/lessons/${lessonId}/flashcards`, {
      method: 'GET',
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      if (response.status === 404) return [];
      throw new Error('Failed to get flashcards');
    }
    return response.json();
  }

  // Theory Questions
  async generateTheoryQuestions(lessonId: number): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/api/lessons/${lessonId}/theory-questions`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      throw new Error('Failed to generate theory questions');
    }
    return response.json();
  }

  async getTheoryQuestions(lessonId: number): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/api/lessons/${lessonId}/theory-questions`, {
      method: 'GET',
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      if (response.status === 404) return { questions: [] };
      throw new Error('Failed to get theory questions');
    }
    return response.json();
  }
} // End of class ApiService

export const apiService = new ApiService();
export default apiService;
