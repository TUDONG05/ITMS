import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

export type TaskStatus =
  | 'TODO'
  | 'SUBMITTED'
  | 'REVISION_REQUIRED'
  | 'COMPLETED'
  | 'CANCELLED';
export type TaskPriority = 'LOW' | 'MEDIUM' | 'HIGH';

export interface Task {
  id: string;
  internship_member_id: string;
  created_by: string;
  title: string;
  description?: string | null;
  deadline?: string | null;
  priority?: string | null;
  attachment_url?: string | null;
  status: TaskStatus;
  created_at: string;
  updated_at: string;
  intern_name?: string | null;
  internship_name?: string | null;
  submissions_count: number;
  comments_count: number;
  is_overdue: boolean;
  is_late_submission: boolean;
}

export interface TaskSubmission {
  id: string;
  task_id: string;
  content?: string | null;
  file_url?: string | null;
  status: string;
  review_comment?: string | null;
  reviewed_by?: string | null;
  submitted_at: string;
  reviewed_at?: string | null;
  is_late: boolean;
}

export interface TaskComment {
  id: string;
  task_id: string;
  user_id: string;
  author_name?: string | null;
  author_role?: string | null;
  content: string;
  created_at: string;
}

export interface TaskDetail extends Task {
  submissions: TaskSubmission[];
  comments: TaskComment[];
}

export interface TaskFilters {
  member_id?: string;
  status?: string;
  priority?: string;
  overdue?: boolean;
  search?: string;
  internship_id?: string;
}

@Injectable({ providedIn: 'root' })
export class TaskService {
  private readonly http = inject(HttpClient);

  private getHeaders(): HttpHeaders {
    const token = sessionStorage.getItem('itms_access_token');
    return new HttpHeaders(token ? { Authorization: `Bearer ${token}` } : {});
  }

  getTasks(filters: TaskFilters = {}): Observable<Task[]> {
    let params = new HttpParams();
    if (filters.member_id) params = params.set('member_id', filters.member_id);
    if (filters.status) params = params.set('status', filters.status);
    if (filters.priority) params = params.set('priority', filters.priority);
    if (filters.overdue !== undefined) params = params.set('overdue', String(filters.overdue));
    if (filters.search?.trim()) params = params.set('search', filters.search.trim());
    if (filters.internship_id) params = params.set('internship_id', filters.internship_id);
    return this.http.get<Task[]>('/api/v1/tasks', { headers: this.getHeaders(), params });
  }

  getTask(id: string): Observable<TaskDetail> {
    return this.http.get<TaskDetail>(`/api/v1/tasks/${id}`, { headers: this.getHeaders() });
  }

  createTask(payload: {
    internship_member_id: string;
    title: string;
    description?: string | null;
    deadline?: string | null;
    priority?: TaskPriority;
    attachment_url?: string | null;
  }): Observable<Task> {
    return this.http.post<Task>('/api/v1/tasks', payload, { headers: this.getHeaders() });
  }

  updateTask(
    id: string,
    payload: { title?: string; description?: string | null; deadline?: string | null; priority?: string; status?: string; attachment_url?: string | null },
  ): Observable<Task> {
    return this.http.patch<Task>(`/api/v1/tasks/${id}`, payload, { headers: this.getHeaders() });
  }

  cancelTask(id: string): Observable<Task> {
    return this.http.delete<Task>(`/api/v1/tasks/${id}`, { headers: this.getHeaders() });
  }

  submitTask(id: string, payload: { content?: string | null; link?: string | null; attachment_url?: string | null }): Observable<TaskSubmission> {
    return this.http.post<TaskSubmission>(`/api/v1/tasks/${id}/submit`, payload, {
      headers: this.getHeaders(),
    });
  }

  deleteSubmission(id: string): Observable<void> {
    return this.http.delete<void>(`/api/v1/tasks/${id}/submission`, {
      headers: this.getHeaders(),
    });
  }

  reviewTask(id: string, payload: { decision: 'COMPLETED' | 'REVISION_REQUIRED'; review_comment?: string | null }): Observable<TaskSubmission> {
    return this.http.post<TaskSubmission>(`/api/v1/tasks/${id}/review`, payload, {
      headers: this.getHeaders(),
    });
  }

  addComment(id: string, content: string): Observable<TaskComment> {
    return this.http.post<TaskComment>(
      `/api/v1/tasks/${id}/comments`,
      { content },
      { headers: this.getHeaders() },
    );
  }

  uploadFiles(files: File[]): Observable<{ urls: string[] }> {
    const formData = new FormData();
    for (const file of files) {
      formData.append('files', file, file.name);
    }
    // Không set Content-Type — browser tự gắn boundary
    const token = sessionStorage.getItem('itms_access_token');
    const headers = new HttpHeaders(token ? { Authorization: `Bearer ${token}` } : {});
    return this.http.post<{ urls: string[] }>('/api/v1/tasks/upload', formData, { headers });
  }
}
