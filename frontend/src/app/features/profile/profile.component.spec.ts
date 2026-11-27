import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { provideRouter } from '@angular/router';
import {
  CameraOutline,
  DeleteOutline,
  EditOutline,
  InfoCircleOutline,
  KeyOutline,
  LockOutline,
  MailOutline,
  PlusOutline,
} from '@ant-design/icons-angular/icons';
import { provideNzIcons } from 'ng-zorro-antd/icon';
import { of, Subject, Observable } from 'rxjs';
import { AuthService, InternProfileRead } from '../../core/api/auth.service';
import { InternshipService, MyInternshipMembership } from '../../core/api/internship.service';
import { ProfileComponent } from './profile.component';

const PROFILE: InternProfileRead = {
  id: 'intern-1',
  full_name: 'Nguyễn Văn An',
  email: 'intern@example.com',
  phone: '0901234567',
  avatar_url: null,
  role: 'INTERN',
  status: 'ACTIVE',
  created_at: '2026-01-01T00:00:00Z',
  mentor: { id: 'old-mentor', full_name: 'Mentor không thuộc đợt', email: 'old@example.com' },
};

function membership(overrides: Partial<MyInternshipMembership> = {}): MyInternshipMembership {
  return {
    id: 'member-1',
    internship_id: 'batch-1',
    intern_id: 'intern-1',
    mentor_id: 'mentor-1',
    roadmap_id: null,
    start_date: null,
    end_date: null,
    status: 'ACTIVE',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    mentor: {
      id: 'mentor-1',
      full_name: 'Mentor của đợt',
      email: 'mentor@example.com',
      role: 'MENTOR',
    },
    internship: {
      id: 'batch-1',
      name: 'Đợt thực tập mùa thu',
      description: null,
      status: 'ONGOING',
      start_date: '2026-09-01',
      end_date: '2026-12-31',
      created_by: null,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    },
    ...overrides,
  };
}

describe('ProfileComponent information sections', () => {
  let fixture: ComponentFixture<ProfileComponent>;
  const getProfile = vi.fn();
  const getMyMemberships = vi.fn();

  beforeEach(() => {
    getProfile.mockReset().mockReturnValue(of(PROFILE));
    getMyMemberships.mockReset().mockReturnValue(of([membership()]));
    TestBed.configureTestingModule({
      imports: [ProfileComponent],
      providers: [
        provideRouter([]),
        provideNoopAnimations(),
        provideNzIcons([
          MailOutline,
          LockOutline,
          EditOutline,
          KeyOutline,
          CameraOutline,
          PlusOutline,
          DeleteOutline,
          InfoCircleOutline,
        ]),
        { provide: AuthService, useValue: { getProfile } },
        { provide: InternshipService, useValue: { getMyMemberships } },
      ],
    });
  });

  async function render(): Promise<void> {
    fixture = TestBed.createComponent(ProfileComponent);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  }

  function text(): string {
    return fixture.nativeElement.textContent;
  }

  it('renders personal information before internship information and places password controls inside personal information', async () => {
    getMyMemberships.mockReturnValue(
      of([membership({ start_date: '2026-09-15', end_date: '2027-01-15', status: 'EXTENDED' })]),
    );
    await render();
    const titles = Array.from(fixture.nativeElement.querySelectorAll('.ant-card-head-title')).map(
      (element) => (element as HTMLElement).textContent?.trim(),
    );
    expect(titles[0]).toContain('Thông tin cá nhân');
    expect(titles[1]).toBe('Thông tin thực tập');
    expect(titles).toHaveLength(2);
    expect(fixture.nativeElement.querySelector('.profile-security-card')).toBeNull();
    expect(
      fixture.nativeElement.querySelector('.profile-info-card .security-row button'),
    ).not.toBeNull();
    expect(text()).toContain('Đợt thực tập mùa thu');
    expect(text()).toContain('15/09/2026');
    expect(text()).toContain('15/01/2027');
    expect(text()).toContain('Đã gia hạn');
    expect(text()).toContain('Mentor của đợt');
    expect(text()).toContain('mentor@example.com');
    expect(text()).not.toContain('Mentor không thuộc đợt');
  });

  it('shows the assigned internship position and an explicit unassigned fallback', async () => {
    getMyMemberships
      .mockReturnValueOnce(of([membership({ position: 'AI' })]))
      .mockReturnValueOnce(of([membership({ position: null })]));
    await render();
    expect(text()).toContain('Vị trí thực tập');
    expect(text()).toContain('AI Engineer');
    fixture.componentInstance['loadInternship']();
    fixture.detectChanges();
    expect(text()).toContain('Chưa có thông tin');
  });

  it.each(['ADMIN', 'MENTOR'])('does not request internship data for %s', async (role) => {
    getProfile.mockReturnValue(of({ ...PROFILE, role }));
    await render();
    expect(getMyMemberships).not.toHaveBeenCalled();
    expect(text()).not.toContain('Thông tin thực tập');
    expect(text()).toContain('Thông tin cá nhân');
    expect(text()).toContain('Đổi mật khẩu');
  });

  it('uses cohort dates when membership dates are absent and does not borrow the profile mentor', async () => {
    getMyMemberships.mockReturnValue(of([membership({ mentor: null })]));
    await render();
    expect(text()).toContain('01/09/2026');
    expect(text()).toContain('31/12/2026');
    expect(text()).toContain('Chưa được phân công Mentor.');
    expect(text()).not.toContain('Mentor không thuộc đợt');
  });

  it('shows an explicit empty state while retaining personal information', async () => {
    getMyMemberships.mockReturnValue(of([]));
    await render();
    expect(text()).toContain('Bạn chưa tham gia đợt thực tập nào.');
    expect(text()).toContain(PROFILE.phone!);
  });

  it('isolates internship loading and error states and permits retry', async () => {
    const pending = new Subject<MyInternshipMembership[]>();
    getMyMemberships.mockReturnValueOnce(pending).mockReturnValueOnce(of([membership()]));
    await render();
    expect(text()).toContain(PROFILE.full_name);
    expect(fixture.nativeElement.querySelector('[role="status"]')).not.toBeNull();
    pending.error(new Error('unavailable'));
    fixture.detectChanges();
    expect(text()).toContain('Không thể tải thông tin thực tập.');
    expect(text()).toContain(PROFILE.phone!);
    (
      fixture.nativeElement.querySelector('.profile-internship-card button') as HTMLButtonElement
    ).click();
    fixture.detectChanges();
    expect(getMyMemberships).toHaveBeenCalledTimes(2);
    expect(text()).toContain('Đợt thực tập mùa thu');
  });

  it('retains the edit form and password modal actions', async () => {
    await render();
    (
      fixture.nativeElement.querySelector('.info-card-title-row button') as HTMLButtonElement
    ).click();
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('.avatar-upload-area')).not.toBeNull();
    expect(fixture.nativeElement.querySelector('input[name="phone"]')).not.toBeNull();
    (
      fixture.nativeElement.querySelector(
        '.profile-info-card .security-row button',
      ) as HTMLButtonElement
    ).click();
    fixture.detectChanges();
    expect(fixture.componentInstance['isPasswordModalVisible']).toBe(true);
    fixture.componentInstance['closePasswordModal']();
  });

  it('cancels a pending membership request on component destruction', async () => {
    let cancelled = false;
    // Use a cold observable to verify teardown rather than exposing component state.
    getMyMemberships.mockReturnValue(
      new Observable(() => () => {
        cancelled = true;
      }),
    );
    await render();
    fixture.destroy();
    expect(cancelled).toBe(true);
  });
});
