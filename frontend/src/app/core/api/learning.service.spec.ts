import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { LearningService } from './learning.service';

describe('LearningService', () => {
  let service: LearningService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(LearningService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('lấy lộ trình của Intern đang đăng nhập, không gửi mã Intern', () => {
    service.getRoadmap().subscribe();
    const request = httpMock.expectOne('/api/v1/learning/roadmap');
    expect(request.request.method).toBe('GET');
    request.flush({});
  });

  it('chỉ gửi sự kiện bắt đầu/hoàn thành, không gửi phần trăm tiến độ', () => {
    service.startContent('c1').subscribe();
    const start = httpMock.expectOne('/api/v1/learning/contents/c1/start');
    expect(start.request.method).toBe('POST');
    expect(start.request.body).toEqual({});
    start.flush({});

    service.completeContent('c1').subscribe();
    const complete = httpMock.expectOne('/api/v1/learning/contents/c1/complete');
    expect(complete.request.method).toBe('POST');
    expect(complete.request.body).toEqual({});
    complete.flush({});
  });

  it('bắt đầu và nộp một lượt làm bài', () => {
    service.startAttempt('q1').subscribe();
    httpMock.expectOne('/api/v1/learning/quizzes/q1/attempts').flush({});

    const answers = [{ question_id: 'x', selected_keys: ['A'], text: null }];
    service.submitAttempt('a1', answers).subscribe();
    const submit = httpMock.expectOne('/api/v1/learning/attempts/a1/submit');
    expect(submit.request.method).toBe('POST');
    expect(submit.request.body).toEqual({ answers });
    submit.flush({});
  });

  it('lấy kết quả các lần làm bài', () => {
    service.getQuizResults('q1').subscribe();
    httpMock.expectOne('/api/v1/learning/quizzes/q1/results').flush({});
  });
});
