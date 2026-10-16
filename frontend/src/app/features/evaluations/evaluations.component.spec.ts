import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { provideNzIcons } from 'ng-zorro-antd/icon';

import { AuthService } from '../../core/api/auth.service';
import { Evaluation } from '../../core/api/evaluation.service';
import { EvaluationsComponent } from './evaluations.component';

function evaluation(overrides: Partial<Evaluation>): Evaluation {
  return {
    id: 'e1',
    internship_member_id: 'm1',
    intern_id: 'u1',
    intern_name: 'Nguyễn Intern',
    internship_name: 'Đợt thực tập 2026',
    mentor_id: 'u2',
    mentor_name: 'Trần Mentor',
    evaluation_type: 'PERIODIC',
    scores: [
      { criterion_id: 'c1', name: 'Chuyên môn', max_score: 10, weight: 40, score: 8.5 },
      { criterion_id: 'c2', name: 'Thái độ', max_score: 10, weight: 60, score: 9 },
    ],
    total_score: 8.8,
    comment: 'Chủ động, tiến bộ tốt',
    status: 'PUBLISHED',
    published_at: '2026-09-22T09:00:00Z',
    created_at: '2026-09-20T09:00:00Z',
    updated_at: '2026-09-22T09:00:00Z',
    ...overrides,
  };
}

describe('EvaluationsComponent', () => {
  let fixture: ComponentFixture<EvaluationsComponent>;
  let httpMock: HttpTestingController;

  function createAs(role: 'INTERN' | 'MENTOR' | 'ADMIN'): void {
    TestBed.inject(AuthService).storeSession({
      access_token: 'token',
      token_type: 'bearer',
      expires_in: 900,
      user: {
        id: '00000000-0000-0000-0000-000000000001',
        email: 'user@itms.local',
        full_name: 'Người dùng',
        role,
        avatar_url: null,
      },
    });
    fixture = TestBed.createComponent(EvaluationsComponent);
    fixture.detectChanges();
  }

  function text(): string {
    return (fixture.nativeElement as HTMLElement).textContent ?? '';
  }

  beforeEach(() => {
    sessionStorage.clear();
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideNoopAnimations(),
        provideNzIcons([]),
      ],
    });
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
    sessionStorage.clear();
  });

  it('Intern xem điểm, bảng tiêu chí và nhận xét của đánh giá đã công bố', () => {
    createAs('INTERN');
    httpMock.expectOne('/api/v1/evaluations').flush([evaluation({})]);
    fixture.detectChanges();

    expect(text()).toContain('Kết quả đánh giá');
    expect(text()).toContain('Đánh giá định kỳ');
    expect(text()).toContain('8.8');
    expect(text()).toContain('Chuyên môn');
    expect(text()).toContain('Chủ động, tiến bộ tốt');
    expect(text()).not.toContain('Lập đánh giá');
  });

  it('Intern chưa có đánh giá nào được công bố', () => {
    createAs('INTERN');
    httpMock.expectOne('/api/v1/evaluations').flush([]);
    fixture.detectChanges();

    expect(text()).toContain('Chưa có đánh giá nào được công bố cho bạn');
  });

  it('Mentor chỉ sửa và công bố được bản nháp, bản đã công bố chỉ để xem', () => {
    createAs('MENTOR');
    httpMock
      .expectOne('/api/v1/evaluations')
      .flush([
        evaluation({ id: 'draft', status: 'DRAFT', published_at: null, total_score: null }),
        evaluation({ id: 'pub', intern_name: 'Intern đã công bố' }),
      ]);
    fixture.detectChanges();

    expect(text()).toContain('Lập đánh giá');
    const rows = Array.from(
      (fixture.nativeElement as HTMLElement).querySelectorAll('tbody tr'),
    ) as HTMLElement[];
    const draftRow = rows.find((row) => row.textContent?.includes('Bản nháp'));
    const publishedRow = rows.find((row) => row.textContent?.includes('Intern đã công bố'));

    expect(draftRow?.textContent).toContain('Sửa');
    expect(draftRow?.textContent).toContain('Công bố');
    expect(draftRow?.textContent).toContain('Chưa chấm đủ');
    expect(publishedRow?.textContent).toContain('Xem');
    expect(publishedRow?.textContent).not.toContain('Sửa');
  });

  it('Admin giám sát đánh giá và quản lý tiêu chí, không có nút lập đánh giá', () => {
    createAs('ADMIN');
    httpMock.expectOne('/api/v1/evaluations').flush([evaluation({ status: 'DRAFT' })]);
    httpMock.expectOne('/api/v1/evaluation-criteria').flush({
      items: [
        {
          id: 'c1',
          name: 'Chuyên môn',
          description: null,
          max_score: 10,
          weight: 40,
          status: 'ACTIVE',
          created_at: '2026-09-01T00:00:00Z',
          updated_at: '2026-09-01T00:00:00Z',
        },
      ],
      total_active_weight: 40,
    });
    fixture.detectChanges();

    expect(text()).toContain('Tiêu chí đánh giá');
    expect(text()).toContain('Thêm tiêu chí');
    expect(text()).toContain('Tổng trọng số các tiêu chí đang áp dụng là 40%');
    expect(text()).not.toContain('Lập đánh giá');
  });

  it('Admin không thấy cảnh báo khi tổng trọng số bằng 100%', () => {
    createAs('ADMIN');
    httpMock.expectOne('/api/v1/evaluations').flush([]);
    httpMock
      .expectOne('/api/v1/evaluation-criteria')
      .flush({ items: [], total_active_weight: 100 });
    fixture.detectChanges();

    expect(text()).not.toContain('Tổng trọng số các tiêu chí đang áp dụng');
  });
});
