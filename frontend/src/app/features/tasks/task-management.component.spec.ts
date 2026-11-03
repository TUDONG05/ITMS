import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { DeleteOutline, EditOutline, PlusOutline } from '@ant-design/icons-angular/icons';
import { provideNzIcons } from 'ng-zorro-antd/icon';
import { NzMessageService } from 'ng-zorro-antd/message';

import { AuthService } from '../../core/api/auth.service';
import { MentorInternListItem } from '../../core/api/mentor.service';
import { Task, TaskDetail, TaskSubmission } from '../../core/api/task.service';
import { TaskManagementComponent } from './task-management.component';

describe('TaskManagementComponent assignment', () => {
  let component: TaskManagementComponent;
  let fixture: ComponentFixture<TaskManagementComponent>;
  let role: 'MENTOR' | 'INTERN';
  let httpMock: HttpTestingController;
  const messages = { success: vi.fn(), error: vi.fn(), warning: vi.fn() };

  const interns = [
    { id: 'm1', intern_name: 'Intern A', internship_id: 'p1', internship_name: 'Đợt 1' },
    { id: 'm2', intern_name: 'Intern B', internship_id: 'p1', internship_name: 'Đợt 1' },
    { id: 'm3', intern_name: 'Intern C', internship_id: 'p2', internship_name: 'Đợt 2' },
  ] as MentorInternListItem[];

  function taskDetail(overrides: Partial<TaskDetail> = {}): TaskDetail {
    return {
      id: 'shared-task',
      assignment_mode: 'GROUP',
      internship_member_ids: ['m1', 'm2'],
      assignees: interns.slice(0, 2).map((intern, index) => ({
        internship_member_id: intern.id,
        intern_id: `u${index + 1}`,
        intern_name: intern.intern_name,
        internship_id: intern.internship_id,
        internship_name: intern.internship_name,
        status: 'TODO' as const,
      })),
      title: 'Task chung',
      created_by: 'mentor',
      status: 'TODO',
      created_at: '2026-11-01T10:00:00Z',
      updated_at: '2026-11-01T10:00:00Z',
      submissions_count: 0,
      comments_count: 0,
      is_overdue: false,
      is_late_submission: false,
      submissions: [],
      comments: [],
      ...overrides,
    };
  }

  function submission(
    memberId: string | null,
    overrides: Partial<TaskSubmission> = {},
  ): TaskSubmission {
    return {
      id: `submission-${memberId}`,
      task_id: 'shared-task',
      internship_member_id: memberId,
      intern_name: memberId === 'm1' ? 'Intern A' : 'Intern B',
      content: `Content for ${memberId}`,
      status: 'SUBMITTED',
      submitted_at: '2026-11-01T10:00:00Z',
      is_late: false,
      ...overrides,
    };
  }

  async function renderDetail(task: TaskDetail): Promise<HTMLElement> {
    fixture.detectChanges();
    httpMock.expectOne('/api/v1/tasks').flush([task]);
    httpMock.expectOne((req) => req.url === '/api/v1/internships').flush([]);
    if (role === 'MENTOR') httpMock.expectOne('/api/v1/mentor/interns').flush(interns);
    await fixture.whenStable();
    component['openDetail'](task.id);
    httpMock.expectOne(`/api/v1/tasks/${task.id}`).flush(task);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    return document.querySelector('.ant-drawer-body') as HTMLElement;
  }

  function prepare(memberIds = ['m1', 'm2']): void {
    component['openCreate']();
    component['form'].update((form) => ({
      ...form,
      internship_member_ids: memberIds,
      title: '  API đăng nhập  ',
      description: '  Kiểm tra đăng nhập  ',
      deadline: '2026-12-01T10:00',
      priority: 'HIGH',
      attachment_url: '/api/v1/uploads/tasks/spec.pdf',
    }));
  }

  function flushReload(): void {
    httpMock.expectOne((req) => req.method === 'GET' && req.url === '/api/v1/tasks').flush([]);
  }

  beforeEach(() => {
    vi.clearAllMocks();
    role = 'MENTOR';
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideNoopAnimations(),
        provideNzIcons([PlusOutline, EditOutline, DeleteOutline]),
        { provide: AuthService, useValue: { currentUser: () => ({ id: 'u1', role }) } },
        { provide: NzMessageService, useValue: messages },
      ],
    });
    httpMock = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(TaskManagementComponent);
    component = fixture.componentInstance;
    component['interns'].set(interns);
  });

  afterEach(() => httpMock.verify());

  it('creates one shared task with all selected recipients in a single request', () => {
    prepare();
    component['saveForm']();
    const request = httpMock.expectOne(
      (req) => req.method === 'POST' && req.url === '/api/v1/tasks',
    );
    expect(request.request.body).toEqual({
      internship_member_ids: ['m1', 'm2'],
      assignment_mode: 'GROUP',
      title: 'API đăng nhập',
      description: 'Kiểm tra đăng nhập',
      deadline: new Date('2026-12-01T10:00').toISOString(),
      priority: 'HIGH',
      attachment_url: '/api/v1/uploads/tasks/spec.pdf',
    });
    request.flush({ id: 'shared-task', internship_member_ids: ['m1', 'm2'] });
    flushReload();
    expect(component['isFormOpen']()).toBe(false);
    expect(component['isSaving']()).toBe(false);
    expect(messages.success).toHaveBeenCalled();
  });

  it('creates an individual task for all selected interns in one request with the selected mode', () => {
    prepare();
    component['form'].update((form) => ({ ...form, assignment_mode: 'INDIVIDUAL' }));
    component['saveForm']();
    const request = httpMock.expectOne((req) => req.method === 'POST');
    expect(request.request.body.assignment_mode).toBe('INDIVIDUAL');
    expect(request.request.body.internship_member_ids).toEqual(['m1', 'm2']);
    request.flush(taskDetail({ assignment_mode: 'INDIVIDUAL' }));
    flushReload();
    expect(component['isFormOpen']()).toBe(false);
  });

  it('offers both assignment modes when creating and resets to GROUP for a new task', async () => {
    fixture.detectChanges();
    httpMock.expectOne('/api/v1/tasks').flush([]);
    httpMock.expectOne((req) => req.url === '/api/v1/internships').flush([]);
    httpMock.expectOne('/api/v1/mentor/interns').flush(interns);
    prepare();
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    const choices = document.querySelectorAll('.ant-modal-body input[type="radio"]');
    expect(choices).toHaveLength(2);
    (choices[1] as HTMLInputElement).click();
    fixture.detectChanges();
    expect(component['form']().assignment_mode).toBe('INDIVIDUAL');
    component['openCreate']();
    expect(component['form']().assignment_mode).toBe('GROUP');
  });

  it('filters intern options by internship and drops selections outside that internship', () => {
    prepare(['m1', 'm3']);
    component['onAssignmentInternshipChange']('p1');
    expect(component['assignmentInterns']().map((intern) => intern.id)).toEqual(['m1', 'm2']);
    expect(component['form']().internship_member_ids).toEqual(['m1']);
    component['onAssignmentInternshipChange'](null);
    expect(component['assignmentInterns']()).toEqual(interns);
    expect(component['form']().internship_member_ids).toEqual(['m1']);
    component['onAssignmentInternshipChange']('empty');
    expect(component['assignmentInterns']()).toEqual([]);
    expect(component['form']().internship_member_ids).toEqual([]);
  });

  it('initializes the assignment filter from the task list and resets selections for a new form', () => {
    prepare(['m3']);
    component['internshipFilter'].set('p1');
    component['openCreate']();
    expect(component['assignmentInternshipFilter']()).toBe('p1');
    expect(component['assignmentInterns']().map((intern) => intern.id)).toEqual(['m1', 'm2']);
    expect(component['form']().internship_member_ids).toEqual([]);
  });

  it('requires a recipient and a nonblank title before creating tasks', () => {
    prepare([]);
    component['saveForm']();
    expect(messages.warning).toHaveBeenCalledWith('Vui lòng chọn intern nhận task');
    prepare();
    component['form'].update((form) => ({ ...form, title: '   ' }));
    component['saveForm']();
    expect(messages.warning).toHaveBeenCalledWith('Vui lòng nhập tiêu đề task');
    httpMock.expectNone((req) => req.method === 'POST');
    expect(component['isSaving']()).toBe(false);
  });

  it('retains every recipient after a failed request and retries the entire shared task once', () => {
    prepare();
    component['saveForm']();
    const request = httpMock.expectOne((req) => req.method === 'POST');
    request.flush({ detail: 'Unavailable' }, { status: 503, statusText: 'Unavailable' });
    expect(component['isFormOpen']()).toBe(true);
    expect(component['form']().internship_member_ids).toEqual(['m1', 'm2']);
    expect(component['isSaving']()).toBe(false);
    expect(messages.error).toHaveBeenCalled();
    expect(messages.success).not.toHaveBeenCalled();
    httpMock.expectNone((req) => req.method === 'GET');
    component['saveForm']();
    const retry = httpMock.expectOne((req) => req.method === 'POST');
    expect(retry.request.body.internship_member_ids).toEqual(['m1', 'm2']);
    retry.flush({ id: 'shared-task' });
    flushReload();
    expect(component['isFormOpen']()).toBe(false);
  });

  it('prevents duplicate saves while the single creation request is pending and deduplicates recipient ids', () => {
    prepare(['m1', 'm1', 'm2']);
    component['saveForm']();
    component['saveForm']();
    const request = httpMock.expectOne((req) => req.method === 'POST');
    expect(request.request.body.internship_member_ids).toEqual(['m1', 'm2']);
    expect(component['isSaving']()).toBe(true);
    request.flush({ id: 'shared-task' });
    flushReload();
    expect(component['isSaving']()).toBe(false);
  });

  it('waits for attachment upload to finish before saving', () => {
    prepare();
    component['isUploading'].set(true);
    component['saveForm']();
    httpMock.expectNone((req) => req.method === 'POST');
    expect(component['isSaving']()).toBe(false);
  });

  it('sends a larger recipient group in one shared task request', () => {
    prepare(['m1', 'm2', 'm3', 'm4', 'm5']);
    component['saveForm']();
    const request = httpMock.expectOne((req) => req.method === 'POST');
    expect(request.request.body.internship_member_ids).toEqual(['m1', 'm2', 'm3', 'm4', 'm5']);
    request.flush({ id: 'shared-task' });
    flushReload();
    expect(component['isFormOpen']()).toBe(false);
  });

  it('updates an existing task with one PATCH without reassigning it', () => {
    component['openEdit']({
      id: 'existing',
      assignment_mode: 'GROUP',
      internship_member_ids: ['m1', 'm2'],
      assignees: [],
      title: 'Task cũ',
      priority: 'MEDIUM',
      created_by: 'mentor',
      status: 'TODO',
      created_at: '2026-11-01T10:00:00Z',
      updated_at: '2026-11-01T10:00:00Z',
      submissions_count: 0,
      comments_count: 0,
      is_overdue: false,
      is_late_submission: false,
    } as Task);
    component['form'].update((form) => ({ ...form, title: 'Task mới' }));
    component['saveForm']();
    const patch = httpMock.expectOne('/api/v1/tasks/existing');
    expect(patch.request.method).toBe('PATCH');
    expect(patch.request.body.title).toBe('Task mới');
    expect(patch.request.body.internship_member_id).toBeUndefined();
    expect(patch.request.body.internship_member_ids).toBeUndefined();
    expect(patch.request.body.assignment_mode).toBeUndefined();
    patch.flush({ id: 'existing' });
    flushReload();
    httpMock.expectNone((req) => req.method === 'POST');
    expect(component['isFormOpen']()).toBe(false);
  });

  for (const viewerRole of ['MENTOR', 'INTERN'] as const) {
    it(`shows all assignees on the list and detail for ${viewerRole}`, async () => {
      role = viewerRole;
      const task: TaskDetail = {
        id: 'shared-task',
        assignment_mode: 'GROUP',
        internship_member_ids: ['m1', 'm2'],
        assignees: [
          {
            internship_member_id: 'm1',
            intern_id: 'u1',
            intern_name: 'Intern A',
            internship_id: 'p1',
            internship_name: 'Đợt 1',
            status: 'TODO',
          },
          {
            internship_member_id: 'm2',
            intern_id: 'u2',
            intern_name: 'Intern B',
            internship_id: 'p1',
            internship_name: 'Đợt 1',
            status: 'TODO',
          },
        ],
        created_by: 'mentor',
        title: 'Task chung',
        status: 'TODO',
        created_at: '2026-11-01T10:00:00Z',
        updated_at: '2026-11-01T10:00:00Z',
        submissions_count: 0,
        comments_count: 0,
        is_overdue: false,
        is_late_submission: false,
        submissions: [],
        comments: [],
      };
      fixture.detectChanges();
      httpMock.expectOne('/api/v1/tasks').flush([task]);
      httpMock.expectOne((req) => req.url === '/api/v1/internships').flush([]);
      if (viewerRole === 'MENTOR') {
        httpMock.expectOne('/api/v1/mentor/interns').flush(interns);
      }
      await fixture.whenStable();
      fixture.detectChanges();
      const list = (fixture.nativeElement as HTMLElement).querySelector('tbody');
      expect(list?.textContent).toContain('Intern A');
      expect(list?.textContent).toContain('Intern B');
      expect(list?.querySelectorAll('tr')).toHaveLength(1);

      component['openDetail']('shared-task');
      httpMock.expectOne('/api/v1/tasks/shared-task').flush(task);
      fixture.detectChanges();
      await fixture.whenStable();
      fixture.detectChanges();
      const drawer = document.querySelector('.ant-drawer-body');
      expect(drawer?.textContent).toContain('Intern A');
      expect(drawer?.textContent).toContain('Intern B');
      component['closeDetail']();
      fixture.detectChanges();
    });
  }

  it('uses the current intern assignment status and shows only their submission with edit/delete actions', async () => {
    role = 'INTERN';
    const task = taskDetail({
      assignment_mode: 'INDIVIDUAL',
      status: 'SUBMITTED',
      submissions: [submission('m1'), submission('m2')],
    });
    task.assignees[0].status = 'REVISION_REQUIRED';
    task.assignees[1].status = 'SUBMITTED';
    const drawer = await renderDetail(task);
    expect(component['taskStatus'](task)).toBe('REVISION_REQUIRED');
    expect(component['visibleSubmissions'](task).map((item) => item.internship_member_id)).toEqual([
      'm1',
    ]);
    expect(drawer.textContent).toContain('Content for m1');
    expect(drawer.textContent).not.toContain('Content for m2');
    const actions = drawer.querySelector('.submission-actions');
    expect(actions?.textContent).toContain('Sửa bài nộp');
    expect(actions?.textContent).toContain('Xóa');
    component['closeDetail']();
    fixture.detectChanges();
  });

  for (const globalStatus of ['TODO', 'SUBMITTED'] as const) {
    it(`hides submission forms and editing when the intern completed an individual task whose global status is ${globalStatus}`, async () => {
      role = 'INTERN';
      const task = taskDetail({
        assignment_mode: 'INDIVIDUAL',
        status: globalStatus,
        submissions: [submission('m1', { status: 'ACCEPTED' })],
      });
      task.assignees[0].status = 'COMPLETED';
      const drawer = await renderDetail(task);
      expect(component['taskStatus'](task)).toBe('COMPLETED');
      expect(drawer.querySelector('.submission-actions')).toBeNull();
      expect(drawer.querySelector('textarea[placeholder="Nội dung bài làm..."]')).toBeNull();
      expect(drawer.querySelector('.submission-form-actions')).toBeNull();
      component['closeDetail']();
      fixture.detectChanges();
    });
  }

  it('targets the selected intern when a mentor reviews an individual task', () => {
    const task = taskDetail({
      assignment_mode: 'INDIVIDUAL',
      status: 'SUBMITTED',
      submissions: [submission('m1'), submission('m2')],
    });
    task.assignees.forEach((assignee) => (assignee.status = 'SUBMITTED'));
    component['detail'].set(task);
    component['reviewMemberId'].set('m2');
    component['reviewDecision'].set('REVISION_REQUIRED');
    component['reviewComment'].set('  Rework B  ');
    component['reviewWork']();
    const request = httpMock.expectOne('/api/v1/tasks/shared-task/review');
    expect(request.request.body).toEqual({
      decision: 'REVISION_REQUIRED',
      review_comment: 'Rework B',
      internship_member_id: 'm2',
    });
    request.flush(submission('m2', { status: 'REVISION_REQUIRED' }));
    flushReload();
    httpMock.expectOne('/api/v1/tasks/shared-task').flush(task);
  });

  it('requires a member target for individual reviews and excludes completed submissions from targets', () => {
    const task = taskDetail({
      assignment_mode: 'INDIVIDUAL',
      status: 'SUBMITTED',
      submissions: [submission('m1', { status: 'ACCEPTED' }), submission('m2')],
    });
    component['detail'].set(task);
    expect(component['reviewTargets'](task).map((item) => item.internship_member_id)).toEqual([
      'm2',
    ]);
    component['reviewWork']();
    httpMock.expectNone('/api/v1/tasks/shared-task/review');
    expect(messages.warning).toHaveBeenCalled();
    expect(component['isSubmitting']()).toBe(false);
  });

  it('reviews a group submission without sending a member target', () => {
    const task = taskDetail({ status: 'SUBMITTED', submissions: [submission(null)] });
    component['detail'].set(task);
    component['reviewMemberId'].set('m2');
    component['reviewWork']();
    const request = httpMock.expectOne('/api/v1/tasks/shared-task/review');
    expect(request.request.body.decision).toBe('COMPLETED');
    expect(request.request.body.internship_member_id).toBeUndefined();
    request.flush(submission(null, { status: 'ACCEPTED' }));
    flushReload();
    httpMock.expectOne('/api/v1/tasks/shared-task').flush(task);
  });
});
