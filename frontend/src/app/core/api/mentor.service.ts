import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

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
  started_at: string;
  submitted_at?: string | null;
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
  tasks_completed: number;
  active_tasks: number;
}

export interface MentorInternDetail {
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
}
