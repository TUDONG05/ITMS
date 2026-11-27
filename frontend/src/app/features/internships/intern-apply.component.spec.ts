import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import {
  CalendarOutline,
  CheckCircleOutline,
  ClockCircleOutline,
  FormOutline,
  CheckOutline,
} from '@ant-design/icons-angular/icons';
import { provideNzIcons } from 'ng-zorro-antd/icon';
import { NzMessageService } from 'ng-zorro-antd/message';
import { of, Subject, throwError } from 'rxjs';
import {
  Internship,
  InternshipApplication,
  InternshipService,
  INTERNSHIP_POSITIONS,
  MyInternshipMembership,
} from '../../core/api/internship.service';
import { InternApplyComponent } from './intern-apply.component';

const BATCH: Internship = {
  id: 'batch-1',
  name: 'Đợt mùa thu',
  description: null,
  status: 'OPEN',
  start_date: '2026-09-01',
  end_date: '2026-12-31',
  created_by: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  roadmaps: INTERNSHIP_POSITIONS.map(({ value, label }) => ({
    id: value,
    name: label,
    position: value,
    status: 'ACTIVE',
  })),
};

describe('Intern internship application position', () => {
  const applyInternship = vi.fn();
  const getMyApplications = vi.fn();
  const getMyMemberships = vi.fn();
  let fixture: ComponentFixture<InternApplyComponent>;
  let component: InternApplyComponent;

  beforeEach(() => {
    applyInternship.mockReset().mockReturnValue(of({}));
    getMyApplications.mockReset().mockReturnValue(of([]));
    getMyMemberships.mockReset().mockReturnValue(of([]));
    TestBed.configureTestingModule({
      imports: [InternApplyComponent],
      providers: [
        provideNoopAnimations(),
        provideNzIcons([
          CalendarOutline,
          CheckCircleOutline,
          ClockCircleOutline,
          FormOutline,
          CheckOutline,
        ]),
        {
          provide: InternshipService,
          useValue: {
            applyInternship,
            getMyApplications,
            getMyMemberships,
            getOpenInternships: () => of([BATCH]),
          },
        },
        { provide: NzMessageService, useValue: { success: vi.fn(), error: vi.fn() } },
      ],
    });
    fixture = TestBed.createComponent(InternApplyComponent);
    component = fixture.componentInstance;
    component.loadMyApps();
  });

  it('requires the intern to choose a position before submitting', () => {
    component.openApplyModal(BATCH);
    component.submitApplication();
    expect(component['applyForm'].controls.position.hasError('required')).toBe(true);
    expect(component['applyForm'].controls.position.touched).toBe(true);
    expect(applyInternship).not.toHaveBeenCalled();
  });

  it('offers only active positions configured for the selected batch', () => {
    const roadmaps = BATCH.roadmaps!;
    component.openApplyModal({
      ...BATCH,
      roadmaps: [
        roadmaps.find((roadmap) => roadmap.position === 'BACKEND')!,
        { ...roadmaps.find((roadmap) => roadmap.position === 'AI')!, status: 'ARCHIVED' },
      ],
    });
    expect(component['positionOptions']().map(({ value }) => value)).toEqual(['BACKEND']);
    component['applyForm'].setValue({ position: 'AI', reason: '' });
    component.submitApplication();
    expect(applyInternship).not.toHaveBeenCalled();
  });

  it.each(INTERNSHIP_POSITIONS)(
    'submits the selected $label position with the reason',
    ({ value }) => {
      component.openApplyModal(BATCH);
      component['applyForm'].setValue({ position: value, reason: '  Nguyện vọng của tôi  ' });
      component.submitApplication();
      expect(applyInternship).toHaveBeenCalledWith('batch-1', {
        position: value,
        reason: 'Nguyện vọng của tôi',
      });
    },
  );

  it('resets position when opening another application and blocks duplicate submission', () => {
    const pending = new Subject<InternshipApplication>();
    applyInternship.mockReturnValue(pending);
    component.openApplyModal(BATCH);
    component['applyForm'].setValue({ position: 'AI', reason: '' });
    component.closeApplyModal();
    component.openApplyModal({ ...BATCH, id: 'batch-2' });
    expect(component['applyForm'].controls.position.value).toBeNull();
    component['applyForm'].setValue({ position: 'AI', reason: '' });
    component.submitApplication();
    component.submitApplication();
    expect(applyInternship).toHaveBeenCalledTimes(1);
    component.closeApplyModal();
    component.openApplyModal(BATCH);
    expect(component['isModalVisible']).toBe(false);
  });

  it('shows selected positions on application history and an explicit legacy fallback', async () => {
    getMyApplications.mockReturnValue(
      of([
        {
          id: 'app-1',
          internship_id: BATCH.id,
          intern_id: 'intern-1',
          internship_name: BATCH.name,
          position: 'BA',
          status: 'PENDING',
          created_at: '2026-01-01T00:00:00Z',
        },
        {
          id: 'app-2',
          internship_id: 'batch-2',
          intern_id: 'intern-1',
          position: null,
          status: 'REJECTED',
          created_at: '2026-01-01T00:00:00Z',
        },
      ]),
    );
    component['selectedTabIndex'] = 1;
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    const text = fixture.nativeElement.textContent;
    expect(text).toContain('Business Analyst (BA)');
    expect(text).toContain('Chưa có thông tin');
  });

  it.each(['ACTIVE', 'EXTENDED', 'COMPLETED', 'STOPPED'])(
    'blocks new registration for a real %s membership without an approved application',
    (status) => {
      getMyMemberships.mockReturnValue(
        of([{ id: 'member-1', status }] as MyInternshipMembership[]),
      );
      component.loadMyApps();
      component.openApplyModal(BATCH);
      expect(component['canRegister']()).toBe(false);
      expect(component['isModalVisible']).toBe(false);
      component['selectedBatch'].set(BATCH);
      component['applyForm'].setValue({ position: 'AI', reason: '' });
      component.submitApplication();
      expect(applyInternship).not.toHaveBeenCalled();
    },
  );

  it.each(['PENDING', 'APPROVED'])('blocks another batch when an application is %s', (status) => {
    getMyApplications.mockReturnValue(
      of([{ id: 'existing', internship_id: 'another-batch', status }]),
    );
    component.loadMyApps();
    expect(component['canRegister']()).toBe(false);
    expect(component.isApplied(BATCH.id)).toBe(false);
    component.openApplyModal(BATCH);
    expect(component['isModalVisible']).toBe(false);
  });

  it('allows registration after rejection if no membership exists', () => {
    getMyApplications.mockReturnValue(
      of([{ id: 'rejected', internship_id: 'another-batch', status: 'REJECTED' }]),
    );
    component.loadMyApps();
    expect(component['canRegister']()).toBe(true);
    component.openApplyModal(BATCH);
    expect(component['isModalVisible']).toBe(true);
  });

  it('keeps registration disabled while eligibility is pending and exposes retry after failure', async () => {
    const pending = new Subject<MyInternshipMembership[]>();
    getMyMemberships.mockReturnValueOnce(pending).mockReturnValueOnce(of([]));
    fixture.detectChanges();
    expect(component['canRegister']()).toBe(false);
    pending.error(new Error('unavailable'));
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    expect(component['eligibilityError']()).toBe(true);
    expect(component['canRegister']()).toBe(false);
    expect(fixture.nativeElement.textContent).toContain('Không thể kiểm tra điều kiện đăng ký');
    const retry = fixture.nativeElement.querySelector(
      '.registration-notice button',
    ) as HTMLButtonElement;
    retry.click();
    fixture.detectChanges();
    expect(component['canRegister']()).toBe(true);
  });

  it('locks immediately on successful submit while eligibility reloads, then allows a rejected application', () => {
    const reloadedApps = new Subject<InternshipApplication[]>();
    getMyApplications.mockReturnValue(reloadedApps);
    component.openApplyModal(BATCH);
    component['applyForm'].setValue({ position: 'BACKEND', reason: '' });
    component.submitApplication();
    expect(component['canRegister']()).toBe(false);
    component.openApplyModal({ ...BATCH, id: 'another-batch' });
    expect(component['isModalVisible']).toBe(false);
    expect(applyInternship).toHaveBeenCalledTimes(1);
    reloadedApps.next([
      {
        id: 'submitted',
        internship_id: BATCH.id,
        intern_id: 'intern-1',
        status: 'REJECTED',
        created_at: '2026-01-01T00:00:00Z',
      },
    ]);
    reloadedApps.complete();
    expect(component['canRegister']()).toBe(true);
  });

  it('keeps application history readable when the membership check fails', () => {
    const apps = [
      {
        id: 'rejected',
        internship_id: 'another-batch',
        intern_id: 'intern-1',
        status: 'REJECTED' as const,
        position: 'AI' as const,
        created_at: '2026-01-01T00:00:00Z',
      },
    ];
    getMyApplications.mockReturnValue(of(apps));
    getMyMemberships.mockReturnValue(throwError(() => new Error('unavailable')));
    component.loadMyApps();
    expect(component['myApplications']()).toEqual(apps);
    expect(component['isLoadingMyApps']()).toBe(false);
    expect(component['canRegister']()).toBe(false);
    expect(component['eligibilityError']()).toBe(true);
  });
});
