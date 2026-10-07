import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

export type ProgressStatus = 'NOT_STARTED' | 'IN_PROGRESS' | 'COMPLETED';
export type LearningContentType = 'LESSON' | 'DOCUMENT' | 'VIDEO' | 'LINK';
export type LearningQuestionType = 'SINGLE_CHOICE' | 'MULTIPLE_CHOICE' | 'TRUE_FALSE' | 'TEXT';

export interface LearningContentItem {
  id: string;
  title: string;
  description: string | null;
  type: LearningContentType;
  resource_url: string | null;
  order_no: number;
  status: ProgressStatus;
  progress_percent: number;
  completed_at: string | null;
}

export interface LearningContentDetail extends LearningContentItem {
  phase_id: string;
  phase_name: string;
  content: string | null;
}

export interface LearningProgress {
  content_id: string;
  status: ProgressStatus;
  progress_percent: number;
  completed_at: string | null;
}

export interface LearningQuizSummary {
  id: string;
  title: string;
  description: string | null;
  duration_minutes: number;
  pass_score: number;
  max_attempts: number;
  status: 'PUBLISHED' | 'CLOSED';
  question_count: number;
  attempts_used: number;
  best_score: number | null;
  passed: boolean;
}

export interface LearningPhase {
  id: string;
  name: string;
  description: string | null;
  order_no: number;
  progress_percent: number;
  completed_contents: number;
  total_contents: number;
  contents: LearningContentItem[];
  quizzes: LearningQuizSummary[];
}

export interface LearningRoadmap {
  id: string;
  name: string;
  description: string | null;
  progress_percent: number;
  completed_contents: number;
  total_contents: number;
  phases: LearningPhase[];
}

export interface QuizOption {
  key: string;
  text: string;
}

/** Câu hỏi gửi cho Intern: backend không bao giờ kèm đáp án đúng. */
export interface QuizQuestion {
  id: string;
  content: string;
  type: LearningQuestionType;
  options: QuizOption[];
  score: number;
  order_no: number | null;
}

export interface AttemptStarted {
  attempt_id: string;
  quiz_id: string;
  quiz_title: string;
  attempt_no: number;
  started_at: string;
  expires_at: string;
  duration_minutes: number;
  resumed: boolean;
  questions: QuizQuestion[];
}

export interface AnswerPayload {
  question_id: string;
  selected_keys: string[];
  text: string | null;
}

export interface QuestionResult {
  question_id: string;
  /** null: câu hỏi chưa thể chấm tự động nên không tính vào điểm. */
  is_correct: boolean | null;
  earned_score: number;
}

export interface AttemptResult {
  attempt_id: string;
  quiz_id: string;
  attempt_no: number;
  score: number;
  passed: boolean;
  earned_points: number;
  total_points: number;
  ungraded_questions: number;
  started_at: string;
  submitted_at: string;
  questions: QuestionResult[];
}

export interface AttemptSummary {
  attempt_id: string;
  attempt_no: number;
  status: 'IN_PROGRESS' | 'SUBMITTED';
  score: number | null;
  passed: boolean | null;
  started_at: string;
  submitted_at: string | null;
}

export interface QuizResults {
  quiz_id: string;
  title: string;
  pass_score: number;
  max_attempts: number;
  attempts_used: number;
  best_score: number | null;
  passed: boolean;
  attempts: AttemptSummary[];
}

@Injectable({ providedIn: 'root' })
export class LearningService {
  private readonly http = inject(HttpClient);
  private readonly base = '/api/v1/learning';

  getRoadmap(): Observable<LearningRoadmap> {
    return this.http.get<LearningRoadmap>(`${this.base}/roadmap`);
  }

  getContent(contentId: string): Observable<LearningContentDetail> {
    return this.http.get<LearningContentDetail>(`${this.base}/contents/${contentId}`);
  }

  startContent(contentId: string): Observable<LearningProgress> {
    return this.http.post<LearningProgress>(`${this.base}/contents/${contentId}/start`, {});
  }

  completeContent(contentId: string): Observable<LearningProgress> {
    return this.http.post<LearningProgress>(`${this.base}/contents/${contentId}/complete`, {});
  }

  startAttempt(quizId: string): Observable<AttemptStarted> {
    return this.http.post<AttemptStarted>(`${this.base}/quizzes/${quizId}/attempts`, {});
  }

  submitAttempt(attemptId: string, answers: AnswerPayload[]): Observable<AttemptResult> {
    return this.http.post<AttemptResult>(`${this.base}/attempts/${attemptId}/submit`, { answers });
  }

  getQuizResults(quizId: string): Observable<QuizResults> {
    return this.http.get<QuizResults>(`${this.base}/quizzes/${quizId}/results`);
  }
}
