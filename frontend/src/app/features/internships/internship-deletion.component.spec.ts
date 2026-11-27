import { TestBed } from '@angular/core/testing';
import { NzMessageService } from 'ng-zorro-antd/message';
import { of, Subject, throwError } from 'rxjs';
import { Internship, InternshipService } from '../../core/api/internship.service';
import { TrainingService } from '../../core/api/training.service';
import { InternshipManagementComponent } from './internship-management.component';

const internship: Internship = {
  id: 'cohort-1',
  name: 'Đợt mới',
  start_date: '2026-01-01',
  end_date: '2026-12-31',
  status: 'DRAFT',
  description: null,
  created_by: null,
  created_at: '',
  updated_at: '',
  members_count: 0,
};

describe('Internship deletion', () => {
  const remove = vi.fn();
  const message = { success: vi.fn(), error: vi.fn() };
  beforeEach(() => {
    vi.clearAllMocks();
    remove.mockReturnValue(of(undefined));
    TestBed.configureTestingModule({
      imports: [InternshipManagementComponent],
      providers: [
        { provide: InternshipService, useValue: { deleteInternship: remove } },
        { provide: TrainingService, useValue: {} },
        { provide: NzMessageService, useValue: message },
      ],
    }).overrideComponent(InternshipManagementComponent, { set: { template: '' } });
  });

  it('removes the deleted row and closes its selected member panel', () => {
    const fixture = TestBed.createComponent(InternshipManagementComponent);
    const component = fixture.componentInstance;
    component['internships'].set([internship]);
    component['selectedInternship'].set(internship);
    component.deleteInternship(internship);
    expect(remove).toHaveBeenCalledWith(internship.id);
    expect(component['internships']()).toEqual([]);
    expect(component['selectedInternship']()).toBeNull();
    expect(component['members']()).toEqual([]);
    fixture.destroy();
  });

  it('retains rows and shows the server explanation when history prevents deletion', () => {
    remove.mockReturnValue(throwError(() => ({ error: { detail: 'Đợt đã có đơn đăng ký.' } })));
    const fixture = TestBed.createComponent(InternshipManagementComponent);
    const component = fixture.componentInstance;
    component['internships'].set([internship]);
    component.deleteInternship(internship);
    expect(component['internships']()).toEqual([internship]);
    expect(component['deletingInternshipId']()).toBeNull();
    expect(message.error).toHaveBeenCalledWith('Đợt đã có đơn đăng ký.');
    fixture.destroy();
  });

  it('prevents duplicate deletion requests while one is pending', () => {
    const pending = new Subject<void>();
    remove.mockReturnValue(pending);
    const fixture = TestBed.createComponent(InternshipManagementComponent);
    const component = fixture.componentInstance;
    component.deleteInternship(internship);
    component.deleteInternship(internship);
    expect(remove).toHaveBeenCalledTimes(1);
    expect(component['deletingInternshipId']()).toBe(internship.id);
    pending.next();
    pending.complete();
    expect(component['deletingInternshipId']()).toBeNull();
    fixture.destroy();
  });
});
