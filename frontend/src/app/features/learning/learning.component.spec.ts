import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { provideNzIcons } from 'ng-zorro-antd/icon';
import {
  CheckCircleOutline,
  FormOutline,
  ReadOutline,
  TrophyOutline,
  WarningOutline,
} from '@ant-design/icons-angular/icons';

import { LearningRoadmap } from '../../core/api/learning.service';
import { LearningComponent } from './learning.component';

const ROADMAP: LearningRoadmap = {
  id: 'r1',
  name: 'Lộ trình Full-stack 2026',
  description: 'Lộ trình nền tảng',
  progress_percent: 25,
  completed_contents: 1,
  total_contents: 2,
  phases: [
    {
      id: 'p1',
      name: 'Giai đoạn 1: Nền tảng',
      description: null,
      order_no: 1,
      progress_percent: 50,
      completed_contents: 1,
      total_contents: 2,
      contents: [
        {
          id: 'c1',
          title: 'Quy trình Git và GitHub',
          description: null,
          type: 'LESSON',
          resource_url: null,
          order_no: 1,
          status: 'NOT_STARTED',
          progress_percent: 0,
          completed_at: null,
        },
        {
          id: 'c2',
          title: 'Tài liệu SDLC',
          description: null,
          type: 'DOCUMENT',
          resource_url: 'https://docs.itms.local/sdlc',
          order_no: 2,
          status: 'COMPLETED',
          progress_percent: 100,
          completed_at: '2026-09-22T09:00:00Z',
        },
      ],
      quizzes: [
        {
          id: 'q1',
          title: 'Quiz kiến thức nền tảng',
          description: null,
          duration_minutes: 30,
          pass_score: 60,
          max_attempts: 2,
          status: 'PUBLISHED',
          question_count: 3,
          attempts_used: 1,
          best_score: 90,
          passed: true,
        },
      ],
    },
  ],
};

describe('LearningComponent', () => {
  let fixture: ComponentFixture<LearningComponent>;
  let httpMock: HttpTestingController;

  function create(view: string): void {
    fixture = TestBed.createComponent(LearningComponent);
    fixture.componentRef.setInput('view', view);
    fixture.detectChanges();
  }

  function text(): string {
    return (fixture.nativeElement as HTMLElement).textContent ?? '';
  }

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideNoopAnimations(),
        provideNzIcons([
          CheckCircleOutline,
          FormOutline,
          ReadOutline,
          TrophyOutline,
          WarningOutline,
        ]),
      ],
    });
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('hiển thị lộ trình, giai đoạn, nội dung và bài kiểm tra được giao', () => {
    create('roadmap');
    httpMock.expectOne('/api/v1/learning/roadmap').flush(ROADMAP);
    fixture.detectChanges();

    expect(text()).toContain('Lộ trình Full-stack 2026');
    expect(text()).toContain('Giai đoạn 1: Nền tảng');
    expect(text()).toContain('Quy trình Git và GitHub');
    expect(text()).toContain('Đã hoàn thành 1 trên 2 nội dung');
    expect(text()).toContain('Quiz kiến thức nền tảng');
  });

  it('hiển thị thông báo của server khi chưa được giao lộ trình', () => {
    create('roadmap');
    httpMock.expectOne('/api/v1/learning/roadmap').flush(
      {
        error: { code: 'ROADMAP_NOT_ASSIGNED', message: 'Bạn chưa được giao lộ trình đào tạo.' },
      },
      { status: 404, statusText: 'Not Found' },
    );
    fixture.detectChanges();

    expect(text()).toContain('Bạn chưa được giao lộ trình đào tạo.');
  });

  it('màn hình bài kiểm tra liệt kê điểm cao nhất và số lượt đã làm', () => {
    create('quizzes');
    httpMock.expectOne('/api/v1/learning/roadmap').flush(ROADMAP);
    fixture.detectChanges();

    expect(text()).toContain('Quiz kiến thức nền tảng');
    expect(text()).toContain('1/2');
    expect(text()).toContain('90');
  });

  it('màn hình tài liệu liệt kê mọi nội dung của lộ trình', () => {
    create('documents');
    httpMock.expectOne('/api/v1/learning/roadmap').flush(ROADMAP);
    fixture.detectChanges();

    expect(text()).toContain('Tài liệu SDLC');
    expect(text()).toContain('Mở tài liệu');
  });

  it('mở nội dung chưa học thì ghi nhận bắt đầu rồi làm mới tiến độ', () => {
    create('roadmap');
    httpMock.expectOne('/api/v1/learning/roadmap').flush(ROADMAP);
    fixture.detectChanges();

    const button = (fixture.nativeElement as HTMLElement).querySelector(
      '.rows .row button.link-btn',
    ) as HTMLButtonElement;
    button.click();

    httpMock.expectOne('/api/v1/learning/contents/c1').flush({
      ...ROADMAP.phases[0].contents[0],
      phase_id: 'p1',
      phase_name: 'Giai đoạn 1: Nền tảng',
      content: 'Nội dung bài học',
    });
    const start = httpMock.expectOne('/api/v1/learning/contents/c1/start');
    expect(start.request.method).toBe('POST');
    start.flush({
      content_id: 'c1',
      status: 'IN_PROGRESS',
      progress_percent: 0,
      completed_at: null,
    });
    httpMock.expectOne('/api/v1/learning/roadmap').flush(ROADMAP);
  });
});
