import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

export type InternshipStatus = 'DRAFT' | 'OPEN' | 'ONGOING' | 'COMPLETED' | 'CANCELLED';
export type MemberStatus = 'ACTIVE' | 'EXTENDED' | 'STOPPED' | 'COMPLETED';

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

export interface CreateInternshipPayload {
  name: string;
  description?: string | null;
  start_date: string;
  end_date: string;
  status?: InternshipStatus;
}

export interface UpdateInternshipPayload {
  name?: string;
  description?: string | null;
  start_date?: string;
  end_date?: string;
  status?: InternshipStatus;
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

  createInternship(payload: CreateInternshipPayload): Observable<Internship> {
    return this.http.post<Internship>('/api/v1/internships', payload, {});
  }

  getInternship(id: string): Observable<Internship> {
    return this.http.get<Internship>(`/api/v1/internships/${id}`, {});
  }

  updateInternship(id: string, payload: UpdateInternshipPayload): Observable<Internship> {
    return this.http.patch<Internship>(`/api/v1/internships/${id}`, payload, {});
  }

  getMembers(internshipId: string, search?: string): Observable<InternshipMember[]> {
    let params = new HttpParams();
    if (search && search.trim()) {
      params = params.set('search', search.trim());
    }
    return this.http.get<InternshipMember[]>(`/api/v1/internships/${internshipId}/members`, {
      params,
    });
  }

  addMember(internshipId: string, payload: AddMemberPayload): Observable<InternshipMember> {
    return this.http.post<InternshipMember>(
      `/api/v1/internships/${internshipId}/members`,
      payload,
      {},
    );
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
}
