import { DatePipe } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  OnInit,
  computed,
  inject,
  input,
  signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzCardModule } from 'ng-zorro-antd/card';
import { NzCheckboxModule } from 'ng-zorro-antd/checkbox';
import { NzDrawerModule } from 'ng-zorro-antd/drawer';
import { NzEmptyModule } from 'ng-zorro-antd/empty';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzMessageService } from 'ng-zorro-antd/message';
import { NzModalModule, NzModalService } from 'ng-zorro-antd/modal';
import { NzPopconfirmModule } from 'ng-zorro-antd/popconfirm';
import { NzProgressModule } from 'ng-zorro-antd/progress';
import { NzRadioModule } from 'ng-zorro-antd/radio';
import { NzSelectModule } from 'ng-zorro-antd/select';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzTableModule } from 'ng-zorro-antd/table';
import { NzTagModule } from 'ng-zorro-antd/tag';

import {
  AttemptResult,
  AttemptStarted,
  LearningContentDetail,
  LearningContentItem,
  LearningContentType,
  LearningPhase,
  LearningQuizSummary,
  LearningRoadmap,
  LearningService,
  ProgressStatus,
  QuestionResult,
  QuizQuestion,
  QuizResults,
} from '../../core/api/learning.service';

export type LearningView = 'roadmap' | 'documents' | 'quizzes';

interface AnswerState {
  keys: string[];
  text: string;
}

interface ContentRow extends LearningContentItem {
  phase_name: string;
}

interface QuizRow extends LearningQuizSummary {
  phase_name: string;
}

const STATUS_LABEL: Record<ProgressStatus, string> = {
  NOT_STARTED: 'Chưa học',
  IN_PROGRESS: 'Đang học',
  COMPLETED: 'Hoàn thành',
};

const STATUS_COLOR: Record<ProgressStatus, string> = {
  NOT_STARTED: 'default',
  IN_PROGRESS: 'processing',
  COMPLETED: 'success',
};

const TYPE_LABEL: Record<LearningContentType, string> = {
  LESSON: 'Bài học',
  DOCUMENT: 'Tài liệu',
  VIDEO: 'Video',
  LINK: 'Liên kết',
};

const QUESTION_TYPE_LABEL: Record<string, string> = {
  SINGLE_CHOICE: 'Chọn một đáp án',
  MULTIPLE_CHOICE: 'Chọn nhiều đáp án',
  TRUE_FALSE: 'Đúng / Sai',
  TEXT: 'Trả lời ngắn',
};

function apiMessage(err: unknown, fallback: string): string {
  const body = (err as { error?: { error?: { message?: unknown }; detail?: unknown } })?.error;
  if (typeof body?.error?.message === 'string') return body.error.message;
  if (typeof body?.detail === 'string') return body.detail;
  return fallback;
}

@Component({
  selector: 'app-learning',
  standalone: true,
  imports: [
    DatePipe,
    FormsModule,
    NzButtonModule,
    NzCardModule,
    NzCheckboxModule,
    NzDrawerModule,
    NzEmptyModule,
    NzIconModule,
    NzInputModule,
    NzModalModule,
    NzPopconfirmModule,
    NzProgressModule,
    NzRadioModule,
    NzSelectModule,
    NzSpinModule,
    NzTableModule,
    NzTagModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './learning.component.html',
  styleUrl: './learning.component.scss',
})
export class LearningComponent implements OnInit {
  private readonly learningService = inject(LearningService);
  private readonly message = inject(NzMessageService);
  private readonly modal = inject(NzModalService);
  private readonly destroyRef = inject(DestroyRef);

  /** Màn hình đang mở: lấy từ mục được chọn trong menu của dashboard. */
  readonly view = input<string>('roadmap');

  protected readonly roadmap = signal<LearningRoadmap | null>(null);
  protected readonly isLoading = signal(true);
  protected readonly loadError = signal<string | null>(null);

  // ── Tài liệu ──
  protected readonly typeFilter = signal<LearningContentType | ''>('');
  protected readonly typeOptions = (Object.keys(TYPE_LABEL) as LearningContentType[]).map(
    (value) => ({ value, label: TYPE_LABEL[value] }),
  );

  protected readonly allContents = computed<ContentRow[]>(() =>
    (this.roadmap()?.phases ?? []).flatMap((phase) =>
      phase.contents.map((content) => ({ ...content, phase_name: phase.name })),
    ),
  );

  protected readonly filteredContents = computed(() => {
    const type = this.typeFilter();
    return type
      ? this.allContents().filter((content) => content.type === type)
      : this.allContents();
  });

  protected readonly allQuizzes = computed<QuizRow[]>(() =>
    (this.roadmap()?.phases ?? []).flatMap((phase) =>
      phase.quizzes.map((quiz) => ({ ...quiz, phase_name: phase.name })),
    ),
  );

  // ── Chi tiết nội dung ──
  protected readonly isContentOpen = signal(false);
  protected readonly isContentLoading = signal(false);
  protected readonly isCompleting = signal(false);
  protected readonly selectedContent = signal<LearningContentDetail | null>(null);

  // ── Làm bài kiểm tra ──
  protected readonly isQuizOpen = signal(false);
  protected readonly isStartingQuiz = signal(false);
  protected readonly isSubmittingQuiz = signal(false);
  protected readonly attempt = signal<AttemptStarted | null>(null);
  protected readonly answers = signal<Record<string, AnswerState>>({});
  protected readonly attemptResult = signal<AttemptResult | null>(null);
  protected readonly remainingSeconds = signal(0);

  protected readonly timeLabel = computed(() => {
    const total = this.remainingSeconds();
    const minutes = Math.floor(total / 60);
    const seconds = total % 60;
    return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
  });

  protected readonly answeredCount = computed(() => {
    const current = this.attempt();
    if (!current) return 0;
    const state = this.answers();
    return current.questions.filter((question) => this.hasAnswer(question, state)).length;
  });

  private readonly resultByQuestion = computed(() => {
    const map = new Map<string, QuestionResult>();
    for (const item of this.attemptResult()?.questions ?? []) {
      map.set(item.question_id, item);
    }
    return map;
  });

  // ── Kết quả các lần làm ──
  protected readonly isResultsOpen = signal(false);
  protected readonly isResultsLoading = signal(false);
  protected readonly quizResults = signal<QuizResults | null>(null);

  private timerId: ReturnType<typeof setInterval> | null = null;

  constructor() {
    this.destroyRef.onDestroy(() => this.stopTimer());
  }

  ngOnInit(): void {
    this.loadRoadmap();
  }

  protected loadRoadmap(silent = false): void {
    if (!silent) {
      this.isLoading.set(true);
    }
    this.loadError.set(null);
    this.learningService.getRoadmap().subscribe({
      next: (data) => {
        this.roadmap.set(data);
        this.isLoading.set(false);
      },
      error: (err) => {
        if (!silent) {
          this.roadmap.set(null);
          this.loadError.set(apiMessage(err, 'Không tải được lộ trình học tập.'));
        }
        this.isLoading.set(false);
      },
    });
  }

  // ── Hiển thị ──
  protected statusLabel(status: ProgressStatus): string {
    return STATUS_LABEL[status];
  }

  protected statusColor(status: ProgressStatus): string {
    return STATUS_COLOR[status];
  }

  protected typeLabel(type: LearningContentType): string {
    return TYPE_LABEL[type];
  }

  protected questionTypeLabel(type: string): string {
    return QUESTION_TYPE_LABEL[type] ?? type;
  }

  /** Chỉ cho mở liên kết http(s) hoặc đường dẫn nội bộ. */
  protected safeUrl(url: string | null): string | null {
    if (!url) return null;
    return /^(https?:\/\/|\/)/i.test(url.trim()) ? url.trim() : null;
  }

  protected phaseTrack(_: number, phase: LearningPhase): string {
    return phase.id;
  }

  // ── Nội dung đào tạo ──
  protected openContent(contentId: string): void {
    this.isContentOpen.set(true);
    this.isContentLoading.set(true);
    this.selectedContent.set(null);
    this.learningService.getContent(contentId).subscribe({
      next: (detail) => {
        this.selectedContent.set(detail);
        this.isContentLoading.set(false);
        if (detail.status === 'NOT_STARTED') {
          this.recordStart(detail);
        }
      },
      error: (err) => {
        this.isContentLoading.set(false);
        this.isContentOpen.set(false);
        this.message.error(apiMessage(err, 'Không tải được nội dung đào tạo.'));
      },
    });
  }

  private recordStart(detail: LearningContentDetail): void {
    this.learningService.startContent(detail.id).subscribe({
      next: (progress) => {
        this.selectedContent.update((current) =>
          current && current.id === detail.id
            ? { ...current, status: progress.status, progress_percent: progress.progress_percent }
            : current,
        );
        this.loadRoadmap(true);
      },
      error: () => undefined,
    });
  }

  protected closeContent(): void {
    this.isContentOpen.set(false);
    this.selectedContent.set(null);
  }

  protected completeContent(): void {
    const detail = this.selectedContent();
    if (!detail) return;
    this.isCompleting.set(true);
    this.learningService.completeContent(detail.id).subscribe({
      next: (progress) => {
        this.isCompleting.set(false);
        this.selectedContent.set({
          ...detail,
          status: progress.status,
          progress_percent: progress.progress_percent,
          completed_at: progress.completed_at,
        });
        this.message.success('Đã ghi nhận hoàn thành nội dung');
        this.loadRoadmap(true);
      },
      error: (err) => {
        this.isCompleting.set(false);
        this.message.error(apiMessage(err, 'Không ghi nhận được tiến độ.'));
      },
    });
  }

  // ── Làm bài kiểm tra ──
  protected confirmStartQuiz(quiz: LearningQuizSummary): void {
    const remaining = Math.max(quiz.max_attempts - quiz.attempts_used, 0);
    this.modal.confirm({
      nzTitle: `Làm bài: ${quiz.title}`,
      nzContent:
        `Thời gian làm bài ${quiz.duration_minutes} phút, điểm đạt từ ${quiz.pass_score}. ` +
        `Bạn còn ${remaining} lượt. Đồng hồ bắt đầu chạy ngay khi vào bài ` +
        `và hết giờ thì bài bị tính 0 điểm. Nếu đang có bài làm dở, bạn sẽ được tiếp tục bài đó.`,
      nzOkText: 'Bắt đầu',
      nzCancelText: 'Để sau',
      nzOnOk: () => this.startQuiz(quiz.id),
    });
  }

  private startQuiz(quizId: string): void {
    this.isStartingQuiz.set(true);
    this.learningService.startAttempt(quizId).subscribe({
      next: (started) => {
        this.isStartingQuiz.set(false);
        this.attempt.set(started);
        this.answers.set({});
        this.attemptResult.set(null);
        this.isQuizOpen.set(true);
        this.startTimer(started.expires_at);
        if (started.resumed) {
          this.message.info('Tiếp tục bài làm đang dở của bạn');
        }
        this.loadRoadmap(true);
      },
      error: (err) => {
        this.isStartingQuiz.set(false);
        this.message.error(apiMessage(err, 'Không bắt đầu được bài kiểm tra.'));
        this.loadRoadmap(true);
      },
    });
  }

  private startTimer(expiresAt: string): void {
    this.stopTimer();
    const deadline = new Date(expiresAt).getTime();
    const tick = (): void => {
      const left = Math.max(0, Math.floor((deadline - Date.now()) / 1000));
      this.remainingSeconds.set(left);
      if (left === 0) {
        this.stopTimer();
        if (this.attempt() && !this.attemptResult()) {
          this.message.warning('Hết giờ, hệ thống đang nộp bài của bạn');
          this.submitAttempt();
        }
      }
    };
    tick();
    if (this.remainingSeconds() > 0) {
      this.timerId = setInterval(tick, 1000);
    }
  }

  private stopTimer(): void {
    if (this.timerId !== null) {
      clearInterval(this.timerId);
      this.timerId = null;
    }
  }

  protected selectedKey(questionId: string): string | null {
    return this.answers()[questionId]?.keys[0] ?? null;
  }

  protected setSingle(questionId: string, key: string): void {
    this.answers.update((state) => ({ ...state, [questionId]: { keys: [key], text: '' } }));
  }

  protected isChecked(questionId: string, key: string): boolean {
    return this.answers()[questionId]?.keys.includes(key) ?? false;
  }

  protected toggleKey(questionId: string, key: string, checked: boolean): void {
    this.answers.update((state) => {
      const current = state[questionId]?.keys ?? [];
      const keys = checked
        ? current.includes(key)
          ? current
          : [...current, key]
        : current.filter((item) => item !== key);
      return { ...state, [questionId]: { keys, text: '' } };
    });
  }

  protected textValue(questionId: string): string {
    return this.answers()[questionId]?.text ?? '';
  }

  protected setText(questionId: string, value: string): void {
    this.answers.update((state) => ({ ...state, [questionId]: { keys: [], text: value } }));
  }

  private hasAnswer(question: QuizQuestion, state: Record<string, AnswerState>): boolean {
    const answer = state[question.id];
    if (!answer) return false;
    return question.type === 'TEXT' ? answer.text.trim().length > 0 : answer.keys.length > 0;
  }

  protected submitAttempt(): void {
    const current = this.attempt();
    if (!current || this.isSubmittingQuiz() || this.attemptResult()) return;
    this.stopTimer();
    this.isSubmittingQuiz.set(true);
    const state = this.answers();
    const payload = current.questions.map((question) => ({
      question_id: question.id,
      selected_keys: question.type === 'TEXT' ? [] : (state[question.id]?.keys ?? []),
      text: question.type === 'TEXT' ? (state[question.id]?.text ?? '') : null,
    }));
    this.learningService.submitAttempt(current.attempt_id, payload).subscribe({
      next: (result) => {
        this.isSubmittingQuiz.set(false);
        this.attemptResult.set(result);
        this.loadRoadmap(true);
      },
      error: (err) => {
        this.isSubmittingQuiz.set(false);
        const code = (err as { error?: { error?: { code?: string } } })?.error?.error?.code;
        this.message.error(apiMessage(err, 'Nộp bài thất bại, vui lòng thử lại.'));
        if (code === 'ATTEMPT_EXPIRED' || code === 'ATTEMPT_ALREADY_SUBMITTED') {
          this.closeQuiz();
          this.loadRoadmap(true);
        } else if (this.remainingSeconds() > 0) {
          this.startTimer(current.expires_at);
        }
      },
    });
  }

  protected closeQuiz(): void {
    this.stopTimer();
    this.isQuizOpen.set(false);
    this.attempt.set(null);
    this.attemptResult.set(null);
    this.answers.set({});
  }

  protected resultFor(questionId: string): QuestionResult | null {
    return this.resultByQuestion().get(questionId) ?? null;
  }

  // ── Kết quả các lần làm bài ──
  protected openResults(quiz: LearningQuizSummary): void {
    this.isResultsOpen.set(true);
    this.isResultsLoading.set(true);
    this.quizResults.set(null);
    this.learningService.getQuizResults(quiz.id).subscribe({
      next: (data) => {
        this.quizResults.set(data);
        this.isResultsLoading.set(false);
      },
      error: (err) => {
        this.isResultsLoading.set(false);
        this.isResultsOpen.set(false);
        this.message.error(apiMessage(err, 'Không tải được kết quả bài kiểm tra.'));
      },
    });
  }

  protected closeResults(): void {
    this.isResultsOpen.set(false);
    this.quizResults.set(null);
  }
}
