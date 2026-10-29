import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

export type InternshipStatus = 'DRAFT' | 'OPEN' | 'ONGOING' | 'COMPLETED' | 'CANCELLED';
export type MemberStatus = 'ACTIVE' | 'EXTENDED' | 'STOPPED' | 'COMPLETED';
export type RequestType = 'EXTEND' | 'STOP' | 'COMPLETE';
export type RequestStatus = 'PENDING' | 'APPROVED' | 'REJECTED';
export type ApplicationStatus = 'PENDING' | 'APPROVED' | 'REJECTED';

export interface UserSummary {
  id: string;
  email: string;
  full_name: string;
  role: string;
}

export interface Internship {
  id: string;
  name: string;
  description: string | null;
  status: InternshipStatus;
  start_date: string;
  end_date: string;
  roadmap_id?: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
  creator?: UserSummary | null;
  members_count?: number;
}

export interface InternshipMember {
  id: string;
  internship_id: string;
  intern_id: string;
  mentor_id: string | null;
  roadmap_id: string | null;
  start_date: string | null;
  end_date: string | null;
  status: MemberStatus;
  created_at: string;
  updated_at: string;
  intern?: UserSummary | null;
  mentor?: UserSummary | null;
}

export interface InternshipRequest {
  id: string;
  internship_member_id: string;
  requested_by: string;
  type: RequestType;
  reason: string;
  requested_end_date?: string | null;
  status: RequestStatus;
  reviewed_by?: string | null;
  review_note?: string | null;
  created_at: string;
  reviewed_at?: string | null;
}

export interface InternshipApplication {
  id: string;
  internship_id: string;
  intern_id: string;
  status: ApplicationStatus;
  reason?: string | null;
  reviewed_by?: string | null;
  review_note?: string | null;
  created_at: string;
  reviewed_at?: string | null;
  internship_name?: string | null;
  intern_name?: string | null;
  intern_email?: string | null;
  reviewer_name?: string | null;
}

export interface CreateInternshipPayload {
  name: string;
  description?: string | null;
  start_date: string;
  end_date: string;
  status?: InternshipStatus;
  roadmap_id?: string | null;
}

export interface UpdateInternshipPayload {
  name?: string;
  description?: string | null;
  start_date?: string;
  end_date?: string;
  status?: InternshipStatus;
  roadmap_id?: string | null;
}

export interface CreateApplicationPayload {
  reason?: string | null;
}

export interface ReviewApplicationPayload {
  status: 'APPROVED' | 'REJECTED';
  review_note?: string | null;
}

export interface AddMemberPayload {
  intern_id: string;
  mentor_id?: string | null;
  roadmap_id?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  status?: MemberStatus;
}

export interface AssignMentorPayload {
  mentor_id: string | null;
}

export interface UpdateMemberPayload {
  intern_id?: string;
  mentor_id?: string | null;
  roadmap_id?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  status?: MemberStatus;
}

export interface ReviewRequestPayload {
  status: 'APPROVED' | 'REJECTED';
  review_note?: string | null;
}

export interface BatchResult {
  processed_count: number;
  message: string;
}

@Injectable({ providedIn: 'root' })
export class InternshipService {
  private readonly http = inject(HttpClient);

  getInternships(
    skip = 0,
    limit = 100,
    search?: string,
    status?: InternshipStatus | '',
  ): Observable<Internship[]> {
    let params = new HttpParams().set('skip', skip).set('limit', limit);
    if (search && search.trim()) {
      params = params.set('search', search.trim());
    }
    if (status) {
      params = params.set('status', status);
    }
    return this.http.get<Internship[]>('/api/v1/internships', {
      params,
    });
  }

  getOpenInternships(): Observable<Internship[]> {
    return this.http.get<Internship[]>('/api/v1/internships/open');
  }

  createInternship(payload: CreateInternshipPayload): Observable<Internship> {
    return this.http.post<Internship>('/api/v1/internships', payload, {});
  }

  getInternship(id: string): Observable<Internship> {
    return this.http.get<Internship>(`/api/v1/internships/${id}`, {});
  }

  updateInternship(id: string, payload: UpdateInternshipPayload): Observable<Internship> {
    return this.http.patch<Internship>(`/api/v1/internships/${id}`, payload, {});
  }

  // --- Intern Applications ---

  applyInternship(
    internshipId: string,
    payload: CreateApplicationPayload,
  ): Observable<InternshipApplication> {
    return this.http.post<InternshipApplication>(
      `/api/v1/internships/${internshipId}/apply`,
      payload,
    );
  }

  getMyApplications(): Observable<InternshipApplication[]> {
    return this.http.get<InternshipApplication[]>('/api/v1/internships/my-applications');
  }

  getApplications(
    status?: string,
    internshipId?: string,
    search?: string,
  ): Observable<InternshipApplication[]> {
    let params = new HttpParams();
    if (status) params = params.set('status', status);
    if (internshipId) params = params.set('internship_id', internshipId);
    if (search && search.trim()) params = params.set('search', search.trim());
    return this.http.get<InternshipApplication[]>('/api/v1/internships/applications', { params });
  }

  getApplication(appId: string): Observable<InternshipApplication> {
    return this.http.get<InternshipApplication>(`/api/v1/internships/applications/${appId}`);
  }

  reviewApplication(
    appId: string,
    payload: ReviewApplicationPayload,
  ): Observable<InternshipApplication> {
    return this.http.patch<InternshipApplication>(
      `/api/v1/internships/applications/${appId}/review`,
      payload,
    );
  }

  // --- Members ---

  getMembers(internshipId: string, search?: string): Observable<InternshipMember[]> {
    let params = new HttpParams();
    if (search && search.trim()) {
      params = params.set('search', search.trim());
    }
    return this.http.get<InternshipMember[]>(`/api/v1/internships/${internshipId}/members`, {
      params,
    });
  }

  getMember(memberId: string): Observable<InternshipMember> {
    return this.http.get<InternshipMember>(`/api/v1/internship-members/${memberId}`, {});
  }

  assignMentor(memberId: string, mentorId: string | null): Observable<InternshipMember> {
    return this.http.patch<InternshipMember>(
      `/api/v1/internship-members/${memberId}/mentor`,
      { mentor_id: mentorId },
      {},
    );
  }

  updateMember(memberId: string, payload: UpdateMemberPayload): Observable<InternshipMember> {
    return this.http.patch<InternshipMember>(`/api/v1/internship-members/${memberId}`, payload, {});
  }

  getUsers(role?: string): Observable<UserSummary[]> {
    let params = new HttpParams();
    if (role) {
      params = params.set('role', role);
    }
    return this.http.get<UserSummary[]>('/api/v1/users', {
      params,
    });
  }

  getRequests(
    status?: string,
    type?: string,
    startDate?: string,
    endDate?: string,
  ): Observable<InternshipRequest[]> {
    let params = new HttpParams();
    if (status) params = params.set('status', status);
    if (type) params = params.set('type', type);
    if (startDate) params = params.set('start_date', startDate);
    if (endDate) params = params.set('end_date', endDate);

    return this.http.get<InternshipRequest[]>('/api/v1/internships/requests', {
      params,
    });
  }

  reviewRequest(requestId: string, payload: ReviewRequestPayload): Observable<InternshipRequest> {
    return this.http.patch<InternshipRequest>(
      `/api/v1/internships/requests/${requestId}/review`,
      payload,
    );
  }

  batchReviewApplications(
    ids: string[],
    status: 'APPROVED' | 'REJECTED',
    review_note?: string | null,
  ): Observable<BatchResult> {
    return this.http.post<BatchResult>('/api/v1/internships/applications/batch-review', {
      ids,
      status,
      review_note,
    });
  }

  approveAllApplications(): Observable<BatchResult> {
    return this.http.post<BatchResult>('/api/v1/internships/applications/approve-all', {});
  }

  batchReviewRequests(
    ids: string[],
    status: 'APPROVED' | 'REJECTED',
    review_note?: string | null,
  ): Observable<BatchResult> {
    return this.http.post<BatchResult>('/api/v1/internships/requests/batch-review', {
      ids,
      status,
      review_note,
    });
  }

  approveAllRequests(): Observable<BatchResult> {
    return this.http.post<BatchResult>('/api/v1/internships/requests/approve-all', {});
  }
}
