import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

export type RoadmapStatus = 'DRAFT' | 'ACTIVE' | 'ARCHIVED';
export type ContentType = 'LESSON' | 'DOCUMENT' | 'VIDEO' | 'LINK';
export type QuizStatus = 'DRAFT' | 'PUBLISHED';
export type QuestionType = 'SINGLE_CHOICE' | 'MULTIPLE_CHOICE' | 'TRUE_FALSE' | 'TEXT';

export interface Roadmap {
  id: string;
  name: string;
  description: string | null;
  status: RoadmapStatus;
  created_by: string | null;
  phase_count?: number;
  created_at: string;
  updated_at: string;
}

export interface Phase {
  id: string;
  roadmap_id: string;
  name: string;
  description: string | null;
  order_no: number;
  created_at: string;
  updated_at: string;
}

export interface LearningContent {
  id: string;
  phase_id: string;
  title: string;
  description: string | null;
  type: ContentType;
  content: string | null;
  resource_url: string | null;
  order_no: number;
  created_at: string;
  updated_at: string;
}

export interface Quiz {
  id: string;
  phase_id: string;
  title: string;
  description: string | null;
  duration_minutes: number;
  pass_score: number;
  max_attempts: number;
  status: QuizStatus;
  created_at: string;
  updated_at: string;
}

export interface Question {
  id: string;
  quiz_id: string;
  content: string;
  type: QuestionType;
  options: string | null;
  correct_answer: string | null;
  score: number;
  order_no: number;
  created_at: string;
}

export interface PhaseDetail extends Phase {
  contents: LearningContent[];
  quiz_count: number;
}

export interface RoadmapDetail extends Roadmap {
  phases: PhaseDetail[];
}

@Injectable({ providedIn: 'root' })
export class TrainingService {
  private readonly http = inject(HttpClient);

  private getHeaders(): HttpHeaders {
    const token = sessionStorage.getItem('itms_access_token');
    return new HttpHeaders(token ? { Authorization: `Bearer ${token}` } : {});
  }

  // ── Roadmaps ──────────────────────────────────────────────────────────────

  getRoadmaps(search?: string, status?: RoadmapStatus | ''): Observable<Roadmap[]> {
    let params = new HttpParams();
    if (search && search.trim()) {
      params = params.set('search', search.trim());
    }
    if (status) {
      params = params.set('status', status);
    }
    return this.http.get<Roadmap[]>('/api/v1/training/roadmaps', {
      headers: this.getHeaders(),
      params,
    });
  }

  createRoadmap(payload: {
    name: string;
    description?: string | null;
    status?: RoadmapStatus;
  }): Observable<Roadmap> {
    return this.http.post<Roadmap>('/api/v1/training/roadmaps', payload, {
      headers: this.getHeaders(),
    });
  }

  getRoadmap(id: string): Observable<RoadmapDetail> {
    return this.http.get<RoadmapDetail>(`/api/v1/training/roadmaps/${id}`, {
      headers: this.getHeaders(),
    });
  }

  updateRoadmap(
    id: string,
    payload: { name?: string; description?: string | null; status?: RoadmapStatus },
  ): Observable<Roadmap> {
    return this.http.patch<Roadmap>(`/api/v1/training/roadmaps/${id}`, payload, {
      headers: this.getHeaders(),
    });
  }

  deleteRoadmap(id: string): Observable<void> {
    return this.http.delete<void>(`/api/v1/training/roadmaps/${id}`, {
      headers: this.getHeaders(),
    });
  }

  // ── Phases ────────────────────────────────────────────────────────────────

  createPhase(payload: {
    roadmap_id: string;
    name: string;
    description?: string | null;
    order_no: number;
  }): Observable<Phase> {
    return this.http.post<Phase>('/api/v1/training/phases', payload, {
      headers: this.getHeaders(),
    });
  }

  updatePhase(
    id: string,
    payload: { name?: string; description?: string | null; order_no?: number },
  ): Observable<Phase> {
    return this.http.patch<Phase>(`/api/v1/training/phases/${id}`, payload, {
      headers: this.getHeaders(),
    });
  }

  deletePhase(id: string): Observable<void> {
    return this.http.delete<void>(`/api/v1/training/phases/${id}`, {
      headers: this.getHeaders(),
    });
  }

  // ── Learning Contents ─────────────────────────────────────────────────────

  getContents(phaseId: string): Observable<LearningContent[]> {
    return this.http.get<LearningContent[]>(`/api/v1/training/phases/${phaseId}/contents`, {
      headers: this.getHeaders(),
    });
  }

  createContent(payload: {
    phase_id: string;
    title: string;
    description?: string | null;
    type: ContentType;
    content?: string | null;
    resource_url?: string | null;
    order_no: number;
  }): Observable<LearningContent> {
    return this.http.post<LearningContent>('/api/v1/training/contents', payload, {
      headers: this.getHeaders(),
    });
  }

  updateContent(
    id: string,
    payload: {
      title?: string;
      description?: string | null;
      type?: ContentType;
      content?: string | null;
      resource_url?: string | null;
      order_no?: number;
    },
  ): Observable<LearningContent> {
    return this.http.patch<LearningContent>(`/api/v1/training/contents/${id}`, payload, {
      headers: this.getHeaders(),
    });
  }

  deleteContent(id: string): Observable<void> {
    return this.http.delete<void>(`/api/v1/training/contents/${id}`, {
      headers: this.getHeaders(),
    });
  }

  // ── Quizzes ───────────────────────────────────────────────────────────────

  getQuizzes(phaseId: string): Observable<Quiz[]> {
    return this.http.get<Quiz[]>(`/api/v1/training/phases/${phaseId}/quizzes`, {
      headers: this.getHeaders(),
    });
  }

  createQuiz(payload: {
    phase_id: string;
    title: string;
    description?: string | null;
    duration_minutes: number;
    pass_score: number;
    max_attempts: number;
  }): Observable<Quiz> {
    return this.http.post<Quiz>('/api/v1/training/quizzes', payload, {
      headers: this.getHeaders(),
    });
  }

  updateQuiz(
    id: string,
    payload: {
      title?: string;
      description?: string | null;
      duration_minutes?: number;
      pass_score?: number;
      max_attempts?: number;
    },
  ): Observable<Quiz> {
    return this.http.patch<Quiz>(`/api/v1/training/quizzes/${id}`, payload, {
      headers: this.getHeaders(),
    });
  }

  deleteQuiz(id: string): Observable<void> {
    return this.http.delete<void>(`/api/v1/training/quizzes/${id}`, {
      headers: this.getHeaders(),
    });
  }

  publishQuiz(id: string): Observable<Quiz> {
    return this.http.post<Quiz>(
      `/api/v1/training/quizzes/${id}/publish`,
      {},
      {
        headers: this.getHeaders(),
      },
    );
  }

  // ── Questions ─────────────────────────────────────────────────────────────

  getQuestions(quizId: string): Observable<Question[]> {
    return this.http.get<Question[]>(`/api/v1/training/quizzes/${quizId}/questions`, {
      headers: this.getHeaders(),
    });
  }

  createQuestion(payload: {
    quiz_id: string;
    content: string;
    type: QuestionType;
    options?: any;
    correct_answer?: any;
    score: number;
    order_no: number;
  }): Observable<Question> {
    return this.http.post<Question>('/api/v1/training/questions', payload, {
      headers: this.getHeaders(),
    });
  }

  updateQuestion(
    id: string,
    payload: {
      content?: string;
      type?: QuestionType;
      options?: any;
      correct_answer?: any;
      score?: number;
      order_no?: number;
    },
  ): Observable<Question> {
    return this.http.patch<Question>(`/api/v1/training/questions/${id}`, payload, {
      headers: this.getHeaders(),
    });
  }

  deleteQuestion(id: string): Observable<void> {
    return this.http.delete<void>(`/api/v1/training/questions/${id}`, {
      headers: this.getHeaders(),
    });
  }
}
