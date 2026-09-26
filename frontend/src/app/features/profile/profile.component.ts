import { SlicePipe } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  inject,
  OnInit,
  signal,
  ViewChild,
} from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { NzAvatarModule } from 'ng-zorro-antd/avatar';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzCardModule } from 'ng-zorro-antd/card';
import { NzDividerModule } from 'ng-zorro-antd/divider';
import { NzFormModule } from 'ng-zorro-antd/form';
import { NzGridModule } from 'ng-zorro-antd/grid';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzMessageService } from 'ng-zorro-antd/message';
import { NzModalModule } from 'ng-zorro-antd/modal';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzTagModule } from 'ng-zorro-antd/tag';
import { NzTooltipModule } from 'ng-zorro-antd/tooltip';
import { finalize } from 'rxjs';
import { AuthService, InternProfileRead, UpdateProfileRequest } from '../../core/api/auth.service';

const ROLE_LABEL: Record<string, string> = {
  INTERN: 'Thực tập sinh',
  MENTOR: 'Mentor',
  ADMIN: 'Quản trị viên',
};

const STATUS_COLOR: Record<string, string> = {
  ACTIVE: 'success',
  LOCKED: 'error',
  INACTIVE: 'default',
};

const STATUS_LABEL: Record<string, string> = {
  ACTIVE: 'Đang hoạt động',
  LOCKED: 'Đã khóa',
  INACTIVE: 'Không hoạt động',
};

const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];
const MAX_BYTES = 2 * 1024 * 1024; // 2 MB

@Component({
  selector: 'app-profile',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    SlicePipe,
    FormsModule,
    ReactiveFormsModule,
    NzAvatarModule,
    NzButtonModule,
    NzCardModule,
    NzDividerModule,
    NzFormModule,
    NzGridModule,
    NzIconModule,
    NzInputModule,
    NzModalModule,
    NzSpinModule,
    NzTagModule,
    NzTooltipModule,
  ],
  template: `
    <!-- Hidden file input for avatar upload -->
    <input
      #fileInput
      type="file"
      accept="image/jpeg,image/png,image/webp,image/gif"
      style="display:none"
      (change)="onFileSelected($event)"
    />

    <div class="profile-page">
      @if (loading()) {
        <div class="profile-loading">
          <nz-spin nzSize="large" />
        </div>
      } @else if (profile()) {
        <!-- Header card -->
        <nz-card class="profile-header-card" [nzBordered]="false">
          <div class="profile-header">
            <nz-avatar
              [nzSize]="80"
              [nzSrc]="profile()!.avatar_url ?? undefined"
              [nzText]="initials()"
              class="profile-avatar"
            />
            <div class="profile-header-info">
              <h2>{{ profile()!.full_name }}</h2>
              <p class="profile-email">
                <span nz-icon nzType="mail"></span>&nbsp;{{ profile()!.email }}
              </p>
              <div class="profile-badges">
                <nz-tag [nzColor]="'blue'">{{ roleLabel() }}</nz-tag>
                <nz-tag [nzColor]="statusColor()">{{ statusLabel() }}</nz-tag>
              </div>
            </div>
            <div class="header-actions">
              @if (!editing()) {
                <button nz-button nzType="primary" (click)="startEdit()">
                  <span nz-icon nzType="edit"></span>Chỉnh sửa hồ sơ
                </button>
              }
              <button nz-button nzType="default" (click)="openPasswordModal()">
                <span nz-icon nzType="key"></span>Đổi mật khẩu
              </button>
            </div>
          </div>
        </nz-card>

        <!-- Mentor card (Intern only) -->
        @if (profile()!.role === 'INTERN') {
          <nz-card class="profile-mentor-card" [nzBordered]="false" nzTitle="Mentor phụ trách">
            @if (profile()!.mentor) {
              <div class="mentor-row">
                <nz-avatar [nzSize]="44" [nzText]="mentorInitials()" />
                <div class="mentor-info">
                  <strong>{{ profile()!.mentor!.full_name }}</strong>
                  <span>
                    <span nz-icon nzType="mail"></span>&nbsp;{{ profile()!.mentor!.email }}
                  </span>
                </div>
              </div>
            } @else {
              <p class="mentor-empty">
                <span nz-icon nzType="info-circle"></span>&nbsp;Chưa được phân công Mentor.
              </p>
            }
          </nz-card>
        }

        <!-- Personal Info / Edit card -->
        <nz-card class="profile-info-card" [nzBordered]="false" nzTitle="Thông tin cá nhân">
          @if (!editing()) {
            <!-- Read-only view -->
            <div nz-row [nzGutter]="[24, 16]">
              <div nz-col [nzSpan]="12">
                <span class="field-label">Họ và tên</span>
                <p class="field-value">
                  {{ profile()!.full_name }}
                  @if (profile()!.role !== 'ADMIN') {
                    <span
                      nz-icon
                      nzType="lock"
                      nz-tooltip
                      nzTooltipTitle="Họ và tên không thể tự thay đổi"
                      class="lock-icon"
                    ></span>
                  }
                </p>
              </div>
              <div nz-col [nzSpan]="12">
                <span class="field-label">Email</span>
                <p class="field-value">
                  {{ profile()!.email }}
                  <span
                    nz-icon
                    nzType="lock"
                    nz-tooltip
                    nzTooltipTitle="Email không thể tự thay đổi"
                    class="lock-icon"
                  ></span>
                </p>
              </div>
              <div nz-col [nzSpan]="12">
                <span class="field-label">Số điện thoại</span>
                <p class="field-value">{{ profile()!.phone ?? '—' }}</p>
              </div>
              <div nz-col [nzSpan]="12">
                <span class="field-label">Ảnh đại diện</span>
                @if (profile()!.avatar_url) {
                  <img
                    [src]="profile()!.avatar_url!"
                    class="avatar-preview-readonly"
                    alt="Ảnh đại diện"
                  />
                } @else {
                  <p class="field-value">—</p>
                }
              </div>
              <div nz-col [nzSpan]="12">
                <span class="field-label">Ngày tạo tài khoản</span>
                <p class="field-value">{{ profile()!.created_at | slice: 0 : 10 }}</p>
              </div>
            </div>
          } @else {
            <!-- Edit form -->
            <form nz-form nzLayout="vertical">
              <!-- Họ và tên: Admin được sửa, các role khác bị khóa -->
              @if (profile()!.role === 'ADMIN') {
                <nz-form-item>
                  <nz-form-label nzRequired>Họ và tên</nz-form-label>
                  <nz-form-control [nzErrorTip]="'Vui lòng nhập họ và tên.'">
                    <input
                      nz-input
                      [(ngModel)]="editName"
                      name="full_name"
                      maxlength="150"
                      placeholder="Nhập họ và tên"
                    />
                  </nz-form-control>
                </nz-form-item>
              } @else {
                <nz-form-item>
                  <nz-form-label>
                    Họ và tên
                    <span
                      nz-icon
                      nzType="lock"
                      nz-tooltip
                      nzTooltipTitle="Họ và tên không thể tự thay đổi"
                      class="lock-icon"
                    ></span>
                  </nz-form-label>
                  <nz-form-control>
                    <input nz-input [value]="profile()!.full_name" disabled />
                  </nz-form-control>
                </nz-form-item>
              }

              <!-- Email: Khóa, không cho sửa -->
              <nz-form-item>
                <nz-form-label>
                  Email
                  <span
                    nz-icon
                    nzType="lock"
                    nz-tooltip
                    nzTooltipTitle="Email không thể tự thay đổi"
                    class="lock-icon"
                  ></span>
                </nz-form-label>
                <nz-form-control>
                  <input nz-input [value]="profile()!.email" disabled />
                </nz-form-control>
              </nz-form-item>

              <!-- Số điện thoại: Được phép sửa -->
              <nz-form-item>
                <nz-form-label>Số điện thoại</nz-form-label>
                <nz-form-control>
                  <input
                    nz-input
                    [(ngModel)]="editPhone"
                    name="phone"
                    maxlength="20"
                    placeholder="Nhập số điện thoại"
                  />
                </nz-form-control>
              </nz-form-item>

              <!-- Chọn ảnh từ máy: Được phép thay đổi -->
              <nz-form-item>
                <nz-form-label>Ảnh đại diện</nz-form-label>
                <nz-form-control>
                  <div
                    class="avatar-upload-area"
                    (click)="triggerFilePicker()"
                    role="button"
                    tabindex="0"
                    (keydown.enter)="triggerFilePicker()"
                  >
                    @if (avatarPreview()) {
                      <img [src]="avatarPreview()!" class="avatar-preview" alt="Xem trước ảnh" />
                      <div class="avatar-upload-overlay">
                        <span nz-icon nzType="camera"></span>
                        <span>Đổi ảnh</span>
                      </div>
                    } @else if (profile()!.avatar_url) {
                      <img
                        [src]="profile()!.avatar_url!"
                        class="avatar-preview"
                        alt="Ảnh đại diện hiện tại"
                      />
                      <div class="avatar-upload-overlay">
                        <span nz-icon nzType="camera"></span>
                        <span>Đổi ảnh</span>
                      </div>
                    } @else {
                      <div class="avatar-upload-placeholder">
                        <span nz-icon nzType="plus" class="upload-icon"></span>
                        <span class="upload-hint">Chọn ảnh từ máy</span>
                        <span class="upload-sub">JPEG, PNG, WebP, GIF · tối đa 2 MB</span>
                      </div>
                    }
                  </div>
                  @if (avatarPreview()) {
                    <button
                      nz-button
                      nzType="text"
                      nzDanger
                      class="remove-avatar-btn"
                      type="button"
                      (click)="removeAvatarPreview($event)"
                    >
                      <span nz-icon nzType="delete"></span>Xóa ảnh vừa chọn
                    </button>
                  }
                </nz-form-control>
              </nz-form-item>

              <div class="form-actions">
                <button nz-button nzType="primary" [nzLoading]="saving()" (click)="save()">
                  Lưu thay đổi
                </button>
                <button nz-button (click)="cancelEdit()">Hủy</button>
              </div>
            </form>
          }
        </nz-card>

        <!-- Security / Password Card -->
        <nz-card class="profile-security-card" [nzBordered]="false" nzTitle="Bảo mật tài khoản">
          <div class="security-row">
            <div>
              <strong>Mật khẩu đăng nhập</strong>
              <p class="security-desc">Đổi mật khẩu định kỳ để nâng cao bảo mật tài khoản.</p>
            </div>
            <button nz-button nzType="default" (click)="openPasswordModal()">
              <span nz-icon nzType="key"></span>Đổi mật khẩu
            </button>
          </div>
        </nz-card>
      } @else if (error()) {
        <nz-card [nzBordered]="false">
          <p class="profile-error"><span nz-icon nzType="warning"></span>&nbsp;{{ error() }}</p>
          <div style="margin-top: 12px; display: flex; gap: 8px;">
            <button nz-button nzType="primary" (click)="loadProfile()">
              <span nz-icon nzType="reload"></span>Thử lại
            </button>
            <button nz-button (click)="goToLogin()">
              <span nz-icon nzType="login"></span>Đăng nhập lại
            </button>
          </div>
        </nz-card>
      }
    </div>

    <!-- Modal Đổi Mật Khẩu -->
    <nz-modal
      [(nzVisible)]="isPasswordModalVisible"
      nzTitle="Đổi mật khẩu"
      (nzOnCancel)="closePasswordModal()"
      [nzFooter]="modalFooter"
    >
      <ng-container *nzModalContent>
        <form nz-form [formGroup]="passwordForm" nzLayout="vertical">
          <nz-form-item>
            <nz-form-label nzRequired>Mật khẩu hiện tại</nz-form-label>
            <nz-form-control [nzErrorTip]="'Vui lòng nhập mật khẩu hiện tại.'">
              <input
                nz-input
                type="password"
                formControlName="currentPassword"
                placeholder="Nhập mật khẩu hiện tại"
                autocomplete="current-password"
              />
            </nz-form-control>
          </nz-form-item>

          <nz-form-item>
            <nz-form-label nzRequired>Mật khẩu mới</nz-form-label>
            <nz-form-control
              [nzErrorTip]="
                passwordForm.controls.newPassword.errors?.['required']
                  ? 'Vui lòng nhập mật khẩu mới.'
                  : 'Mật khẩu mới cần ít nhất 8 ký tự.'
              "
            >
              <input
                nz-input
                type="password"
                formControlName="newPassword"
                placeholder="Tối thiểu 8 ký tự"
                autocomplete="new-password"
              />
            </nz-form-control>
          </nz-form-item>

          <nz-form-item>
            <nz-form-label nzRequired>Xác nhận mật khẩu mới</nz-form-label>
            <nz-form-control
              [nzErrorTip]="
                passwordForm.controls.confirmation.errors?.['required']
                  ? 'Vui lòng xác nhận mật khẩu mới.'
                  : 'Mật khẩu xác nhận không khớp.'
              "
            >
              <input
                nz-input
                type="password"
                formControlName="confirmation"
                placeholder="Nhập lại mật khẩu mới"
                autocomplete="new-password"
              />
            </nz-form-control>
          </nz-form-item>
        </form>
      </ng-container>
      <ng-template #modalFooter>
        <button nz-button nzType="default" (click)="closePasswordModal()">Hủy</button>
        <button
          nz-button
          nzType="primary"
          [nzLoading]="isSubmittingPassword()"
          (click)="submitChangePassword()"
        >
          Cập nhật mật khẩu
        </button>
      </ng-template>
    </nz-modal>
  `,
  styles: [
    `
      .profile-page {
        display: flex;
        flex-direction: column;
        gap: 16px;
        max-width: 800px;
      }

      .profile-loading {
        display: flex;
        justify-content: center;
        padding: 64px 0;
      }

      .profile-header {
        display: flex;
        align-items: center;
        gap: 20px;
        flex-wrap: wrap;
      }

      .profile-header-info {
        flex: 1;
        min-width: 200px;
      }

      .profile-header-info h2 {
        margin: 0 0 4px;
        font-size: 20px;
        font-weight: 600;
      }

      .profile-email {
        margin: 0 0 8px;
        color: #595959;
      }

      .profile-badges {
        display: flex;
        gap: 8px;
      }

      .header-actions {
        display: flex;
        gap: 8px;
        align-self: flex-start;
        margin-left: auto;
      }

      .mentor-row {
        display: flex;
        align-items: center;
        gap: 14px;
      }

      .mentor-info {
        display: flex;
        flex-direction: column;
        gap: 2px;
      }

      .mentor-info strong {
        font-size: 15px;
      }

      .mentor-info span {
        color: #595959;
        font-size: 13px;
      }

      .mentor-empty {
        color: #8c8c8c;
        margin: 0;
      }

      .field-label {
        display: block;
        font-size: 12px;
        color: #8c8c8c;
        margin-bottom: 2px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
      }

      .field-value {
        margin: 0;
        font-size: 14px;
        color: #262626;
      }

      .lock-icon {
        margin-left: 4px;
        color: #bfbfbf;
        cursor: help;
      }

      /* ── Avatar uploader ── */

      .avatar-upload-area {
        position: relative;
        width: 120px;
        height: 120px;
        border-radius: 8px;
        border: 2px dashed #d9d9d9;
        cursor: pointer;
        overflow: hidden;
        transition: border-color 0.2s;
        background: #fafafa;
      }

      .avatar-upload-area:hover {
        border-color: #1890ff;
      }

      .avatar-preview,
      .avatar-preview-readonly {
        width: 100%;
        height: 100%;
        object-fit: cover;
        display: block;
      }

      .avatar-preview-readonly {
        width: 80px;
        height: 80px;
        border-radius: 6px;
        border: 1px solid #f0f0f0;
      }

      .avatar-upload-overlay {
        position: absolute;
        inset: 0;
        background: rgba(0, 0, 0, 0.45);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 4px;
        color: #fff;
        font-size: 12px;
        opacity: 0;
        transition: opacity 0.2s;
      }

      .avatar-upload-area:hover .avatar-upload-overlay {
        opacity: 1;
      }

      .avatar-upload-placeholder {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 100%;
        gap: 6px;
        padding: 8px;
        text-align: center;
      }

      .upload-icon {
        font-size: 22px;
        color: #8c8c8c;
      }

      .upload-hint {
        font-size: 13px;
        color: #595959;
      }

      .upload-sub {
        font-size: 11px;
        color: #bfbfbf;
        line-height: 1.3;
      }

      .remove-avatar-btn {
        margin-top: 6px;
        padding-left: 0;
        font-size: 13px;
      }

      /* ── Security section ── */

      .security-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
      }

      .security-desc {
        margin: 4px 0 0;
        color: #8c8c8c;
        font-size: 13px;
      }

      /* ── Form actions ── */

      .form-actions {
        display: flex;
        gap: 8px;
        margin-top: 8px;
      }

      .profile-error {
        color: #ff4d4f;
      }
    `,
  ],
})
export class ProfileComponent implements OnInit {
  @ViewChild('fileInput') private readonly fileInputRef!: ElementRef<HTMLInputElement>;

  private readonly authService = inject(AuthService);
  private readonly message = inject(NzMessageService);
  private readonly formBuilder = inject(FormBuilder).nonNullable;
  private readonly router = inject(Router);

  protected readonly loading = signal(true);
  protected readonly saving = signal(false);
  protected readonly editing = signal(false);
  protected readonly profile = signal<InternProfileRead | null>(null);
  protected readonly error = signal<string | null>(null);

  /** Ảnh mới được chọn từ máy (data URL để preview) */
  protected readonly avatarPreview = signal<string | null>(null);
  /** File thực sự để upload khi Save */
  private pendingFile: File | null = null;

  protected editName = '';
  protected editPhone = '';

  /** Quản lý Modal Đổi Mật Khẩu */
  protected isPasswordModalVisible = false;
  protected readonly isSubmittingPassword = signal(false);

  protected readonly passwordForm = this.formBuilder.group({
    currentPassword: ['', Validators.required],
    newPassword: ['', [Validators.required, Validators.minLength(8)]],
    confirmation: ['', Validators.required],
  });

  ngOnInit(): void {
    this.loadProfile();
  }

  protected loadProfile(): void {
    this.loading.set(true);
    this.error.set(null);
    this.authService.getProfile().subscribe({
      next: (data) => {
        this.profile.set(data);
        this.loading.set(false);
      },
      error: (err: { status?: number }) => {
        if (err.status === 401) {
          this.error.set('Phiên đăng nhập đã hết hạn hoặc không hợp lệ. Vui lòng đăng nhập lại.');
        } else {
          this.error.set('Không thể tải thông tin hồ sơ. Vui lòng thử lại.');
        }
        this.loading.set(false);
      },
    });
  }

  protected goToLogin(): void {
    this.authService.clearSession();
    void this.router.navigate(['/login']);
  }

  protected initials(): string {
    const name = this.profile()?.full_name ?? '';
    return name
      .split(' ')
      .map((w) => w[0])
      .slice(-2)
      .join('')
      .toUpperCase();
  }

  protected mentorInitials(): string {
    const name = this.profile()?.mentor?.full_name ?? '';
    return name
      .split(' ')
      .map((w) => w[0])
      .slice(-2)
      .join('')
      .toUpperCase();
  }

  protected roleLabel(): string {
    return ROLE_LABEL[this.profile()?.role ?? ''] ?? this.profile()?.role ?? '';
  }

  protected statusColor(): string {
    return STATUS_COLOR[this.profile()?.status ?? ''] ?? 'default';
  }

  protected statusLabel(): string {
    return STATUS_LABEL[this.profile()?.status ?? ''] ?? this.profile()?.status ?? '';
  }

  protected startEdit(): void {
    const p = this.profile()!;
    this.editName = p.full_name;
    this.editPhone = p.phone ?? '';
    this.avatarPreview.set(null);
    this.pendingFile = null;
    this.editing.set(true);
  }

  protected cancelEdit(): void {
    this.avatarPreview.set(null);
    this.pendingFile = null;
    this.editing.set(false);
  }

  /** Mở hộp thoại chọn file */
  protected triggerFilePicker(): void {
    this.fileInputRef.nativeElement.value = '';
    this.fileInputRef.nativeElement.click();
  }

  /** Xử lý khi người dùng chọn file */
  protected onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;

    if (!ALLOWED_TYPES.includes(file.type)) {
      this.message.error('Chỉ chấp nhận ảnh JPEG, PNG, WebP hoặc GIF.');
      return;
    }
    if (file.size > MAX_BYTES) {
      this.message.error('Kích thước ảnh không được vượt quá 2 MB.');
      return;
    }

    this.pendingFile = file;
    const reader = new FileReader();
    reader.onload = () => this.avatarPreview.set(reader.result as string);
    reader.readAsDataURL(file);
  }

  /** Hủy ảnh đã chọn (giữ nguyên ảnh cũ) */
  protected removeAvatarPreview(event: MouseEvent): void {
    event.stopPropagation();
    this.avatarPreview.set(null);
    this.pendingFile = null;
  }

  protected save(): void {
    if (this.saving()) return;
    this.saving.set(true);

    if (this.pendingFile) {
      // Bước 1: upload ảnh trước
      this.authService.uploadAvatar(this.pendingFile).subscribe({
        next: (updated: InternProfileRead) => {
          this.profile.set(updated);
          this.pendingFile = null;
          this.avatarPreview.set(null);
          // Bước 2: lưu số điện thoại nếu có thay đổi
          this.saveProfileFields(updated);
        },
        error: () => {
          this.saving.set(false);
          this.message.error('Upload ảnh thất bại. Vui lòng thử lại.');
        },
      });
    } else {
      this.saveProfileFields(this.profile()!);
    }
  }

  private saveProfileFields(current: InternProfileRead): void {
    const isAdmin = current.role === 'ADMIN';
    const payload: UpdateProfileRequest = {
      full_name: isAdmin ? this.editName.trim() || null : null,
      phone: this.editPhone.trim() || null,
      avatar_url: null, // avatar xử lý qua uploadAvatar riêng
    };

    const nameChanged = isAdmin && payload.full_name !== current.full_name;
    const phoneChanged = payload.phone !== (current.phone ?? null);

    if (!nameChanged && !phoneChanged) {
      this.editing.set(false);
      this.saving.set(false);
      this.message.success('Cập nhật hồ sơ thành công!');
      return;
    }

    this.authService.updateProfile(payload).subscribe({
      next: (updated: InternProfileRead) => {
        this.profile.set(updated);
        this.editing.set(false);
        this.saving.set(false);
        this.message.success('Cập nhật hồ sơ thành công!');
      },
      error: (err: { error?: { error?: { code?: string; message?: string } } }) => {
        this.saving.set(false);
        const code = err.error?.error?.code;
        if (code === 'INVALID_FULL_NAME') {
          this.message.error('Họ và tên không được để trống.');
        } else {
          this.message.error('Cập nhật thất bại. Vui lòng thử lại.');
        }
      },
    });
  }

  /** Mở modal đổi mật khẩu */
  protected openPasswordModal(): void {
    this.passwordForm.reset();
    this.isPasswordModalVisible = true;
  }

  /** Đóng modal đổi mật khẩu */
  protected closePasswordModal(): void {
    this.isPasswordModalVisible = false;
  }

  /** Submit đổi mật khẩu */
  protected submitChangePassword(): void {
    if (this.passwordForm.invalid) {
      this.passwordForm.markAllAsTouched();
      return;
    }

    const { currentPassword, newPassword, confirmation } = this.passwordForm.getRawValue();

    if (newPassword !== confirmation) {
      this.passwordForm.controls.confirmation.setErrors({ mismatch: true });
      this.message.error('Mật khẩu xác nhận không khớp.');
      return;
    }

    this.isSubmittingPassword.set(true);
    this.authService
      .changePassword({ current_password: currentPassword, new_password: newPassword })
      .pipe(finalize(() => this.isSubmittingPassword.set(false)))
      .subscribe({
        next: () => {
          this.isPasswordModalVisible = false;
          this.message.success('Đổi mật khẩu thành công. Vui lòng đăng nhập lại.');
          this.authService.clearSession();
          setTimeout(() => void this.router.navigate(['/login']), 1200);
        },
        error: (error: { error?: { error?: { message?: string } } }) => {
          const msg = error.error?.error?.message ?? 'Đổi mật khẩu thất bại. Vui lòng thử lại.';
          this.message.error(msg);
        },
      });
  }
}
