import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { InternshipPosition } from './internship.service';

export interface InternProfile {
  id: string;
  full_name: string;
  email: string;
  phone?: string | null;
  avatar_url?: string | null;
  status: string;
}

export interface InternshipBrief {
  id: string;
  name: string;
  status: string;
  start_date?: string | null;
  end_date?: string | null;
}

export interface MentorBrief {
  id: string;
  full_name: string;
  email: string;
  phone?: string | null;
  avatar_url?: string | null;
}

export interface LearningContentProgress {
  id: string;
  title: string;
  type: string;
  order_no: number;
  progress_percent: number;
  status: string;
  completed_at?: string | null;
}

export interface RoadmapPhaseDetail {
  id: string;
  name: string;
  order_no: number;
  description?: string | null;
  contents: LearningContentProgress[];
}

export interface InternRoadmapDetail {
  roadmap_id?: string | null;
  roadmap_name?: string | null;
  description?: string | null;
  phases: RoadmapPhaseDetail[];
}

export interface QuizAttemptDetail {
  id: string;
  quiz_id: string;
  quiz_title: string;
  attempt_no: number;
  score?: number | null;
  passed?: boolean | null;
  grading_status?: 'AUTO_GRADED' | 'PENDING_GRADING' | 'GRADED';
  ungraded_questions?: number;
  started_at: string;
  submitted_at?: string | null;
}

export interface PendingQuizGradingItem {
  attempt_id: string;
  member_id: string;
  intern_id: string;
  intern_name: string;
  intern_email: string;
  quiz_id: string;
  quiz_title: string;
  attempt_no: number;
  submitted_at: string;
  ungraded_questions: number;
}

export interface QuizAttemptQuestionGradeView {
  question_id: string;
  content: string;
  type: string;
  max_score: number;
  order_no?: number | null;
  options: { key: string; text: string }[];
  correct_answer: unknown;
  selected_keys: string[];
  text?: string | null;
  is_correct?: boolean | null;
  earned_score?: number | null;
  feedback?: string | null;
  needs_manual_grading: boolean;
}

export interface QuizAttemptGradingDetail {
  attempt_id: string;
  quiz_id: string;
  quiz_title: string;
  pass_score: number;
  attempt_no: number;
  intern_name: string;
  score?: number | null;
  passed?: boolean | null;
  grading_status: 'AUTO_GRADED' | 'PENDING_GRADING' | 'GRADED';
  started_at: string;
  submitted_at?: string | null;
  questions: QuizAttemptQuestionGradeView[];
}

export interface QuizAttemptGradeRequest {
  grades: {
    question_id: string;
    earned_score: number;
    feedback?: string | null;
  }[];
}

export interface MentorAssignmentHistoryItem {
  action: 'ASSIGN' | 'CHANGE';
  member_id: string;
  intern_id: string;
  intern_name: string;
  old_mentor_id?: string | null;
  old_mentor_name?: string | null;
  new_mentor_id: string;
  new_mentor_name: string;
  changed_by_id: string;
  changed_by_name: string;
  changed_at: string;
  note?: string | null;
}

export interface MentorInternListItem {
  position?: InternshipPosition | null;
  id: string;
  intern_id: string;
  intern_name: string;
  intern_email: string;
  intern_phone?: string | null;
  intern_avatar_url?: string | null;
  internship_id: string;
  internship_name: string;
  roadmap_id?: string | null;
  roadmap_name?: string | null;
  mentor_id?: string | null;
  mentor_name?: string | null;
  status: string;
  start_date?: string | null;
  end_date?: string | null;
  progress_percent: number;
  quizzes_passed: number;
  pending_quiz_gradings?: number;
  tasks_completed: number;
  active_tasks: number;
}

export interface MentorInternDetail {
  position?: InternshipPosition | null;
  id: string;
  intern: InternProfile;
  internship: InternshipBrief;
  mentor?: MentorBrief | null;
  roadmap?: InternRoadmapDetail | null;
  learning_progress: LearningContentProgress[];
  quiz_attempts: QuizAttemptDetail[];
  assignment_history: MentorAssignmentHistoryItem[];
  start_date?: string | null;
  end_date?: string | null;
  status: string;
}

export interface MentorAssignRequestPayload {
  member_id: string;
  mentor_id: string;
  note?: string | null;
}

export interface MentorOverviewMetrics {
  total_interns: number;
  active_interns: number;
  completed_interns: number;
  avg_progress: number;
  total_quizzes_passed: number;
  pending_quiz_gradings?: number;
  recent_interns: MentorInternListItem[];
}

@Injectable({ providedIn: 'root' })
export class MentorService {
  private readonly http = inject(HttpClient);

  getOverview(): Observable<MentorOverviewMetrics> {
    return this.http.get<MentorOverviewMetrics>('/api/v1/mentor/overview', {});
  }

  getInterns(
    search?: string,
    status?: string,
    internshipId?: string,
  ): Observable<MentorInternListItem[]> {
    let params = new HttpParams();
    if (search && search.trim()) {
      params = params.set('search', search.trim());
    }
    if (status && status.trim()) {
      params = params.set('status', status.trim());
    }
    if (internshipId && internshipId.trim()) {
      params = params.set('internship_id', internshipId.trim());
    }

    return this.http.get<MentorInternListItem[]>('/api/v1/mentor/interns', {
      params,
    });
  }

  getInternDetail(memberId: string): Observable<MentorInternDetail> {
    return this.http.get<MentorInternDetail>(`/api/v1/mentor/interns/${memberId}`, {});
  }

  getInternRoadmap(memberId: string): Observable<InternRoadmapDetail> {
    return this.http.get<InternRoadmapDetail>(`/api/v1/mentor/interns/${memberId}/roadmap`, {});
  }

  getInternQuizzes(memberId: string): Observable<QuizAttemptDetail[]> {
    return this.http.get<QuizAttemptDetail[]>(`/api/v1/mentor/interns/${memberId}/quizzes`, {});
  }

  getPendingQuizAttempts(memberId?: string | null): Observable<PendingQuizGradingItem[]> {
    let params = new HttpParams();
    if (memberId) {
      params = params.set('member_id', memberId);
    }
    return this.http.get<PendingQuizGradingItem[]>('/api/v1/mentor/quiz-attempts/pending', {
      params,
    });
  }

  assignOrChangeMentor(
    payload: MentorAssignRequestPayload,
  ): Observable<MentorAssignmentHistoryItem> {
    return this.http.post<MentorAssignmentHistoryItem>('/api/v1/mentor/assignments', payload, {});
  }

  getAssignmentHistory(memberId?: string): Observable<MentorAssignmentHistoryItem[]> {
    let params = new HttpParams();
    if (memberId) {
      params = params.set('member_id', memberId);
    }
    return this.http.get<MentorAssignmentHistoryItem[]>('/api/v1/mentor/assignments/history', {
      params,
    });
  }

  createProposal(payload: InternshipProposalCreatePayload): Observable<InternshipProposalItem> {
    return this.http.post<InternshipProposalItem>('/api/v1/mentor/proposals', payload, {});
  }

  getMentorProposals(status?: string): Observable<InternshipProposalItem[]> {
    let params = new HttpParams();
    if (status && status.trim()) {
      params = params.set('status', status.trim());
    }
    return this.http.get<InternshipProposalItem[]>('/api/v1/mentor/proposals', {
      params,
    });
  }

  getInternStatusHistory(memberId: string): Observable<InternshipStatusHistoryItem[]> {
    return this.http.get<InternshipStatusHistoryItem[]>(
      `/api/v1/mentor/interns/${memberId}/status-history`,
      {},
    );
  }

  getQuizAttemptDetail(attemptId: string): Observable<QuizAttemptGradingDetail> {
    return this.http.get<QuizAttemptGradingDetail>(`/api/v1/mentor/quiz-attempts/${attemptId}`, {});
  }

  gradeQuizAttempt(
    attemptId: string,
    payload: QuizAttemptGradeRequest,
  ): Observable<QuizAttemptGradingDetail> {
    return this.http.post<QuizAttemptGradingDetail>(
      `/api/v1/mentor/quiz-attempts/${attemptId}/grade`,
      payload,
      {},
    );
  }
}

export interface InternshipProposalCreatePayload {
  member_id: string;
  type: 'EXTEND' | 'STOP' | 'COMPLETE' | 'TERMINATE';
  reason: string;
  requested_end_date?: string | null;
}

export interface InternshipStatusHistoryItem {
  id: string;
  action: string;
  from_status?: string | null;
  to_status: string;
  requested_by_name?: string | null;
  reviewed_by_name?: string | null;
  changed_at: string;
  reason?: string | null;
  review_note?: string | null;
  proposal_status?: string | null;
  requested_end_date?: string | null;
}

export interface InternshipProposalItem {
  id: string;
  internship_member_id: string;
  requested_by: string;
  type: string;
  reason: string;
  requested_end_date?: string | null;
  status: string;
  reviewed_by?: string | null;
  review_note?: string | null;
  created_at: string;
  reviewed_at?: string | null;
  intern_id?: string | null;
  intern_name?: string | null;
  intern_email?: string | null;
  mentor_name?: string | null;
  internship_id?: string | null;
  internship_name?: string | null;
}
