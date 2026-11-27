import { TestBed } from '@angular/core/testing';
import { NzMessageService } from 'ng-zorro-antd/message';
import { of, throwError } from 'rxjs';
import {
  Internship,
  InternshipPosition,
  InternshipService,
} from '../../core/api/internship.service';
import { Roadmap, TrainingService } from '../../core/api/training.service';
import { InternshipManagementComponent } from '../internships/internship-management.component';
import { TrainingManagementComponent } from './training-management.component';
import { RequestManagementComponent } from '../requests/request-management.component';

function roadmap(
  id: string,
  position: InternshipPosition | null = 'BACKEND',
  status: Roadmap['status'] = 'ACTIVE',
): Roadmap {
  return {
    id,
    name: id,
    position,
    status,
    description: null,
    created_by: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  };
}
const COHORT: Internship = {
  id: 'cohort-1',
  name: 'Đợt thực tập',
  description: null,
  status: 'OPEN',
  start_date: '2026-09-01',
  end_date: '2026-12-31',
  created_by: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  roadmap_ids: [],
  roadmaps: [],
};

describe('Position-specific roadmap configuration', () => {
  const training = { getRoadmaps: vi.fn(), createRoadmap: vi.fn(), updateRoadmap: vi.fn() };
  const internships = {
    createInternship: vi.fn(),
    updateInternship: vi.fn(),
    getInternships: vi.fn(),
    getMembers: vi.fn(),
    reviewApplication: vi.fn(),
  };
  const message = { success: vi.fn(), error: vi.fn() };

  beforeEach(async () => {
    training.getRoadmaps.mockReset().mockReturnValue(of([]));
    training.createRoadmap.mockReset().mockReturnValue(of(roadmap('created')));
    training.updateRoadmap.mockReset().mockReturnValue(of(roadmap('updated')));
    internships.createInternship.mockReset().mockReturnValue(of(COHORT));
    internships.updateInternship.mockReset().mockReturnValue(of(COHORT));
    internships.getInternships.mockReset().mockReturnValue(of([]));
    internships.getMembers.mockReset().mockReturnValue(of([]));
    message.error.mockReset();
    await TestBed.configureTestingModule({
      imports: [
        TrainingManagementComponent,
        InternshipManagementComponent,
        RequestManagementComponent,
      ],
      providers: [
        { provide: TrainingService, useValue: training },
        { provide: InternshipService, useValue: internships },
        { provide: NzMessageService, useValue: message },
      ],
    })
      .overrideComponent(TrainingManagementComponent, { set: { template: '' } })
      .overrideComponent(InternshipManagementComponent, { set: { template: '' } })
      .overrideComponent(RequestManagementComponent, { set: { template: '' } })
      .compileComponents();
  });

  it('requires a position when creating a roadmap instead of guessing a default', () => {
    const component = TestBed.createComponent(TrainingManagementComponent).componentInstance;
    component.openCreateRoadmapModal();
    component['roadmapForm'].patchValue({ name: 'Backend roadmap' });
    component.saveRoadmap();
    expect(component['roadmapForm'].controls.position.value).toBeNull();
    expect(component['roadmapForm'].controls.position.hasError('required')).toBe(true);
    expect(training.createRoadmap).not.toHaveBeenCalled();
    component['roadmapForm'].controls.position.setValue('BACKEND');
    component.saveRoadmap();
    expect(training.createRoadmap).toHaveBeenCalledWith(
      expect.objectContaining({ position: 'BACKEND' }),
    );
  });

  it('forces classification when editing an untyped legacy roadmap and includes the chosen position', () => {
    const component = TestBed.createComponent(TrainingManagementComponent).componentInstance;
    component.openEditRoadmapModal(roadmap('legacy', null));
    component.saveRoadmap();
    expect(training.updateRoadmap).not.toHaveBeenCalled();
    component['roadmapForm'].controls.position.setValue('AI');
    component.saveRoadmap();
    expect(training.updateRoadmap).toHaveBeenCalledWith(
      'legacy',
      expect.objectContaining({ position: 'AI' }),
    );
  });

  it('shows the backend explanation when a configured roadmap position cannot be changed', () => {
    training.updateRoadmap.mockReturnValue(
      throwError(() => ({ error: { detail: 'Lộ trình đã được cấu hình cho đợt thực tập.' } })),
    );
    const component = TestBed.createComponent(TrainingManagementComponent).componentInstance;
    component.openEditRoadmapModal(roadmap('configured'));
    component['roadmapForm'].controls.position.setValue('FRONTEND');
    component.saveRoadmap();
    expect(message.error).toHaveBeenCalledWith('Lộ trình đã được cấu hình cho đợt thực tập.');
    expect(component['isSaving']()).toBe(false);
    expect(component['isRoadmapModalVisible']).toBe(true);
  });

  it('sends multiple roadmaps for different positions and never sends a global roadmap_id', () => {
    const component = TestBed.createComponent(InternshipManagementComponent).componentInstance;
    component['availableRoadmaps'].set([roadmap('backend'), roadmap('frontend', 'FRONTEND')]);
    component.openCreateModal();
    component['internshipForm'].patchValue({
      name: 'New cohort',
      roadmap_ids: ['backend', 'frontend'],
    });
    component.saveInternship();
    const payload = internships.createInternship.mock.calls[0][0];
    expect(payload.roadmap_ids).toEqual(['backend', 'frontend']);
    expect(payload).not.toHaveProperty('roadmap_id');
  });

  it('rejects two roadmaps for the same position', () => {
    const component = TestBed.createComponent(InternshipManagementComponent).componentInstance;
    component['availableRoadmaps'].set([roadmap('backend-a'), roadmap('backend-b')]);
    component.openCreateModal();
    component['internshipForm'].patchValue({
      name: 'New cohort',
      roadmap_ids: ['backend-a', 'backend-b'],
    });
    component.saveInternship();
    expect(internships.createInternship).not.toHaveBeenCalled();
    expect(component['internshipForm'].controls.roadmap_ids.hasError('duplicatePosition')).toBe(
      true,
    );
  });

  it.each([roadmap('untyped', null), roadmap('inactive', 'BACKEND', 'ARCHIVED')])(
    'rejects a new selection of $id',
    (invalid) => {
      const component = TestBed.createComponent(InternshipManagementComponent).componentInstance;
      component['availableRoadmaps'].set([invalid]);
      component.openCreateModal();
      component['internshipForm'].patchValue({ name: 'New cohort', roadmap_ids: [invalid.id] });
      component.saveInternship();
      expect(internships.createInternship).not.toHaveBeenCalled();
      expect(component['internshipForm'].controls.roadmap_ids.hasError('invalidRoadmap')).toBe(
        true,
      );
    },
  );

  it('preserves an existing inactive mapping for metadata edits and displays its position', () => {
    const inactive = roadmap('previous', 'BA', 'ARCHIVED');
    const cohort = { ...COHORT, roadmap_ids: [inactive.id], roadmaps: [inactive] };
    const component = TestBed.createComponent(InternshipManagementComponent).componentInstance;
    component.openEditModal(cohort);
    expect(component['roadmapOptions']()).toContainEqual(inactive);
    expect(component['configuredRoadmaps'](cohort)[0].position).toBe('BA');
    component['internshipForm'].controls.name.setValue('Updated cohort');
    component.saveInternship();
    expect(internships.updateInternship).toHaveBeenCalledWith(
      COHORT.id,
      expect.objectContaining({ roadmap_ids: [inactive.id] }),
    );
  });

  it('does not turn a legacy single global roadmap into a position mapping', () => {
    const component = TestBed.createComponent(InternshipManagementComponent).componentInstance;
    component.openEditModal({
      ...COHORT,
      roadmap_ids: undefined,
      roadmaps: undefined,
      roadmap_id: 'legacy-global',
    });
    expect(component['internshipForm'].controls.roadmap_ids.value).toEqual([]);
    expect(component['configuredRoadmaps']({ ...COHORT, roadmap_id: 'legacy-global' })).toEqual([]);
  });

  it.each([
    { error: { detail: 'Đợt thực tập chưa có lộ trình phù hợp với vị trí.' } },
    { error: { error: { message: 'Đơn đăng ký chưa có vị trí thực tập.' } } },
  ])('shows the Vietnamese approval conflict explanation to the admin', (error) => {
    internships.reviewApplication.mockReturnValue(throwError(() => error));
    const component = TestBed.createComponent(RequestManagementComponent).componentInstance;
    component.singleApproveApp({
      id: 'application-1',
      internship_id: COHORT.id,
      intern_id: 'intern-1',
      status: 'PENDING',
      created_at: '2026-01-01T00:00:00Z',
    });
    const expected = 'detail' in error.error ? error.error.detail : error.error.error.message;
    expect(message.error).toHaveBeenCalledWith(expected);
  });
});
