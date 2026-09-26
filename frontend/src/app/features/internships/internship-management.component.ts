import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  OnInit,
  computed,
  inject,
  signal,
} from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { NzBadgeModule } from 'ng-zorro-antd/badge';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzCardModule } from 'ng-zorro-antd/card';
import { NzDatePickerModule } from 'ng-zorro-antd/date-picker';
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
  UpdateMemberPayload,
  UserSummary,
} from '../../core/api/internship.service';

@Component({
  selector: 'app-internship-management',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    NzBadgeModule,
    NzButtonModule,
    NzCardModule,
    NzDatePickerModule,
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
        <!-- Toolbar: Tìm kiếm và Lọc trạng thái -->
        <div class="table-toolbar">
          <div class="search-box">
            <input
              type="text"
              nz-input
              placeholder="🔎 Tìm kiếm tên đợt thực tập..."
              [ngModel]="searchQuery()"
              (ngModelChange)="onSearchChange($event)"
            />
          </div>

          <div class="filter-box">
            <span class="filter-label">Trạng thái:</span>
            <nz-select
              [ngModel]="statusFilter()"
              (ngModelChange)="onStatusChange($event)"
              nzPlaceHolder="Trạng thái"
              class="status-filter-select"
            >
              <nz-option nzValue="" nzLabel="Tất cả trạng thái"></nz-option>
              <nz-option nzValue="DRAFT" nzLabel="Bản nháp"></nz-option>
              <nz-option nzValue="OPEN" nzLabel="Đang mở"></nz-option>
              <nz-option nzValue="ONGOING" nzLabel="Đang diễn ra"></nz-option>
              <nz-option nzValue="COMPLETED" nzLabel="Đã hoàn thành"></nz-option>
              <nz-option nzValue="CANCELLED" nzLabel="Đã hủy"></nz-option>
            </nz-select>
          </div>
        </div>

        <!-- Internships Table -->
        <nz-table
          #internshipTable
          [nzData]="filteredInternships()"
          [nzLoading]="isLoading()"
          [nzShowPagination]="true"
          [nzPageSize]="10"
        >
          <thead>
            <tr>
              <th>Tên đợt thực tập</th>
              <th>Thời gian bắt đầu</th>
              <th>Thời gian kết thúc</th>
              <th>Trạng thái</th>
              <th nzAlign="center">Số lượng thực tập sinh</th>
              <th nzAlign="center">Thao tác</th>
            </tr>
          </thead>
          <tbody>
            @for (item of internshipTable.data; track item.id) {
              <tr [class.selected-row]="selectedInternship()?.id === item.id">
                <td>
                  <strong>{{ item.name }}</strong>
                </td>
                <td>{{ item.start_date }}</td>
                <td>{{ item.end_date }}</td>
                <td>
                  <nz-tag [nzColor]="getStatusColor(item.status)">
                    {{ getStatusLabel(item.status) }}
                  </nz-tag>
                </td>
                <td nzAlign="center">
                  <div class="member-count">
                    <span class="count-number">{{ item.members_count ?? 0 }}</span>
                    <span class="count-label"></span>
                  </div>
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
                      Chỉnh sửa
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

          <!-- Member Toolbar with Search Intern -->
          <div class="table-toolbar member-toolbar">
            <div class="search-box">
              <input
                type="text"
                nz-input
                placeholder="🔎 Tìm kiếm tên thực tập sinh..."
                [ngModel]="memberSearchQuery()"
                (ngModelChange)="onMemberSearchChange($event)"
              />
            </div>
          </div>

          <!-- Members Table -->
          <nz-table
            #memberTable
            [nzData]="filteredMembers()"
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
                <th nzAlign="center">Thao tác</th>
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
                      nzType="text"
                      nzSize="small"
                      (click)="openEditMemberModal(member)"
                    >
                      <span nz-icon nzType="edit"></span>
                      Chỉnh sửa
                    </button>
                  </td>
                </tr>
              }
              @if (filteredMembers().length === 0 && !isMembersLoading()) {
                <tr>
                  <td colspan="6" class="empty-members">
                    <p>
                      {{
                        memberSearchQuery()
                          ? 'Không tìm thấy thực tập sinh phù hợp.'
                          : 'Đợt thực tập này chưa có Intern nào tham gia.'
                      }}
                    </p>
                    @if (!memberSearchQuery()) {
                      <button nz-button nzType="dashed" (click)="openAddMemberModal()">
                        + Thêm Intern đầu tiên
                      </button>
                    }
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
                  <nz-option nzValue="OPEN" nzLabel="Đang mở (OPEN)"></nz-option>
                  <nz-option nzValue="ONGOING" nzLabel="Đang diễn ra (ONGOING)"></nz-option>
                  <nz-option nzValue="COMPLETED" nzLabel="Đã hoàn thành (COMPLETED)"></nz-option>
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
                  <nz-option nzValue="ACTIVE" nzLabel="Đang thực tập (ACTIVE)"></nz-option>
                  <nz-option nzValue="EXTENDED" nzLabel="Gia hạn (EXTENDED)"></nz-option>
                  <nz-option nzValue="STOPPED" nzLabel="Tạm dừng (STOPPED)"></nz-option>
                  <nz-option nzValue="COMPLETED" nzLabel="Hoàn thành (COMPLETED)"></nz-option>
                </nz-select>
              </nz-form-control>
            </nz-form-item>
          </form>
        </ng-container>
      </nz-modal>

      <!-- Modal: Chỉnh sửa thông tin thực tập sinh -->
      <nz-modal
        [(nzVisible)]="isEditMemberModalVisible"
        nzTitle="Chỉnh sửa thông tin thực tập sinh"
        (nzOnCancel)="closeEditMemberModal()"
        (nzOnOk)="saveEditMember()"
        [nzOkLoading]="isSavingEditMember()"
        nzOkText="Lưu thay đổi"
        nzCancelText="Hủy"
        nzWidth="540px"
      >
        <ng-container *nzModalContent>
          <form [formGroup]="editMemberForm" nz-form nzLayout="vertical">
            <div class="form-row">
              <nz-form-item class="form-col">
                <nz-form-label>Tên thực tập sinh</nz-form-label>
                <nz-form-control>
                  <input nz-input formControlName="intern_name" />
                </nz-form-control>
              </nz-form-item>

              <nz-form-item class="form-col">
                <nz-form-label>Email</nz-form-label>
                <nz-form-control>
                  <input nz-input formControlName="intern_email" />
                </nz-form-control>
              </nz-form-item>
            </div>

            <nz-form-item>
              <nz-form-label nzRequired>Trạng thái thực tập sinh</nz-form-label>
              <nz-form-control nzErrorTip="Vui lòng chọn trạng thái">
                <nz-select formControlName="status">
                  <nz-option nzValue="ACTIVE" nzLabel="Đang thực tập"></nz-option>
                  <nz-option nzValue="EXTENDED" nzLabel="Gia hạn"></nz-option>
                  <nz-option nzValue="STOPPED" nzLabel="Tạm dừng"></nz-option>
                  <nz-option nzValue="COMPLETED" nzLabel="Hoàn thành"></nz-option>
                </nz-select>
              </nz-form-control>
            </nz-form-item>

            <nz-form-item>
              <nz-form-label>Mentor phụ trách</nz-form-label>
              <nz-form-control>
                <nz-select
                  formControlName="mentor_id"
                  nzPlaceHolder="Chưa phân công (chọn Mentor)"
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

      .table-toolbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 16px;
        margin-bottom: 16px;
        flex-wrap: wrap;

        .search-box {
          flex: 1;
          min-width: 260px;
          max-width: 380px;
        }

        .filter-box {
          display: flex;
          align-items: center;
          gap: 8px;

          .filter-label {
            font-size: 14px;
            color: #555;
            white-space: nowrap;
          }

          .status-filter-select {
            width: 180px;
          }
        }
      }

      .member-toolbar {
        margin-top: 4px;
        margin-bottom: 16px;
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
      .member-count {
        display: inline-flex;
        align-items: baseline;
        gap: 4px;
      }

      .count-number {
        font-size: 15px;
        font-weight: 600;
        color: #1890ff;
      }

      .count-label {
        font-size: 13px;
        color: #666;
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
  private readonly cdr = inject(ChangeDetectorRef);

  protected readonly internships = signal<Internship[]>([]);
  protected readonly isLoading = signal<boolean>(false);
  protected readonly selectedInternship = signal<Internship | null>(null);

  protected readonly searchQuery = signal<string>('');
  protected readonly statusFilter = signal<InternshipStatus | ''>('');

  protected readonly members = signal<InternshipMember[]>([]);
  protected readonly isMembersLoading = signal<boolean>(false);
  protected readonly memberSearchQuery = signal<string>('');

  protected readonly availableInterns = signal<UserSummary[]>([]);
  protected readonly availableMentors = signal<UserSummary[]>([]);

  private searchDebounceTimer?: ReturnType<typeof setTimeout>;

  // Computed filtered lists for instant client-side responsiveness
  protected readonly filteredInternships = computed(() => {
    const q = this.searchQuery().trim().toLowerCase();
    const status = this.statusFilter();
    let list = this.internships();
    if (status) {
      list = list.filter((i) => i.status === status);
    }
    if (q) {
      list = list.filter((i) => i.name.toLowerCase().includes(q));
    }
    return list;
  });

  protected readonly filteredMembers = computed(() => {
    const q = this.memberSearchQuery().trim().toLowerCase();
    const list = this.members();
    if (!q) return list;
    return list.filter(
      (m) =>
        m.intern?.full_name?.toLowerCase().includes(q) ||
        m.intern?.email?.toLowerCase().includes(q),
    );
  });

  // Modals state
  protected isInternshipModalVisible = false;
  protected isSavingInternship = signal<boolean>(false);
  protected readonly editingInternship = signal<Internship | null>(null);

  protected isAddMemberModalVisible = false;
  protected isSavingMember = signal<boolean>(false);

  protected isEditMemberModalVisible = false;
  protected isSavingEditMember = signal<boolean>(false);
  protected readonly selectedMemberForEdit = signal<InternshipMember | null>(null);

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

  protected readonly editMemberForm = this.fb.group({
    intern_name: [{ value: '', disabled: true }],
    intern_email: [{ value: '', disabled: true }],
    status: ['ACTIVE' as MemberStatus, [Validators.required]],
    mentor_id: [null as string | null],
    start_date: ['', [Validators.required]],
    end_date: ['', [Validators.required]],
  });

  ngOnInit(): void {
    this.loadInternships();
    this.loadUsers();
  }

  loadInternships(): void {
    this.isLoading.set(true);
    this.internshipService
      .getInternships(0, 100, this.searchQuery(), this.statusFilter())
      .subscribe({
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

  onSearchChange(value: string): void {
    this.searchQuery.set(value);
    if (this.searchDebounceTimer) {
      clearTimeout(this.searchDebounceTimer);
    }
    this.searchDebounceTimer = setTimeout(() => {
      this.loadInternships();
    }, 300);
  }

  onStatusChange(value: InternshipStatus | ''): void {
    this.statusFilter.set(value);
    this.loadInternships();
  }

  onMemberSearchChange(value: string): void {
    this.memberSearchQuery.set(value);
  }

  loadUsers(): void {
    this.internshipService.getUsers('INTERN').subscribe({
      next: (users) => this.availableInterns.set(users),
      error: (err) => console.error('Không thể tải danh sách Intern:', err),
    });

    this.internshipService.getUsers('MENTOR').subscribe({
      next: (users) => this.availableMentors.set(users),
      error: (err) => console.error('Không thể tải danh sách Mentor:', err),
    });
  }

  selectInternship(internship: Internship): void {
    this.selectedInternship.set(internship);
    this.memberSearchQuery.set('');
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
          this.loadInternships(); // Refresh members_count in table
        },
        error: (err) => {
          this.message.error(
            err?.error?.detail || 'Không thể thêm Intern (có thể đã tồn tại trong đợt).',
          );
          this.isSavingMember.set(false);
        },
      });
  }

  // --- Modal Chỉnh sửa Thực tập sinh ---
  openEditMemberModal(member: InternshipMember): void {
    const current = this.selectedInternship();
    this.selectedMemberForEdit.set(member);

    if (this.availableMentors().length === 0) {
      this.loadUsers();
    }

    if (member.mentor) {
      const exists = this.availableMentors().some((m) => m.id === member.mentor!.id);
      if (!exists) {
        this.availableMentors.update((list) => [...list, member.mentor!]);
      }
    }

    const effectiveStart = member.start_date || current?.start_date || '';
    const effectiveEnd = member.end_date || current?.end_date || '';
    const effectiveMentorId = member.mentor_id || member.mentor?.id || null;

    this.editMemberForm.patchValue({
      intern_name: member.intern?.full_name || 'Thực tập sinh',
      intern_email: member.intern?.email || '—',
      status: member.status || 'ACTIVE',
      mentor_id: effectiveMentorId,
      start_date: effectiveStart,
      end_date: effectiveEnd,
    });
    this.isEditMemberModalVisible = true;
    this.cdr.markForCheck();
  }

  closeEditMemberModal(): void {
    this.isEditMemberModalVisible = false;
    this.selectedMemberForEdit.set(null);
    this.cdr.markForCheck();
  }

  saveEditMember(): void {
    const member = this.selectedMemberForEdit();
    const current = this.selectedInternship();
    if (!member || !current) return;

    if (this.editMemberForm.invalid) {
      this.editMemberForm.markAllAsTouched();
      return;
    }

    const formVal = this.editMemberForm.getRawValue();
    if (formVal.start_date && formVal.end_date && formVal.end_date < formVal.start_date) {
      this.message.error('Ngày kết thúc không được nhỏ hơn ngày bắt đầu.');
      return;
    }

    const payload: UpdateMemberPayload = {
      status: formVal.status ?? undefined,
      start_date: formVal.start_date || undefined,
      end_date: formVal.end_date || undefined,
      mentor_id: formVal.mentor_id || null,
    };

    this.isSavingEditMember.set(true);

    this.internshipService.updateMember(member.id, payload).subscribe({
      next: () => {
        this.message.success('Cập nhật thông tin thực tập sinh thành công!');
        this.isSavingEditMember.set(false);
        this.closeEditMemberModal();
        this.loadMembers(current.id);
        this.loadInternships();
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.message.error(err?.error?.detail || 'Lỗi khi cập nhật thực tập sinh.');
        this.isSavingEditMember.set(false);
        this.cdr.markForCheck();
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
        return 'Đang mở';
      case 'ONGOING':
        return 'Đang diễn ra';
      case 'COMPLETED':
        return 'Đã hoàn thành';
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
        return 'Tạm dừng';
      case 'COMPLETED':
        return 'Hoàn thành';
      default:
        return status;
    }
  }
}
