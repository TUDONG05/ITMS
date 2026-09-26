import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzCardModule } from 'ng-zorro-antd/card';
import { NzDividerModule } from 'ng-zorro-antd/divider';
import { NzFormModule } from 'ng-zorro-antd/form';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzMessageService } from 'ng-zorro-antd/message';
import { NzModalModule } from 'ng-zorro-antd/modal';
import { NzPopconfirmModule } from 'ng-zorro-antd/popconfirm';
import { NzSelectModule } from 'ng-zorro-antd/select';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzTableModule } from 'ng-zorro-antd/table';
import { NzTagModule } from 'ng-zorro-antd/tag';
import { NzTooltipModule } from 'ng-zorro-antd/tooltip';

import {
  CreateUserPayload,
  UpdateUserPayload,
  User,
  UserManagementService,
  UserRole,
  UserStatus,
} from '../../core/api/user-management.service';

@Component({
  selector: 'app-user-management',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    NzButtonModule,
    NzCardModule,
    NzDividerModule,
    NzFormModule,
    NzIconModule,
    NzInputModule,
    NzModalModule,
    NzPopconfirmModule,
    NzSelectModule,
    NzSpinModule,
    NzTableModule,
    NzTagModule,
    NzTooltipModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="user-mgmt-page">
      <!-- Page Header -->
      <div class="page-header">
        <div class="header-titles">
          <h2>Quản lý người dùng</h2>
          <p>Tạo mới, cập nhật thông tin, phân vai trò và khóa/mở tài khoản người dùng.</p>
        </div>
        <button nz-button nzType="primary" (click)="openCreateModal()">
          <span nz-icon nzType="user-add"></span> Thêm người dùng
        </button>
      </div>

      <!-- Filters -->
      <nz-card [nzBordered]="false" class="filter-card">
        <div class="filter-row">
          <nz-input-group nzPrefixIcon="search" class="search-input">
            <input
              nz-input
              placeholder="Tìm theo tên hoặc email..."
              [(ngModel)]="searchText"
              (ngModelChange)="onSearch($event)"
            />
          </nz-input-group>

          <nz-select
            [(ngModel)]="filterRole"
            (ngModelChange)="loadUsers()"
            nzPlaceHolder="Lọc theo vai trò"
            nzAllowClear
            class="filter-select"
          >
            <nz-option nzValue="ADMIN" nzLabel="Admin"></nz-option>
            <nz-option nzValue="MENTOR" nzLabel="Mentor"></nz-option>
            <nz-option nzValue="INTERN" nzLabel="Intern"></nz-option>
          </nz-select>

          <nz-select
            [(ngModel)]="filterStatus"
            (ngModelChange)="loadUsers()"
            nzPlaceHolder="Lọc theo trạng thái"
            nzAllowClear
            class="filter-select"
          >
            <nz-option nzValue="ACTIVE" nzLabel="Đang hoạt động"></nz-option>
            <nz-option nzValue="LOCKED" nzLabel="Đã khóa"></nz-option>
            <nz-option nzValue="INACTIVE" nzLabel="Không hoạt động"></nz-option>
          </nz-select>
        </div>
      </nz-card>

      <!-- Users Table -->
      <nz-card [nzBordered]="false" class="table-card">
        <nz-spin [nzSpinning]="loading()">
          <nz-table
            #userTable
            [nzData]="users()"
            [nzPageSize]="10"
            [nzShowSizeChanger]="true"
            [nzPageSizeOptions]="[10, 20, 50]"
            nzTableLayout="fixed"
          >
            <thead>
              <tr>
                <th nzWidth="220px">Họ tên</th>
                <th>Email</th>
                <th nzWidth="120px">Số điện thoại</th>
                <th nzWidth="110px">Vai trò</th>
                <th nzWidth="130px">Trạng thái</th>
                <th nzWidth="130px" nzAlign="center">Thao tác</th>
              </tr>
            </thead>
            <tbody>
              @for (user of userTable.data; track user.id) {
                <tr [class.row-locked]="user.status === 'LOCKED'">
                  <td>
                    <div class="user-cell">
                      <div class="user-avatar" [class]="'avatar-' + user.role.toLowerCase()">
                        {{ initials(user.full_name) }}
                      </div>
                      <span class="user-fullname">{{ user.full_name }}</span>
                    </div>
                  </td>
                  <td>
                    <span class="email-text">{{ user.email }}</span>
                  </td>
                  <td>{{ user.phone || '—' }}</td>
                  <td>
                    <nz-tag [nzColor]="roleColor(user.role)">{{ roleLabel(user.role) }}</nz-tag>
                  </td>
                  <td>
                    <nz-tag [nzColor]="statusColor(user.status)">
                      <span
                        nz-icon
                        [nzType]="user.status === 'ACTIVE' ? 'check-circle' : 'lock'"
                      ></span>
                      {{ statusLabel(user.status) }}
                    </nz-tag>
                  </td>
                  <td nzAlign="center">
                    <div class="action-buttons">
                      <button
                        nz-button
                        nzType="text"
                        nzSize="small"
                        nz-tooltip
                        nzTooltipTitle="Chỉnh sửa"
                        (click)="openEditModal(user)"
                      >
                        <span nz-icon nzType="edit"></span>
                      </button>

                      @if (user.status === 'ACTIVE') {
                        <button
                          nz-button
                          nzType="text"
                          nzSize="small"
                          nzDanger
                          nz-tooltip
                          nzTooltipTitle="Khóa tài khoản"
                          nz-popconfirm
                          nzPopconfirmTitle="Khóa tài khoản {{ user.full_name }}?"
                          nzPopconfirmPlacement="left"
                          (nzOnConfirm)="lockUser(user)"
                        >
                          <span nz-icon nzType="lock"></span>
                        </button>
                      } @else {
                        <button
                          nz-button
                          nzType="text"
                          nzSize="small"
                          nz-tooltip
                          nzTooltipTitle="Mở khóa tài khoản"
                          nz-popconfirm
                          nzPopconfirmTitle="Mở khóa tài khoản {{ user.full_name }}?"
                          nzPopconfirmPlacement="left"
                          (nzOnConfirm)="unlockUser(user)"
                        >
                          <span nz-icon nzType="unlock"></span>
                        </button>
                      }
                    </div>
                  </td>
                </tr>
              } @empty {
                <tr>
                  <td colspan="6" style="text-align:center; padding: 32px; color: #999;">
                    <span
                      nz-icon
                      nzType="inbox"
                      style="font-size:32px; display:block; margin-bottom:8px;"
                    ></span>
                    Không tìm thấy người dùng nào.
                  </td>
                </tr>
              }
            </tbody>
          </nz-table>
        </nz-spin>
      </nz-card>

      <!-- Create User Modal -->
      <nz-modal
        [(nzVisible)]="showCreateModal"
        nzTitle="Thêm người dùng mới"
        [nzOkLoading]="submitting()"
        nzOkText="Tạo tài khoản"
        nzCancelText="Hủy"
        (nzOnOk)="submitCreateForm()"
        (nzOnCancel)="closeCreateModal()"
      >
        <ng-container *nzModalContent>
          <form nz-form [formGroup]="createForm" nzLayout="vertical">
            <nz-form-item>
              <nz-form-label nzRequired>Email</nz-form-label>
              <nz-form-control nzErrorTip="Email hợp lệ là bắt buộc">
                <input
                  nz-input
                  formControlName="email"
                  placeholder="example@itms.local"
                  type="email"
                />
              </nz-form-control>
            </nz-form-item>
            <nz-form-item>
              <nz-form-label nzRequired>Họ và tên</nz-form-label>
              <nz-form-control nzErrorTip="Họ tên là bắt buộc">
                <input nz-input formControlName="full_name" placeholder="Nguyễn Văn A" />
              </nz-form-control>
            </nz-form-item>
            <nz-form-item>
              <nz-form-label nzRequired>Mật khẩu</nz-form-label>
              <nz-form-control nzErrorTip="Mật khẩu tối thiểu 8 ký tự">
                <input nz-input formControlName="password" placeholder="Mật khẩu" type="password" />
              </nz-form-control>
            </nz-form-item>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
              <nz-form-item>
                <nz-form-label nzRequired>Vai trò</nz-form-label>
                <nz-form-control nzErrorTip="Chọn vai trò">
                  <nz-select formControlName="role" nzPlaceHolder="Chọn vai trò">
                    <nz-option nzValue="ADMIN" nzLabel="Admin"></nz-option>
                    <nz-option nzValue="MENTOR" nzLabel="Mentor"></nz-option>
                    <nz-option nzValue="INTERN" nzLabel="Intern"></nz-option>
                  </nz-select>
                </nz-form-control>
              </nz-form-item>
              <nz-form-item>
                <nz-form-label>Số điện thoại</nz-form-label>
                <nz-form-control>
                  <input nz-input formControlName="phone" placeholder="0xxxxxxxxx" />
                </nz-form-control>
              </nz-form-item>
            </div>
          </form>
        </ng-container>
      </nz-modal>

      <!-- Edit User Modal -->
      <nz-modal
        [(nzVisible)]="showEditModal"
        nzTitle="Chỉnh sửa người dùng"
        [nzOkLoading]="submitting()"
        nzOkText="Lưu thay đổi"
        nzCancelText="Hủy"
        (nzOnOk)="submitEditForm()"
        (nzOnCancel)="closeEditModal()"
      >
        <ng-container *nzModalContent>
          <form nz-form [formGroup]="editForm" nzLayout="vertical">
            <nz-form-item>
              <nz-form-label nzRequired>Họ và tên</nz-form-label>
              <nz-form-control nzErrorTip="Họ tên là bắt buộc">
                <input nz-input formControlName="full_name" placeholder="Nguyễn Văn A" />
              </nz-form-control>
            </nz-form-item>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
              <nz-form-item>
                <nz-form-label nzRequired>Vai trò</nz-form-label>
                <nz-form-control nzErrorTip="Chọn vai trò">
                  <nz-select formControlName="role" nzPlaceHolder="Chọn vai trò">
                    <nz-option nzValue="ADMIN" nzLabel="Admin"></nz-option>
                    <nz-option nzValue="MENTOR" nzLabel="Mentor"></nz-option>
                    <nz-option nzValue="INTERN" nzLabel="Intern"></nz-option>
                  </nz-select>
                </nz-form-control>
              </nz-form-item>
              <nz-form-item>
                <nz-form-label>Số điện thoại</nz-form-label>
                <nz-form-control>
                  <input nz-input formControlName="phone" placeholder="0xxxxxxxxx" />
                </nz-form-control>
              </nz-form-item>
            </div>
          </form>
        </ng-container>
      </nz-modal>
    </div>

    <style>
      .user-mgmt-page {
        display: flex;
        flex-direction: column;
        gap: 16px;
      }
      .page-header {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 12px;
      }
      .page-header h2 {
        margin: 0;
        font-size: 20px;
        font-weight: 600;
      }
      .page-header p {
        margin: 4px 0 0;
        color: #666;
        font-size: 13px;
      }
      .filter-card :ng-deep .ant-card-body {
        padding: 12px 16px;
      }
      .filter-row {
        display: flex;
        gap: 12px;
        flex-wrap: wrap;
        align-items: center;
      }
      .search-input {
        flex: 1;
        min-width: 220px;
        max-width: 360px;
      }
      .filter-select {
        width: 170px;
      }
      .table-card :ng-deep .ant-card-body {
        padding: 0;
      }
      .user-cell {
        display: flex;
        align-items: center;
        gap: 10px;
      }
      .user-avatar {
        width: 34px;
        height: 34px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 13px;
        font-weight: 600;
        color: #fff;
        flex-shrink: 0;
      }
      .avatar-admin {
        background: #1890ff;
      }
      .avatar-mentor {
        background: #fa8c16;
      }
      .avatar-intern {
        background: #52c41a;
      }
      .user-fullname {
        font-weight: 500;
      }
      .email-text {
        color: #555;
        font-size: 13px;
      }
      .action-buttons {
        display: flex;
        gap: 4px;
        justify-content: center;
      }
      .row-locked td {
        opacity: 0.65;
      }
    </style>
  `,
})
export class UserManagementComponent implements OnInit {
  private readonly userSvc = inject(UserManagementService);
  private readonly message = inject(NzMessageService);
  private readonly fb = inject(FormBuilder);

  users = signal<User[]>([]);
  loading = signal(false);
  submitting = signal(false);

  searchText = '';
  filterRole: UserRole | null = null;
  filterStatus: UserStatus | null = null;

  showCreateModal = false;
  showEditModal = false;
  editingUser: User | null = null;

  createForm = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    full_name: ['', [Validators.required]],
    password: ['', [Validators.required, Validators.minLength(8)]],
    role: ['INTERN' as UserRole, [Validators.required]],
    phone: [''],
  });

  editForm = this.fb.nonNullable.group({
    full_name: ['', [Validators.required]],
    role: ['INTERN' as UserRole, [Validators.required]],
    phone: [''],
  });

  ngOnInit(): void {
    this.loadUsers();
  }

  loadUsers(): void {
    this.loading.set(true);
    this.userSvc
      .getUsers({
        role: this.filterRole ?? undefined,
        status: this.filterStatus ?? undefined,
        search: this.searchText.trim() || undefined,
      })
      .subscribe({
        next: (data) => {
          this.users.set(data);
          this.loading.set(false);
        },
        error: () => {
          this.message.error('Không thể tải danh sách người dùng.');
          this.loading.set(false);
        },
      });
  }

  onSearch(text: string): void {
    this.searchText = text;
    this.loadUsers();
  }

  // ---- Create ----
  openCreateModal(): void {
    this.createForm.reset({ role: 'INTERN' });
    this.showCreateModal = true;
  }

  closeCreateModal(): void {
    this.showCreateModal = false;
    this.createForm.reset({ role: 'INTERN' });
  }

  submitCreateForm(): void {
    if (this.createForm.invalid) {
      Object.values(this.createForm.controls).forEach((c) => c.markAsDirty());
      return;
    }
    this.submitting.set(true);
    const raw = this.createForm.getRawValue();
    const payload: CreateUserPayload = {
      email: raw.email.trim(),
      full_name: raw.full_name.trim(),
      password: raw.password,
      role: raw.role,
      phone: raw.phone?.trim() || null,
    };
    this.userSvc.createUser(payload).subscribe({
      next: () => {
        this.message.success(`Tạo tài khoản "${payload.full_name}" thành công!`);
        this.submitting.set(false);
        this.showCreateModal = false;
        this.loadUsers();
      },
      error: (err) => {
        const detail = err?.error?.detail || 'Tạo tài khoản thất bại.';
        this.message.error(detail);
        this.submitting.set(false);
      },
    });
  }

  // ---- Edit ----
  openEditModal(user: User): void {
    this.editingUser = user;
    this.editForm.patchValue({
      full_name: user.full_name,
      role: user.role,
      phone: user.phone ?? '',
    });
    this.showEditModal = true;
  }

  closeEditModal(): void {
    this.showEditModal = false;
    this.editingUser = null;
  }

  submitEditForm(): void {
    if (this.editForm.invalid || !this.editingUser) {
      Object.values(this.editForm.controls).forEach((c) => c.markAsDirty());
      return;
    }
    this.submitting.set(true);
    const raw = this.editForm.getRawValue();
    const payload: UpdateUserPayload = {
      full_name: raw.full_name.trim(),
      role: raw.role,
      phone: raw.phone?.trim() || null,
    };
    this.userSvc.updateUser(this.editingUser.id, payload).subscribe({
      next: (updated) => {
        this.message.success(`Cập nhật "${updated.full_name}" thành công!`);
        this.submitting.set(false);
        this.showEditModal = false;
        this.loadUsers();
      },
      error: () => {
        this.message.error('Cập nhật thất bại. Vui lòng thử lại.');
        this.submitting.set(false);
      },
    });
  }

  // ---- Lock / Unlock ----
  lockUser(user: User): void {
    this.userSvc.updateUserStatus(user.id, { status: 'LOCKED' }).subscribe({
      next: () => {
        this.message.warning(`Đã khóa tài khoản "${user.full_name}".`);
        this.loadUsers();
      },
      error: (err) => {
        const detail = err?.error?.detail || 'Khóa tài khoản thất bại.';
        this.message.error(detail);
      },
    });
  }

  unlockUser(user: User): void {
    this.userSvc.updateUserStatus(user.id, { status: 'ACTIVE' }).subscribe({
      next: () => {
        this.message.success(`Đã mở khóa tài khoản "${user.full_name}".`);
        this.loadUsers();
      },
      error: () => {
        this.message.error('Mở khóa thất bại. Vui lòng thử lại.');
      },
    });
  }

  // ---- Helpers ----
  initials(name: string): string {
    return name
      .split(' ')
      .filter(Boolean)
      .map((w) => w[0].toUpperCase())
      .slice(-2)
      .join('');
  }

  roleLabel(role: UserRole): string {
    return { ADMIN: 'Admin', MENTOR: 'Mentor', INTERN: 'Intern' }[role] ?? role;
  }

  roleColor(role: UserRole): string {
    return { ADMIN: 'blue', MENTOR: 'orange', INTERN: 'green' }[role] ?? 'default';
  }

  statusLabel(status: UserStatus): string {
    return { ACTIVE: 'Hoạt động', LOCKED: 'Đã khóa', INACTIVE: 'Ngừng HĐ' }[status] ?? status;
  }

  statusColor(status: UserStatus): string {
    return { ACTIVE: 'success', LOCKED: 'error', INACTIVE: 'default' }[status] ?? 'default';
  }
}
