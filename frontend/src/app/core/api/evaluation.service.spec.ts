import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { EvaluationService, previewTotal } from './evaluation.service';

describe('previewTotal', () => {
  it('khớp dữ liệu mẫu: 8,5×40% + 9×30% + 9×30% = 8,8', () => {
    expect(
      previewTotal([
        { score: 8.5, max_score: 10, weight: 40 },
        { score: 9, max_score: 10, weight: 30 },
        { score: 9, max_score: 10, weight: 30 },
      ]),
    ).toBe(8.8);
  });

  it('quy đổi thang điểm khác nhau và trọng số bất kỳ về thang 10', () => {
    expect(
      previewTotal([
        { score: 8, max_score: 10, weight: 3 },
        { score: 15, max_score: 20, weight: 2 },
      ]),
    ).toBe(7.8);
  });

  it('dùng trung bình cộng khi mọi trọng số bằng 0 và trả null khi chưa có điểm', () => {
    expect(previewTotal([{ score: 5, max_score: 10, weight: 0 }])).toBe(5);
    expect(previewTotal([])).toBeNull();
  });
});

describe('EvaluationService', () => {
  let service: EvaluationService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(EvaluationService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('gọi API tiêu chí với đúng phương thức', () => {
    service.listCriteria('ACTIVE').subscribe();
    const list = httpMock.expectOne('/api/v1/evaluation-criteria?status=ACTIVE');
    expect(list.request.method).toBe('GET');
    list.flush({ items: [], total_active_weight: 0 });

    const payload = {
      name: 'Chuyên môn',
      description: null,
      max_score: 10,
      weight: 40,
      status: 'ACTIVE' as const,
    };
    service.createCriterion(payload).subscribe();
    const create = httpMock.expectOne('/api/v1/evaluation-criteria');
    expect(create.request.method).toBe('POST');
    expect(create.request.body).toEqual(payload);
    create.flush({});

    service.updateCriterion('c1', { weight: 50 }).subscribe();
    const update = httpMock.expectOne('/api/v1/evaluation-criteria/c1');
    expect(update.request.method).toBe('PUT');
    expect(update.request.body).toEqual({ weight: 50 });
    update.flush({});

    service.deleteCriterion('c1').subscribe();
    const del = httpMock.expectOne('/api/v1/evaluation-criteria/c1');
    expect(del.request.method).toBe('DELETE');
    del.flush(null);
  });

  it('lọc danh sách đánh giá theo trạng thái, loại và thành viên', () => {
    service.listEvaluations({ status: 'DRAFT', type: 'FINAL', memberId: 'm1' }).subscribe();
    const request = httpMock.expectOne(
      (req) => req.url === '/api/v1/evaluations' && req.method === 'GET',
    );
    expect(request.request.params.get('status')).toBe('DRAFT');
    expect(request.request.params.get('evaluation_type')).toBe('FINAL');
    expect(request.request.params.get('member_id')).toBe('m1');
    request.flush([]);

    service.listEvaluations({ status: '' }).subscribe();
    const unfiltered = httpMock.expectOne('/api/v1/evaluations');
    expect(unfiltered.request.params.keys()).toEqual([]);
    unfiltered.flush([]);
  });

  it('lập nháp, sửa nháp và công bố đánh giá', () => {
    const draft = {
      internship_member_id: 'm1',
      evaluation_type: 'PERIODIC' as const,
      scores: [{ criterion_id: 'c1', score: 8 }],
      comment: 'Tốt',
    };
    service.createEvaluation(draft).subscribe();
    const create = httpMock.expectOne('/api/v1/evaluations');
    expect(create.request.method).toBe('POST');
    expect(create.request.body).toEqual(draft);
    create.flush({});

    service
      .updateEvaluation('e1', {
        evaluation_type: 'FINAL',
        scores: draft.scores,
        comment: null,
      })
      .subscribe();
    const update = httpMock.expectOne('/api/v1/evaluations/e1');
    expect(update.request.method).toBe('PUT');
    update.flush({});

    service.publishEvaluation('e1').subscribe();
    const publish = httpMock.expectOne('/api/v1/evaluations/e1/publish');
    expect(publish.request.method).toBe('POST');
    expect(publish.request.body).toEqual({});
    publish.flush({});
  });
});
