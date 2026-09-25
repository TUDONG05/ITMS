import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { NzBadgeModule } from 'ng-zorro-antd/badge';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzCardModule } from 'ng-zorro-antd/card';
import { NzDividerModule } from 'ng-zorro-antd/divider';
import { NzFormModule } from 'ng-zorro-antd/form';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzMessageService } from 'ng-zorro-antd/message';
import { NzModalModule } from 'ng-zorro-antd/modal';
import { NzSelectModule } from 'ng-zorro-antd/select';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzTableModule } from 'ng-zorro-antd/table';
import { NzTagModule } from 'ng-zorro-antd/tag';

import {
  CreateInternshipPayload,
  Internship,
  InternshipMember,
  InternshipService,
  InternshipStatus,
  MemberStatus,
  UpdateInternshipPayload,
  UserSummary,
} from '../../core/api/internship.service';

@Component({
  selector: 'app-internship-management',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    NzBadgeModule,
    NzButtonModule,
    NzCardModule,
    NzDividerModule,
    NzFormModule,
    NzIconModule,
    NzInputModule,
    NzModalModule,
    NzSelectModule,
    NzSpinModule,
    NzTableModule,
    NzTagModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="internship-page">
      <!-- Header Actions -->
      <div class="page-header">
        <div class="header-titles">
          <h2>Quản lý Đợt thực tập</h2>
          <p>
            Tạo mới, theo dõi tiến độ các đợt thực tập và quản lý danh sách thực tập sinh & mentor.
          </p>
        </div>
        <button nz-button nzType="primary" (click)="openCreateModal()">
          <span nz-icon nzType="plus"></span>
          Tạo đợt thực tập
        </button>
      </div>

      <!-- Main Content Cards -->
      <nz-card [nzBordered]="false" class="main-card">
        <!-- Internships Table -->
        <nz-table
          #internshipTable
          [nzData]="internships()"
          [nzLoading]="isLoading()"
          [nzShowPagination]="true"
          [nzPageSize]="10"
        >
          <thead>
            <tr>
              <th>Tên đợt thực tập</th>
              <th>Thời gian</th>
              <th>Trạng thái</th>
              <th>Mô tả</th>
              <th nzAlign="center">Hành động</th>
            </tr>
          </thead>
          <tbody>
            @for (item of internshipTable.data; track item.id) {
              <tr [class.selected-row]="selectedInternship()?.id === item.id">
                <td>
                  <strong>{{ item.name }}</strong>
                </td>
                <td>
                  <span>{{ item.start_date }}</span>
                  <span nz-icon nzType="arrow-right" class="date-arrow"></span>
                  <span>{{ item.end_date }}</span>
                </td>
                <td>
                  <nz-tag [nzColor]="getStatusColor(item.status)">
                    {{ getStatusLabel(item.status) }}
                  </nz-tag>
                </td>
                <td>
                  <span class="desc-text">{{ item.description || '—' }}</span>
                </td>
                <td nzAlign="center">
                  <div class="table-actions">
                    <button
                      nz-button
                      nzType="default"
                      nzSize="small"
                      (click)="selectInternship(item)"
                      [class.btn-active]="selectedInternship()?.id === item.id"
                    >
                      <span nz-icon nzType="team"></span>
                      Quản lý Intern
                    </button>
                    <button nz-button nzType="text" nzSize="small" (click)="openEditModal(item)">
                      <span nz-icon nzType="edit"></span>
                      Sửa
                    </button>
                  </div>
                </td>
              </tr>
            }
          </tbody>
        </nz-table>
      </nz-card>

      <!-- Member Management Panel (When an internship is selected) -->
      @if (selectedInternship(); as current) {
        <nz-card
          [nzBordered]="false"
          class="member-card"
          [nzTitle]="memberCardTitle"
          [nzExtra]="memberCardExtra"
        >
          <ng-template #memberCardTitle>
            <div class="member-panel-header">
              <span nz-icon nzType="team" class="panel-icon"></span>
              <span
                >Danh sách Intern trong đợt: <strong>{{ current.name }}</strong></span
              >
              <nz-tag [nzColor]="getStatusColor(current.status)" style="margin-left: 8px;">
                {{ getStatusLabel(current.status) }}
              </nz-tag>
            </div>
          </ng-template>

          <ng-template #memberCardExtra>
            <button nz-button nzType="primary" nzSize="small" (click)="openAddMemberModal()">
              <span nz-icon nzType="user-add"></span>
              Thêm Intern vào đợt
            </button>
          </ng-template>

          <!-- Members Table -->
          <nz-table
            #memberTable
            [nzData]="members()"
            [nzLoading]="isMembersLoading()"
            [nzShowPagination]="true"
            [nzPageSize]="10"
          >
            <thead>
              <tr>
                <th>Thực tập sinh (Intern)</th>
                <th>Email</th>
                <th>Mentor phụ trách</th>
                <th>Thời gian thực tập</th>
                <th>Trạng thái</th>
                <th nzAlign="center">Phân công Mentor</th>
              </tr>
            </thead>
            <tbody>
              @for (member of memberTable.data; track member.id) {
                <tr>
                  <td>
                    <strong>{{ member.intern?.full_name || 'Intern' }}</strong>
                  </td>
                  <td>{{ member.intern?.email || '—' }}</td>
                  <td>
                    @if (member.mentor) {
                      <div class="mentor-badge">
                        <span nz-icon nzType="solution"></span>
                        <span>{{ member.mentor.full_name }}</span>
                      </div>
                    } @else {
                      <span class="unassigned-text">Chưa phân công</span>
                    }
                  </td>
                  <td>
                    <span>{{ member.start_date || current.start_date }}</span>
                    <span nz-icon nzType="arrow-right" class="date-arrow"></span>
                    <span>{{ member.end_date || current.end_date }}</span>
                  </td>
                  <td>
                    <nz-tag [nzColor]="getMemberStatusColor(member.status)">
                      {{ getMemberStatusLabel(member.status) }}
                    </nz-tag>
                  </td>
                  <td nzAlign="center">
                    <button
                      nz-button
                      nzType="link"
                      nzSize="small"
                      (click)="openAssignMentorModal(member)"
                    >
                      <span nz-icon nzType="swap"></span>
                      {{ member.mentor ? 'Đổi Mentor' : 'Gán Mentor' }}
                    </button>
                  </td>
                </tr>
              }
              @if (members().length === 0 && !isMembersLoading()) {
                <tr>
                  <td colspan="6" class="empty-members">
                    <p>Đợt thực tập này chưa có Intern nào tham gia.</p>
                    <button nz-button nzType="dashed" (click)="openAddMemberModal()">
                      + Thêm Intern đầu tiên
                    </button>
                  </td>
                </tr>
              }
            </tbody>
          </nz-table>
        </nz-card>
      }

      <!-- Modal: Tạo / Chỉnh sửa Đợt thực tập -->
      <nz-modal
        [(nzVisible)]="isInternshipModalVisible"
        [nzTitle]="editingInternship() ? 'Chỉnh sửa Đợt thực tập' : 'Tạo Đợt thực tập mới'"
        (nzOnCancel)="closeInternshipModal()"
        (nzOnOk)="saveInternship()"
        [nzOkLoading]="isSavingInternship()"
        nzWidth="540px"
      >
        <ng-container *nzModalContent>
          <form [formGroup]="internshipForm" nz-form nzLayout="vertical">
            <nz-form-item>
              <nz-form-label nzRequired>Tên đợt thực tập</nz-form-label>
              <nz-form-control nzErrorTip="Vui lòng nhập tên đợt thực tập (tối thiểu 3 ký tự)">
                <input nz-input formControlName="name" placeholder="Ví dụ: Đợt thực tập Thu 2026" />
              </nz-form-control>
            </nz-form-item>

            <div class="form-row">
              <nz-form-item class="form-col">
                <nz-form-label nzRequired>Ngày bắt đầu</nz-form-label>
                <nz-form-control nzErrorTip="Chọn ngày bắt đầu">
                  <input nz-input type="date" formControlName="start_date" />
                </nz-form-control>
              </nz-form-item>

              <nz-form-item class="form-col">
                <nz-form-label nzRequired>Ngày kết thúc</nz-form-label>
                <nz-form-control nzErrorTip="Chọn ngày kết thúc">
                  <input nz-input type="date" formControlName="end_date" />
                </nz-form-control>
              </nz-form-item>
            </div>

            <nz-form-item>
              <nz-form-label nzRequired>Trạng thái</nz-form-label>
              <nz-form-control>
                <nz-select formControlName="status">
                  <nz-option nzValue="DRAFT" nzLabel="Bản nháp (DRAFT)"></nz-option>
                  <nz-option nzValue="OPEN" nzLabel="Đang mở tuyển (OPEN)"></nz-option>
                  <nz-option nzValue="ONGOING" nzLabel="Đang diễn ra (ONGOING)"></nz-option>
                  <nz-option nzValue="COMPLETED" nzLabel="Đã kết thúc (COMPLETED)"></nz-option>
                  <nz-option nzValue="CANCELLED" nzLabel="Đã hủy (CANCELLED)"></nz-option>
                </nz-select>
              </nz-form-control>
            </nz-form-item>

            <nz-form-item>
              <nz-form-label>Mô tả chi tiết</nz-form-label>
              <nz-form-control>
                <textarea
                  nz-input
                  rows="3"
                  formControlName="description"
                  placeholder="Mô tả mục tiêu, yêu cầu hoặc lộ trình đào tạo của đợt..."
                ></textarea>
              </nz-form-control>
            </nz-form-item>
          </form>
        </ng-container>
      </nz-modal>

      <!-- Modal: Thêm Intern vào Đợt thực tập -->
      <nz-modal
        [(nzVisible)]="isAddMemberModalVisible"
        nzTitle="Thêm Thực tập sinh vào đợt"
        (nzOnCancel)="closeAddMemberModal()"
        (nzOnOk)="saveAddMember()"
        [nzOkLoading]="isSavingMember()"
        nzWidth="500px"
      >
        <ng-container *nzModalContent>
          <form [formGroup]="addMemberForm" nz-form nzLayout="vertical">
            <nz-form-item>
              <nz-form-label nzRequired>Chọn Thực tập sinh (Intern)</nz-form-label>
              <nz-form-control nzErrorTip="Vui lòng chọn một thực tập sinh">
                <nz-select
                  formControlName="intern_id"
                  nzPlaceHolder="Chọn Intern từ hệ thống"
                  nzShowSearch
                >
                  @for (intern of availableInterns(); track intern.id) {
                    <nz-option
                      [nzValue]="intern.id"
                      [nzLabel]="intern.full_name + ' (' + intern.email + ')'"
                    ></nz-option>
                  }
                </nz-select>
              </nz-form-control>
            </nz-form-item>

            <nz-form-item>
              <nz-form-label>Phân công Mentor (Tùy chọn)</nz-form-label>
              <nz-form-control>
                <nz-select
                  formControlName="mentor_id"
                  nzPlaceHolder="Chưa phân công (chọn sau)"
                  nzAllowClear
                  nzShowSearch
                >
                  @for (mentor of availableMentors(); track mentor.id) {
                    <nz-option
                      [nzValue]="mentor.id"
                      [nzLabel]="mentor.full_name + ' (' + mentor.email + ')'"
                    ></nz-option>
                  }
                </nz-select>
              </nz-form-control>
            </nz-form-item>

            <nz-form-item>
              <nz-form-label>Trạng thái tham gia</nz-form-label>
              <nz-form-control>
                <nz-select formControlName="status">
                  <nz-option nzValue="ACTIVE" nzLabel="Đang hoạt động (ACTIVE)"></nz-option>
                  <nz-option nzValue="EXTENDED" nzLabel="Gia hạn (EXTENDED)"></nz-option>
                  <nz-option nzValue="STOPPED" nzLabel="Tạm dừng (STOPPED)"></nz-option>
                  <nz-option nzValue="COMPLETED" nzLabel="Hoàn thành (COMPLETED)"></nz-option>
                </nz-select>
              </nz-form-control>
            </nz-form-item>
          </form>
        </ng-container>
      </nz-modal>

      <!-- Modal: Gán / Thay đổi Mentor cho Intern -->
      <nz-modal
        [(nzVisible)]="isAssignMentorModalVisible"
        nzTitle="Phân công Mentor phụ trách"
        (nzOnCancel)="closeAssignMentorModal()"
        (nzOnOk)="saveAssignMentor()"
        [nzOkLoading]="isSavingMentorAssignment()"
        nzWidth="460px"
      >
        <ng-container *nzModalContent>
          <div class="assign-info-box">
            <p>
              Thực tập sinh: <strong>{{ selectedMemberForMentor()?.intern?.full_name }}</strong>
            </p>
            <p>
              Mentor hiện tại:
              <strong>{{ selectedMemberForMentor()?.mentor?.full_name || 'Chưa có' }}</strong>
            </p>
          </div>

          <form [formGroup]="assignMentorForm" nz-form nzLayout="vertical">
            <nz-form-item>
              <nz-form-label nzRequired>Chọn Mentor mới</nz-form-label>
              <nz-form-control nzErrorTip="Vui lòng chọn Mentor">
                <nz-select
                  formControlName="mentor_id"
                  nzPlaceHolder="Chọn Mentor từ danh sách"
                  nzShowSearch
                  nzAllowClear
                >
                  @for (mentor of availableMentors(); track mentor.id) {
                    <nz-option
                      [nzValue]="mentor.id"
                      [nzLabel]="mentor.full_name + ' (' + mentor.email + ')'"
                    ></nz-option>
                  }
                </nz-select>
              </nz-form-control>
            </nz-form-item>
          </form>
        </ng-container>
      </nz-modal>
    </div>
  `,
  styles: [
    `
      .internship-page {
        display: flex;
        flex-direction: column;
        gap: 20px;
      }

      .page-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: #fff;
        padding: 18px 24px;
        border-radius: 8px;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);

        .header-titles {
          h2 {
            margin: 0 0 4px;
            font-size: 20px;
            font-weight: 600;
            color: #1a1a1a;
          }
          p {
            margin: 0;
            font-size: 13px;
            color: #666;
          }
        }
      }

      .main-card,
      .member-card {
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
      }

      .selected-row {
        background-color: #f0f7ff !important;
      }

      .date-arrow {
        margin: 0 6px;
        font-size: 11px;
        color: #999;
      }

      .desc-text {
        color: #555;
        font-size: 13px;
        max-width: 250px;
        display: inline-block;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .table-actions {
        display: flex;
        gap: 8px;
        justify-content: center;

        .btn-active {
          border-color: #1890ff;
          color: #1890ff;
          font-weight: 600;
        }
      }

      .member-panel-header {
        display: flex;
        align-items: center;
        font-size: 16px;

        .panel-icon {
          margin-right: 8px;
          color: #1890ff;
        }
      }

      .mentor-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        color: #2f54eb;
        font-weight: 500;
      }

      .unassigned-text {
        color: #fa8c16;
        font-style: italic;
        font-size: 12px;
      }

      .empty-members {
        text-align: center;
        padding: 30px;
        color: #888;

        p {
          margin-bottom: 12px;
        }
      }

      .form-row {
        display: flex;
        gap: 16px;

        .form-col {
          flex: 1;
        }
      }

      .assign-info-box {
        background: #fafafa;
        padding: 12px 16px;
        border-radius: 6px;
        margin-bottom: 16px;
        border-left: 3px solid #1890ff;

        p {
          margin: 4px 0;
          font-size: 13px;
        }
      }
    `,
  ],
})
export class InternshipManagementComponent implements OnInit {
  private readonly internshipService = inject(InternshipService);
  private readonly fb = inject(FormBuilder);
  private readonly message = inject(NzMessageService);

  protected readonly internships = signal<Internship[]>([]);
  protected readonly isLoading = signal<boolean>(false);
  protected readonly selectedInternship = signal<Internship | null>(null);

  protected readonly members = signal<InternshipMember[]>([]);
  protected readonly isMembersLoading = signal<boolean>(false);

  protected readonly availableInterns = signal<UserSummary[]>([]);
  protected readonly availableMentors = signal<UserSummary[]>([]);

  // Modals state
  protected isInternshipModalVisible = false;
  protected isSavingInternship = signal<boolean>(false);
  protected readonly editingInternship = signal<Internship | null>(null);

  protected isAddMemberModalVisible = false;
  protected isSavingMember = signal<boolean>(false);

  protected isAssignMentorModalVisible = false;
  protected isSavingMentorAssignment = signal<boolean>(false);
  protected readonly selectedMemberForMentor = signal<InternshipMember | null>(null);

  // Forms
  protected readonly internshipForm = this.fb.group({
    name: ['', [Validators.required, Validators.minLength(3)]],
    start_date: ['', [Validators.required]],
    end_date: ['', [Validators.required]],
    status: ['DRAFT' as InternshipStatus, [Validators.required]],
    description: [''],
  });

  protected readonly addMemberForm = this.fb.group({
    intern_id: ['', [Validators.required]],
    mentor_id: [null as string | null],
    status: ['ACTIVE' as MemberStatus, [Validators.required]],
  });

  protected readonly assignMentorForm = this.fb.group({
    mentor_id: ['', [Validators.required]],
  });

  ngOnInit(): void {
    this.loadInternships();
    this.loadUsers();
  }

  loadInternships(): void {
    this.isLoading.set(true);
    this.internshipService.getInternships().subscribe({
      next: (data) => {
        this.internships.set(data);
        this.isLoading.set(false);
        // If an internship was previously selected, refresh its reference
        const current = this.selectedInternship();
        if (current) {
          const updated = data.find((i) => i.id === current.id);
          if (updated) {
            this.selectedInternship.set(updated);
            this.loadMembers(updated.id);
          }
        }
      },
      error: () => {
        this.message.error('Không thể tải danh sách đợt thực tập.');
        this.isLoading.set(false);
      },
    });
  }

  loadUsers(): void {
    this.internshipService.getUsers('INTERN').subscribe({
      next: (users) => this.availableInterns.set(users),
    });
    this.internshipService.getUsers('MENTOR').subscribe({
      next: (users) => this.availableMentors.set(users),
    });
  }

  selectInternship(internship: Internship): void {
    this.selectedInternship.set(internship);
    this.loadMembers(internship.id);
  }

  loadMembers(internshipId: string): void {
    this.isMembersLoading.set(true);
    this.internshipService.getMembers(internshipId).subscribe({
      next: (members) => {
        this.members.set(members);
        this.isMembersLoading.set(false);
      },
      error: () => {
        this.message.error('Không thể tải danh sách thành viên thực tập.');
        this.isMembersLoading.set(false);
      },
    });
  }

  // --- Modal Đợt thực tập ---
  openCreateModal(): void {
    this.editingInternship.set(null);
    this.internshipForm.reset({
      name: '',
      start_date: new Date().toISOString().substring(0, 10),
      end_date: new Date(Date.now() + 90 * 24 * 60 * 60 * 1000).toISOString().substring(0, 10),
      status: 'DRAFT',
      description: '',
    });
    this.isInternshipModalVisible = true;
  }

  openEditModal(item: Internship): void {
    this.editingInternship.set(item);
    this.internshipForm.patchValue({
      name: item.name,
      start_date: item.start_date,
      end_date: item.end_date,
      status: item.status,
      description: item.description || '',
    });
    this.isInternshipModalVisible = true;
  }

  closeInternshipModal(): void {
    this.isInternshipModalVisible = false;
  }

  saveInternship(): void {
    if (this.internshipForm.invalid) {
      this.internshipForm.markAllAsTouched();
      return;
    }

    const formVal = this.internshipForm.getRawValue();
    if (formVal.end_date && formVal.start_date && formVal.end_date < formVal.start_date) {
      this.message.error('Ngày kết thúc không được nhỏ hơn ngày bắt đầu.');
      return;
    }

    this.isSavingInternship.set(true);
    const editing = this.editingInternship();

    if (editing) {
      const payload: UpdateInternshipPayload = {
        name: formVal.name ?? undefined,
        start_date: formVal.start_date ?? undefined,
        end_date: formVal.end_date ?? undefined,
        status: formVal.status ?? undefined,
        description: formVal.description,
      };
      this.internshipService.updateInternship(editing.id, payload).subscribe({
        next: () => {
          this.message.success('Cập nhật đợt thực tập thành công!');
          this.isSavingInternship.set(false);
          this.closeInternshipModal();
          this.loadInternships();
        },
        error: (err) => {
          this.message.error(err?.error?.detail || 'Lỗi khi cập nhật đợt thực tập.');
          this.isSavingInternship.set(false);
        },
      });
    } else {
      const payload: CreateInternshipPayload = {
        name: formVal.name!,
        start_date: formVal.start_date!,
        end_date: formVal.end_date!,
        status: formVal.status ?? 'DRAFT',
        description: formVal.description,
      };
      this.internshipService.createInternship(payload).subscribe({
        next: (created) => {
          this.message.success('Tạo đợt thực tập thành công!');
          this.isSavingInternship.set(false);
          this.closeInternshipModal();
          this.loadInternships();
          this.selectInternship(created);
        },
        error: (err) => {
          this.message.error(err?.error?.detail || 'Lỗi khi tạo đợt thực tập.');
          this.isSavingInternship.set(false);
        },
      });
    }
  }

  // --- Modal Thêm Intern ---
  openAddMemberModal(): void {
    this.addMemberForm.reset({
      intern_id: '',
      mentor_id: null,
      status: 'ACTIVE',
    });
    this.isAddMemberModalVisible = true;
  }

  closeAddMemberModal(): void {
    this.isAddMemberModalVisible = false;
  }

  saveAddMember(): void {
    const current = this.selectedInternship();
    if (!current) return;

    if (this.addMemberForm.invalid) {
      this.addMemberForm.markAllAsTouched();
      return;
    }

    const formVal = this.addMemberForm.getRawValue();
    this.isSavingMember.set(true);

    this.internshipService
      .addMember(current.id, {
        intern_id: formVal.intern_id!,
        mentor_id: formVal.mentor_id,
        status: formVal.status ?? 'ACTIVE',
      })
      .subscribe({
        next: () => {
          this.message.success('Đã thêm thực tập sinh vào đợt thành công!');
          this.isSavingMember.set(false);
          this.closeAddMemberModal();
          this.loadMembers(current.id);
        },
        error: (err) => {
          this.message.error(
            err?.error?.detail || 'Không thể thêm Intern (có thể đã tồn tại trong đợt).',
          );
          this.isSavingMember.set(false);
        },
      });
  }

  // --- Modal Gán / Đổi Mentor ---
  openAssignMentorModal(member: InternshipMember): void {
    this.selectedMemberForMentor.set(member);
    this.assignMentorForm.reset({
      mentor_id: member.mentor_id || '',
    });
    this.isAssignMentorModalVisible = true;
  }

  closeAssignMentorModal(): void {
    this.isAssignMentorModalVisible = false;
  }

  saveAssignMentor(): void {
    const member = this.selectedMemberForMentor();
    if (!member) return;

    if (this.assignMentorForm.invalid) {
      this.assignMentorForm.markAllAsTouched();
      return;
    }

    const mentorId = this.assignMentorForm.getRawValue().mentor_id;
    this.isSavingMentorAssignment.set(true);

    this.internshipService.assignMentor(member.id, mentorId).subscribe({
      next: () => {
        this.message.success('Đã phân công Mentor thành công!');
        this.isSavingMentorAssignment.set(false);
        this.closeAssignMentorModal();
        const current = this.selectedInternship();
        if (current) {
          this.loadMembers(current.id);
        }
      },
      error: (err) => {
        this.message.error(err?.error?.detail || 'Lỗi khi phân công Mentor.');
        this.isSavingMentorAssignment.set(false);
      },
    });
  }

  // --- Helpers ---
  getStatusColor(status: InternshipStatus): string {
    switch (status) {
      case 'DRAFT':
        return 'default';
      case 'OPEN':
        return 'processing';
      case 'ONGOING':
        return 'success';
      case 'COMPLETED':
        return 'purple';
      case 'CANCELLED':
        return 'error';
      default:
        return 'default';
    }
  }

  getStatusLabel(status: InternshipStatus): string {
    switch (status) {
      case 'DRAFT':
        return 'Bản nháp';
      case 'OPEN':
        return 'Mở tuyển';
      case 'ONGOING':
        return 'Đang diễn ra';
      case 'COMPLETED':
        return 'Hoàn thành';
      case 'CANCELLED':
        return 'Đã hủy';
      default:
        return status;
    }
  }

  getMemberStatusColor(status: MemberStatus): string {
    switch (status) {
      case 'ACTIVE':
        return 'success';
      case 'EXTENDED':
        return 'warning';
      case 'STOPPED':
        return 'error';
      case 'COMPLETED':
        return 'blue';
      default:
        return 'default';
    }
  }

  getMemberStatusLabel(status: MemberStatus): string {
    switch (status) {
      case 'ACTIVE':
        return 'Đang thực tập';
      case 'EXTENDED':
        return 'Gia hạn';
      case 'STOPPED':
        return 'Đã dừng';
      case 'COMPLETED':
        return 'Hoàn thành';
      default:
        return status;
    }
  }
}
