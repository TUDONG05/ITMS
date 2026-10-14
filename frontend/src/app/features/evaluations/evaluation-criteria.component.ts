import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { NzAlertModule } from 'ng-zorro-antd/alert';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzCardModule } from 'ng-zorro-antd/card';
import { NzEmptyModule } from 'ng-zorro-antd/empty';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzInputNumberModule } from 'ng-zorro-antd/input-number';
import { NzMessageService } from 'ng-zorro-antd/message';
import { NzModalModule } from 'ng-zorro-antd/modal';
import { NzPopconfirmModule } from 'ng-zorro-antd/popconfirm';
import { NzSelectModule } from 'ng-zorro-antd/select';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzTableModule } from 'ng-zorro-antd/table';
import { NzTagModule } from 'ng-zorro-antd/tag';

import { apiErrorCode, apiMessage } from '../../core/api/api-error';
import {
  CriterionPayload,
  CriterionStatus,
  EvaluationCriterion,
  EvaluationService,
} from '../../core/api/evaluation.service';

interface CriterionForm {
  name: string;
  description: string;
  max_score: number | null;
  weight: number | null;
  status: CriterionStatus;
}

const EMPTY_FORM: CriterionForm = {
  name: '',
  description: '',
  max_score: 10,
  weight: 0,
  status: 'ACTIVE',
};

/** UC-12 (Admin): quản lý tiêu chí, thang điểm và trọng số. */
@Component({
  selector: 'app-evaluation-criteria',
  standalone: true,
  imports: [
    FormsModule,
    NzAlertModule,
    NzButtonModule,
    NzCardModule,
    NzEmptyModule,
    NzInputModule,
    NzInputNumberModule,
    NzModalModule,
    NzPopconfirmModule,
    NzSelectModule,
    NzSpinModule,
    NzTableModule,
    NzTagModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './evaluation-criteria.component.html',
  styleUrl: './evaluation-criteria.component.scss',
})
export class EvaluationCriteriaComponent implements OnInit {
  private readonly evaluationService = inject(EvaluationService);
  private readonly message = inject(NzMessageService);

  protected readonly criteria = signal<EvaluationCriterion[]>([]);
  protected readonly totalActiveWeight = signal(0);
  protected readonly isLoading = signal(true);
  protected readonly loadError = signal<string | null>(null);

  protected readonly isFormOpen = signal(false);
  protected readonly isSaving = signal(false);
  protected readonly editingId = signal<string | null>(null);
  protected readonly form = signal<CriterionForm>({ ...EMPTY_FORM });
  protected readonly formError = signal<string | null>(null);

  ngOnInit(): void {
    this.load();
  }

  protected load(): void {
    this.isLoading.set(true);
    this.loadError.set(null);
    this.evaluationService.listCriteria().subscribe({
      next: (data) => {
        this.criteria.set(data.items);
        this.totalActiveWeight.set(data.total_active_weight);
        this.isLoading.set(false);
      },
      error: (err) => {
        this.isLoading.set(false);
        this.loadError.set(apiMessage(err, 'Không tải được danh sách tiêu chí.'));
      },
    });
  }

  protected openCreate(): void {
    this.editingId.set(null);
    this.form.set({ ...EMPTY_FORM });
    this.formError.set(null);
    this.isFormOpen.set(true);
  }

  protected openEdit(criterion: EvaluationCriterion): void {
    this.editingId.set(criterion.id);
    this.form.set({
      name: criterion.name,
      description: criterion.description ?? '',
      max_score: criterion.max_score,
      weight: criterion.weight,
      status: criterion.status,
    });
    this.formError.set(null);
    this.isFormOpen.set(true);
  }

  protected closeForm(): void {
    this.isFormOpen.set(false);
  }

  protected patchForm(patch: Partial<CriterionForm>): void {
    this.form.update((current) => ({ ...current, ...patch }));
  }

  private validate(form: CriterionForm): string | null {
    if (!form.name.trim()) return 'Vui lòng nhập tên tiêu chí.';
    if (form.max_score === null || form.max_score <= 0 || form.max_score > 100) {
      return 'Thang điểm tối đa phải lớn hơn 0 và không quá 100.';
    }
    if (form.weight === null || form.weight < 0 || form.weight > 100) {
      return 'Trọng số phải từ 0 đến 100.';
    }
    return null;
  }

  protected save(): void {
    const form = this.form();
    const problem = this.validate(form);
    if (problem) {
      this.formError.set(problem);
      return;
    }
    const payload: CriterionPayload = {
      name: form.name.trim(),
      description: form.description.trim() || null,
      max_score: form.max_score as number,
      weight: form.weight as number,
      status: form.status,
    };
    const id = this.editingId();
    this.isSaving.set(true);
    this.formError.set(null);
    const request = id
      ? this.evaluationService.updateCriterion(id, payload)
      : this.evaluationService.createCriterion(payload);
    request.subscribe({
      next: () => {
        this.isSaving.set(false);
        this.isFormOpen.set(false);
        this.message.success(id ? 'Đã cập nhật tiêu chí' : 'Đã thêm tiêu chí');
        this.load();
      },
      error: (err) => {
        this.isSaving.set(false);
        this.formError.set(apiMessage(err, 'Không lưu được tiêu chí.'));
      },
    });
  }

  protected toggleStatus(criterion: EvaluationCriterion): void {
    const next: CriterionStatus = criterion.status === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE';
    this.evaluationService.updateCriterion(criterion.id, { status: next }).subscribe({
      next: () => {
        this.message.success(next === 'ACTIVE' ? 'Đã bật tiêu chí' : 'Đã ngừng áp dụng tiêu chí');
        this.load();
      },
      error: (err) => this.message.error(apiMessage(err, 'Không đổi được trạng thái.')),
    });
  }

  protected remove(criterion: EvaluationCriterion): void {
    this.evaluationService.deleteCriterion(criterion.id).subscribe({
      next: () => {
        this.message.success('Đã xóa tiêu chí');
        this.load();
      },
      error: (err) => {
        const inUse = apiErrorCode(err) === 'CRITERION_IN_USE';
        this.message.error(apiMessage(err, 'Không xóa được tiêu chí.'));
        if (inUse) {
          this.load();
        }
      },
    });
  }
}
