import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

export type CriterionStatus = 'ACTIVE' | 'INACTIVE';
export type EvaluationType = 'PERIODIC' | 'FINAL';
export type EvaluationStatus = 'DRAFT' | 'PUBLISHED';

export interface EvaluationCriterion {
  id: string;
  name: string;
  description: string | null;
  max_score: number;
  weight: number;
  status: CriterionStatus;
  created_at: string;
  updated_at: string;
}

export interface CriterionList {
  items: EvaluationCriterion[];
  total_active_weight: number;
}

export interface CriterionPayload {
  name: string;
  description: string | null;
  max_score: number;
  weight: number;
  status: CriterionStatus;
}

export interface EvaluationScore {
  criterion_id: string;
  name: string;
  max_score: number;
  weight: number;
  score: number;
}

export interface Evaluation {
  id: string;
  internship_member_id: string;
  intern_id: string;
  intern_name: string;
  internship_name: string | null;
  mentor_id: string;
  mentor_name: string | null;
  evaluation_type: EvaluationType;
  scores: EvaluationScore[];
  /** Thang 10, bình quân theo trọng số. null khi chưa chấm đủ tiêu chí. */
  total_score: number | null;
  comment: string | null;
  status: EvaluationStatus;
  published_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ScoreInput {
  criterion_id: string;
  score: number;
}

export interface EvaluationCreatePayload {
  internship_member_id: string;
  evaluation_type: EvaluationType;
  scores: ScoreInput[];
  comment: string | null;
}

export interface EvaluationUpdatePayload {
  evaluation_type: EvaluationType;
  scores: ScoreInput[];
  comment: string | null;
}

export interface EvaluationFilters {
  status?: EvaluationStatus | '';
  type?: EvaluationType | '';
  memberId?: string;
}

export const TOTAL_SCALE = 10;

/**
 * Tổng điểm tạm tính để xem trước khi chấm. Cùng công thức với backend:
 * Σ(điểm / điểm tối đa × trọng số) / Σ trọng số × 10. Kết quả chính thức do server tính.
 */
export function previewTotal(
  items: { score: number; max_score: number; weight: number }[],
): number | null {
  if (items.length === 0) return null;
  const weightSum = items.reduce((sum, item) => sum + item.weight, 0);
  const ratio =
    weightSum > 0
      ? items.reduce((sum, item) => sum + (item.score / item.max_score) * item.weight, 0) /
        weightSum
      : items.reduce((sum, item) => sum + item.score / item.max_score, 0) / items.length;
  return Math.round(ratio * TOTAL_SCALE * 100) / 100;
}

@Injectable({ providedIn: 'root' })
export class EvaluationService {
  private readonly http = inject(HttpClient);
  private readonly criteriaUrl = '/api/v1/evaluation-criteria';
  private readonly evaluationsUrl = '/api/v1/evaluations';

  listCriteria(status?: CriterionStatus | ''): Observable<CriterionList> {
    let params = new HttpParams();
    if (status) {
      params = params.set('status', status);
    }
    return this.http.get<CriterionList>(this.criteriaUrl, { params });
  }

  createCriterion(payload: CriterionPayload): Observable<EvaluationCriterion> {
    return this.http.post<EvaluationCriterion>(this.criteriaUrl, payload);
  }

  updateCriterion(id: string, payload: Partial<CriterionPayload>): Observable<EvaluationCriterion> {
    return this.http.put<EvaluationCriterion>(`${this.criteriaUrl}/${id}`, payload);
  }

  deleteCriterion(id: string): Observable<void> {
    return this.http.delete<void>(`${this.criteriaUrl}/${id}`);
  }

  listEvaluations(filters: EvaluationFilters = {}): Observable<Evaluation[]> {
    let params = new HttpParams();
    if (filters.status) {
      params = params.set('status', filters.status);
    }
    if (filters.type) {
      params = params.set('evaluation_type', filters.type);
    }
    if (filters.memberId) {
      params = params.set('member_id', filters.memberId);
    }
    return this.http.get<Evaluation[]>(this.evaluationsUrl, { params });
  }

  getEvaluation(id: string): Observable<Evaluation> {
    return this.http.get<Evaluation>(`${this.evaluationsUrl}/${id}`);
  }

  createEvaluation(payload: EvaluationCreatePayload): Observable<Evaluation> {
    return this.http.post<Evaluation>(this.evaluationsUrl, payload);
  }

  updateEvaluation(id: string, payload: EvaluationUpdatePayload): Observable<Evaluation> {
    return this.http.put<Evaluation>(`${this.evaluationsUrl}/${id}`, payload);
  }

  publishEvaluation(id: string): Observable<Evaluation> {
    return this.http.post<Evaluation>(`${this.evaluationsUrl}/${id}/publish`, {});
  }
}
