import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  ElementRef,
  HostListener,
  ViewChild,
  computed,
  inject,
  input,
  signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzSelectModule } from 'ng-zorro-antd/select';
import { NzSpinModule } from 'ng-zorro-antd/spin';

import {
  AssistantConversationSummary,
  AssistantMessage,
  AssistantService,
} from '../../core/api/assistant.service';

type AssistantRole = 'ADMIN' | 'MENTOR' | 'INTERN';

@Component({
  selector: 'app-assistant-chat',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, NzButtonModule, NzIconModule, NzSelectModule, NzSpinModule],
  template: `
    @if (!visible()) {
      <button
        #launcher
        class="assistant-launcher"
        type="button"
        aria-label="Mở Trợ lý dữ liệu ITMS"
        (click)="open()"
      >
        <img src="/chat_bot_logo.png" alt="" />
      </button>
    }

    @if (visible()) {
      <section
        class="assistant-window"
        role="dialog"
        aria-modal="false"
        aria-labelledby="assistant-title"
      >
        <header class="assistant-header">
          <div class="assistant-brand">
            <span class="assistant-avatar" aria-hidden="true">
              <img src="/chat_bot_logo.png" alt="" />
            </span>
            <span class="assistant-brand__text">
              <strong id="assistant-title">Trợ lý dữ liệu ITMS</strong>
              <small>Tra cứu theo quyền của bạn</small>
            </span>
          </div>
          <div class="assistant-header__actions">
            <button
              type="button"
              aria-label="Mở lịch sử hội thoại"
              [attr.aria-expanded]="historyOpen()"
              (click)="historyOpen.set(!historyOpen())"
            >
              <span nz-icon nzType="file-text" aria-hidden="true"></span>
            </button>
            <button type="button" aria-label="Đóng trợ lý" (click)="close()">
              <span class="assistant-close" aria-hidden="true">×</span>
            </button>
          </div>
        </header>

        @if (historyOpen()) {
          <div class="assistant-history">
            <nz-select
              aria-label="Lịch sử hội thoại"
              nzPlaceHolder="Chọn hội thoại cũ"
              nzNotFoundContent="Chưa có hội thoại"
              [nzLoading]="isLoadingConversations()"
              [nzDisabled]="isSending()"
              [ngModel]="activeConversationId()"
              (ngModelChange)="loadConversation($event)"
            >
              @for (conversation of conversations(); track conversation.id) {
                <nz-option
                  [nzValue]="conversation.id"
                  [nzLabel]="conversation.title || 'Hội thoại không tiêu đề'"
                />
              }
            </nz-select>
            <button
              nz-button
              type="button"
              aria-label="Bắt đầu cuộc trò chuyện mới"
              [disabled]="isSending()"
              (click)="startNewConversation()"
            >
              <span nz-icon nzType="plus" aria-hidden="true"></span>
            </button>
          </div>
        }

        @if (loadError()) {
          <div class="assistant-alert" role="alert">
            <span>{{ loadError() }}</span>
            <button nz-button nzType="link" type="button" (click)="reloadCurrent()">Tải lại</button>
          </div>
        }

        <div
          #messageLog
          class="assistant-messages"
          role="log"
          aria-label="Nội dung hội thoại"
          aria-live="polite"
          aria-relevant="additions"
        >
          @if (isLoadingMessages()) {
            <div class="assistant-state" role="status">
              <nz-spin nzSimple></nz-spin>
              <span>Đang tải hội thoại…</span>
            </div>
          } @else if (messages().length === 0) {
            <div class="assistant-welcome">
              <span class="assistant-message-avatar" aria-hidden="true">
                <img src="/chat_bot_logo.png" alt="" />
              </span>
              <div class="assistant-bubble">
                Chào bạn! Tôi có thể giúp tra cứu roadmap, tiến độ, task, deadline, kết quả quiz và
                đánh giá.
              </div>
            </div>
          } @else {
            @for (message of messages(); track message.id) {
              <article
                class="assistant-message"
                [class.assistant-message--user]="message.role === 'USER'"
              >
                @if (message.role !== 'USER') {
                  <span class="assistant-message-avatar" aria-hidden="true">
                    <img src="/chat_bot_logo.png" alt="" />
                  </span>
                }
                <div class="assistant-message__body">
                  @if (message.role === 'USER') {
                    <div class="assistant-bubble">{{ message.content }}</div>
                  } @else {
                    <div
                      class="assistant-bubble"
                      [innerHTML]="formatAssistantMessage(message.content)"
                    ></div>
                  }
                  @if (message.citations?.length) {
                    <div class="assistant-citations" aria-label="Nguồn dữ liệu">
                      @for (citation of message.citations; track citation.tool) {
                        <span>
                          <span nz-icon nzType="file-text" aria-hidden="true"></span>
                          {{ citation.label }}
                        </span>
                      }
                    </div>
                  }
                </div>
              </article>
            }
            @if (isSending()) {
              <div class="assistant-message assistant-message--pending" role="status">
                <span class="assistant-message-avatar" aria-hidden="true">
                  <img src="/chat_bot_logo.png" alt="" />
                </span>
                <div class="assistant-bubble">
                  <nz-spin nzSimple></nz-spin>
                  <span>Đang phân tích dữ liệu…</span>
                </div>
              </div>
            }
          }
        </div>

        <div class="assistant-suggestions" aria-label="Câu hỏi gợi ý">
          @for (suggestion of suggestions(); track suggestion) {
            <button type="button" [disabled]="isSending()" (click)="useSuggestion(suggestion)">
              {{ suggestion }}
            </button>
          }
        </div>

        <div class="assistant-composer">
          @if (sendError()) {
            <div class="assistant-send-error" role="alert">{{ sendError() }}</div>
          }
          <div class="assistant-input-shell">
            <label class="sr-only" for="assistant-question">Câu hỏi cho Trợ lý dữ liệu ITMS</label>
            <textarea
              #composer
              id="assistant-question"
              name="assistant-question"
              rows="1"
              maxlength="2000"
              autocomplete="off"
              placeholder="Nhập câu hỏi…"
              [disabled]="isLoadingMessages()"
              [ngModel]="draft()"
              (ngModelChange)="draft.set($event)"
              (keydown)="handleKeydown($event)"
            ></textarea>
            <button
              nz-button
              nzType="primary"
              type="button"
              [nzLoading]="isSending()"
              [disabled]="!canSend()"
              aria-label="Gửi câu hỏi"
              (click)="send()"
            >
              Gửi
            </button>
          </div>
        </div>
      </section>
    }
  `,
  styles: [
    `
      .assistant-launcher {
        position: fixed;
        right: max(20px, env(safe-area-inset-right));
        bottom: max(20px, env(safe-area-inset-bottom));
        z-index: 1010;
        width: 56px;
        height: 56px;
        padding: 0;
        border: 0;
        border-radius: 50%;
        background: #fff;
        box-shadow: 0 8px 24px rgb(15 23 42 / 20%);
        cursor: pointer;
        transition:
          transform 160ms ease,
          box-shadow 160ms ease;
      }

      .assistant-launcher:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 28px rgb(15 23 42 / 24%);
      }

      .assistant-launcher:focus-visible,
      button:focus-visible,
      textarea:focus-visible {
        outline: 3px solid rgb(22 119 255 / 32%);
        outline-offset: 2px;
      }

      .assistant-launcher img {
        width: 100%;
        height: 100%;
        object-fit: contain;
      }

      .assistant-window {
        position: fixed;
        right: max(20px, env(safe-area-inset-right));
        bottom: max(20px, env(safe-area-inset-bottom));
        z-index: 1010;
        display: flex;
        flex-direction: column;
        width: min(368px, calc(100vw - 32px));
        height: min(540px, calc(100dvh - 40px));
        overflow: hidden;
        border: 1px solid #dfe3ea;
        border-radius: 18px;
        background: #fff;
        box-shadow:
          0 20px 48px rgb(15 23 42 / 18%),
          0 4px 12px rgb(15 23 42 / 8%);
        animation: assistant-window-enter 180ms ease-out;
      }

      .assistant-header {
        display: flex;
        flex: 0 0 auto;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        min-height: 56px;
        padding: 8px 8px 8px 12px;
        border-bottom: 1px solid #edf0f4;
      }

      .assistant-brand {
        display: flex;
        min-width: 0;
        align-items: center;
        gap: 9px;
      }

      .assistant-avatar,
      .assistant-message-avatar {
        display: inline-flex;
        flex: 0 0 auto;
        align-items: center;
        justify-content: center;
        overflow: hidden;
        border-radius: 50%;
        background: #fff;
      }

      .assistant-avatar {
        width: 34px;
        height: 34px;
        box-shadow: 0 2px 8px rgb(15 23 42 / 12%);
      }

      .assistant-avatar img,
      .assistant-message-avatar img {
        width: 100%;
        height: 100%;
        object-fit: contain;
      }

      .assistant-brand__text {
        display: grid;
        min-width: 0;
        line-height: 1.2;
      }

      .assistant-brand__text strong {
        overflow: hidden;
        color: #111827;
        font-size: 14px;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .assistant-brand__text small {
        margin-top: 3px;
        color: #6b7280;
        font-size: 11px;
      }

      .assistant-header__actions {
        display: flex;
        flex: 0 0 auto;
      }

      .assistant-header__actions button {
        display: inline-flex;
        width: 40px;
        height: 40px;
        align-items: center;
        justify-content: center;
        padding: 0;
        border: 0;
        border-radius: 10px;
        background: transparent;
        color: #4b5563;
        cursor: pointer;
      }

      .assistant-header__actions button:hover {
        background: #f3f4f6;
        color: #111827;
      }

      .assistant-close {
        font-size: 23px;
        font-weight: 300;
        line-height: 1;
      }

      .assistant-history {
        display: grid;
        flex: 0 0 auto;
        grid-template-columns: minmax(0, 1fr) 40px;
        gap: 8px;
        padding: 8px 12px;
        border-bottom: 1px solid #edf0f4;
        background: #fafbfc;
      }

      .assistant-history nz-select,
      .assistant-history button {
        width: 100%;
        min-height: 40px;
      }

      .assistant-alert {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
        margin: 8px 12px 0;
        padding: 6px 10px;
        border: 1px solid #ffccc7;
        border-radius: 10px;
        background: #fff2f0;
        color: #a8071a;
        font-size: 12px;
      }

      .assistant-messages {
        flex: 1 1 auto;
        min-height: 0;
        overflow-y: auto;
        overscroll-behavior: contain;
        padding: 12px;
        scrollbar-gutter: stable;
      }

      .assistant-state {
        display: flex;
        height: 100%;
        align-items: center;
        justify-content: center;
        gap: 10px;
        color: #64748b;
      }

      .assistant-welcome,
      .assistant-message {
        display: flex;
        align-items: flex-start;
        gap: 8px;
        margin-bottom: 12px;
      }

      .assistant-suggestions {
        display: flex;
        flex: 0 0 auto;
        gap: 8px;
        overflow-x: auto;
        padding: 6px 12px 8px;
        scrollbar-width: none;
      }

      .assistant-suggestions::-webkit-scrollbar {
        display: none;
      }

      .assistant-suggestions button {
        flex: 0 0 auto;
        min-height: 40px;
        padding: 7px 12px;
        border: 1px solid #dce4ef;
        border-radius: 999px;
        background: #fff;
        color: #374151;
        font-size: 12px;
        white-space: nowrap;
        cursor: pointer;
      }

      .assistant-suggestions button:hover:not(:disabled) {
        border-color: #ef1748;
        color: #cf123f;
      }

      .assistant-message--user {
        justify-content: flex-end;
      }

      .assistant-message-avatar {
        width: 26px;
        height: 26px;
        margin-top: 2px;
        box-shadow: 0 1px 5px rgb(15 23 42 / 12%);
      }

      .assistant-message__body {
        display: flex;
        max-width: calc(88% - 34px);
        flex-direction: column;
        align-items: flex-start;
      }

      .assistant-message--user .assistant-message__body {
        max-width: 88%;
        align-items: flex-end;
      }

      .assistant-bubble {
        max-width: 100%;
        padding: 10px 12px;
        border-radius: 6px 14px 14px;
        background: #f1f3f5;
        color: #242b37;
        font-size: 13px;
        line-height: 1.5;
        white-space: pre-wrap;
        overflow-wrap: anywhere;
      }

      .assistant-message--user .assistant-bubble {
        border-radius: 14px 7px 14px 14px;
        background: #ef1748;
        color: #fff;
      }

      .assistant-message--pending .assistant-bubble {
        display: flex;
        align-items: center;
        gap: 8px;
        color: #64748b;
      }

      .assistant-citations {
        display: grid;
        gap: 4px;
        margin-top: 6px;
        color: #64748b;
        font-size: 12px;
      }

      .assistant-composer {
        flex: 0 0 auto;
        padding: 0 12px max(12px, env(safe-area-inset-bottom));
      }

      .assistant-input-shell {
        display: flex;
        align-items: flex-end;
        gap: 8px;
        min-height: 44px;
        padding: 5px 5px 5px 13px;
        border: 1px solid #d7dce5;
        border-radius: 18px;
        background: #fff;
        transition:
          border-color 160ms ease,
          box-shadow 160ms ease;
      }

      .assistant-input-shell:focus-within {
        border-color: #ef1748;
        box-shadow: 0 0 0 3px rgb(239 23 72 / 12%);
      }

      .assistant-input-shell textarea {
        min-width: 0;
        min-height: 32px;
        max-height: 84px;
        flex: 1;
        padding: 6px 0;
        overflow-y: auto;
        border: 0;
        outline: 0;
        background: transparent;
        color: #111827;
        font: inherit;
        font-size: 16px;
        line-height: 20px;
        resize: none;
      }

      .assistant-input-shell textarea::placeholder {
        color: #9ca3af;
      }

      .assistant-input-shell button {
        min-width: 58px;
        min-height: 34px;
        border-radius: 13px;
        background: #ef1748;
        font-size: 12px;
      }

      .assistant-send-error {
        margin-bottom: 6px;
        color: #cf1322;
        font-size: 12px;
      }

      .sr-only {
        position: absolute;
        width: 1px;
        height: 1px;
        padding: 0;
        margin: -1px;
        overflow: hidden;
        clip: rect(0, 0, 0, 0);
        white-space: nowrap;
        border: 0;
      }

      @keyframes assistant-window-enter {
        from {
          opacity: 0;
          transform: translateY(8px) scale(0.98);
        }
        to {
          opacity: 1;
          transform: translateY(0) scale(1);
        }
      }

      @media (max-width: 480px) {
        .assistant-launcher {
          right: max(16px, env(safe-area-inset-right));
          bottom: max(16px, env(safe-area-inset-bottom));
        }

        .assistant-window {
          right: max(8px, env(safe-area-inset-right));
          bottom: max(8px, env(safe-area-inset-bottom));
          width: calc(100vw - 16px);
          height: min(540px, calc(100dvh - 16px));
          border-radius: 16px;
        }

        .assistant-brand__text small {
          display: none;
        }
      }

      @media (max-height: 480px) and (orientation: landscape) {
        .assistant-window {
          top: 8px;
          bottom: 8px;
          height: auto;
        }
      }

      @media (prefers-reduced-motion: reduce) {
        .assistant-launcher,
        .assistant-window,
        .assistant-input-shell {
          animation: none;
          transition: none;
        }
      }
    `,
  ],
})
export class AssistantChatComponent {
  private readonly assistantService = inject(AssistantService);
  private readonly cdr = inject(ChangeDetectorRef);

  readonly role = input<AssistantRole>('INTERN');
  readonly visible = signal(false);
  readonly historyOpen = signal(false);
  readonly conversations = signal<AssistantConversationSummary[]>([]);
  readonly activeConversationId = signal<string | null>(null);
  readonly messages = signal<AssistantMessage[]>([]);
  readonly draft = signal('');
  readonly isLoadingConversations = signal(false);
  readonly isLoadingMessages = signal(false);
  readonly isSending = signal(false);
  readonly loadError = signal('');
  readonly sendError = signal('');
  readonly canSend = computed(
    () => Boolean(this.draft().trim()) && !this.isSending() && !this.isLoadingMessages(),
  );
  readonly suggestions = computed(() => {
    if (this.role() === 'INTERN') {
      return ['Deadline gần nhất của tôi là gì?', 'Tiến độ học tập của tôi thế nào?'];
    }
    return ['Intern nào đang có task quá hạn?', 'Tiến độ của Nguyễn Văn An thế nào?'];
  });

  @ViewChild('composer') private composer?: ElementRef<HTMLTextAreaElement>;
  @ViewChild('launcher') private launcher?: ElementRef<HTMLButtonElement>;
  @ViewChild('messageLog') private messageLog?: ElementRef<HTMLDivElement>;
  private conversationLoadToken = 0;

  open(): void {
    this.visible.set(true);
    this.historyOpen.set(false);
    this.loadConversations();
    this.focusComposer();
  }

  close(): void {
    this.visible.set(false);
    this.historyOpen.set(false);
    setTimeout(() => this.launcher?.nativeElement.focus());
  }

  @HostListener('document:keydown.escape')
  closeOnEscape(): void {
    if (this.visible()) this.close();
  }

  startNewConversation(): void {
    if (this.isSending()) return;
    this.conversationLoadToken += 1;
    this.activeConversationId.set(null);
    this.messages.set([]);
    this.isLoadingMessages.set(false);
    this.draft.set('');
    this.loadError.set('');
    this.sendError.set('');
    this.historyOpen.set(false);
    this.focusComposer();
  }

  loadConversation(conversationId: string | null): void {
    if (this.isSending()) return;
    const loadToken = ++this.conversationLoadToken;
    this.activeConversationId.set(conversationId);
    this.historyOpen.set(false);
    this.messages.set([]);
    this.loadError.set('');
    if (!conversationId) {
      this.isLoadingMessages.set(false);
      return;
    }
    this.isLoadingMessages.set(true);
    this.assistantService.getConversation(conversationId).subscribe({
      next: (conversation) => {
        if (
          loadToken !== this.conversationLoadToken ||
          this.activeConversationId() !== conversationId
        ) {
          return;
        }
        this.messages.set(conversation.messages);
        this.isLoadingMessages.set(false);
        this.scrollToBottom();
        this.cdr.markForCheck();
      },
      error: () => {
        if (
          loadToken !== this.conversationLoadToken ||
          this.activeConversationId() !== conversationId
        ) {
          return;
        }
        this.loadError.set('Không thể tải hội thoại này.');
        this.isLoadingMessages.set(false);
        this.cdr.markForCheck();
      },
    });
  }

  reloadCurrent(): void {
    const conversationId = this.activeConversationId();
    if (conversationId) this.loadConversation(conversationId);
    else this.loadConversations();
  }

  useSuggestion(suggestion: string): void {
    this.draft.set(suggestion);
    this.focusComposer();
  }

  handleKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      this.send();
    }
  }

  protected formatAssistantMessage(content: string): string {
    return content
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;')
      .replace(/\*\*([^*\r\n]+)\*\*/g, '<strong>$1</strong>')
      .replace(/\r?\n/g, '<br />');
  }

  send(): void {
    const content = this.draft().trim();
    if (!content || this.isSending()) return;
    const optimisticId = `pending-${Date.now()}`;
    this.messages.update((items) => [
      ...items,
      {
        id: optimisticId,
        role: 'USER',
        content,
        citations: null,
        created_at: new Date().toISOString(),
      },
    ]);
    this.draft.set('');
    this.sendError.set('');
    this.isSending.set(true);
    this.scrollToBottom();

    this.assistantService.chat(content, this.activeConversationId()).subscribe({
      next: (response) => {
        this.activeConversationId.set(response.conversation_id);
        this.messages.update((items) => [...items, response.message]);
        this.isSending.set(false);
        this.loadConversations(false);
        this.scrollToBottom();
        this.cdr.markForCheck();
      },
      error: (error: { error?: { error?: { message?: string } } }) => {
        this.messages.update((items) => items.filter((item) => item.id !== optimisticId));
        this.draft.set(content);
        this.sendError.set(
          error.error?.error?.message || 'Không thể gửi câu hỏi. Vui lòng thử lại.',
        );
        this.isSending.set(false);
        this.cdr.markForCheck();
      },
    });
  }

  private loadConversations(showLoading = true): void {
    if (showLoading) this.isLoadingConversations.set(true);
    this.assistantService.getConversations().subscribe({
      next: (conversations) => {
        this.conversations.set(conversations);
        this.isLoadingConversations.set(false);
        this.cdr.markForCheck();
      },
      error: () => {
        this.loadError.set('Không thể tải lịch sử hội thoại.');
        this.isLoadingConversations.set(false);
        this.cdr.markForCheck();
      },
    });
  }

  private focusComposer(): void {
    setTimeout(() => this.composer?.nativeElement.focus());
  }

  private scrollToBottom(): void {
    setTimeout(() => {
      const element = this.messageLog?.nativeElement;
      if (element) element.scrollTop = element.scrollHeight;
    });
  }
}
