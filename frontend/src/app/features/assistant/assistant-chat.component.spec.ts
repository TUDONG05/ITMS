import { TestBed } from '@angular/core/testing';
import { FileTextOutline, PlusOutline } from '@ant-design/icons-angular/icons';
import { provideNzIcons } from 'ng-zorro-antd/icon';
import { Subject, of } from 'rxjs';

import {
  AssistantChatResponse,
  AssistantConversationDetail,
  AssistantService,
} from '../../core/api/assistant.service';
import { AssistantChatComponent } from './assistant-chat.component';

describe('AssistantChatComponent', () => {
  const conversation = (id: string, content: string): AssistantConversationDetail => ({
    id,
    title: id,
    created_at: '2026-10-13T00:00:00Z',
    updated_at: '2026-10-13T00:00:00Z',
    messages: [
      {
        id: `${id}-message`,
        role: 'ASSISTANT',
        content,
        citations: null,
        created_at: '2026-10-13T00:00:00Z',
      },
    ],
  });

  it('không để response cũ ghi đè hội thoại vừa chọn', () => {
    const first = new Subject<AssistantConversationDetail>();
    const second = new Subject<AssistantConversationDetail>();
    const service = {
      getConversations: () => of([]),
      getConversation: (id: string) => (id === 'first' ? first : second),
      chat: () => new Subject<AssistantChatResponse>(),
    };
    TestBed.configureTestingModule({
      imports: [AssistantChatComponent],
      providers: [
        { provide: AssistantService, useValue: service },
        provideNzIcons([FileTextOutline, PlusOutline]),
      ],
    });
    const component = TestBed.createComponent(AssistantChatComponent).componentInstance;

    component.loadConversation('first');
    component.loadConversation('second');
    second.next(conversation('second', 'Nội dung mới'));
    first.next(conversation('first', 'Nội dung cũ'));

    expect(component.activeConversationId()).toBe('second');
    expect(component.messages()[0].content).toBe('Nội dung mới');
  });

  it('khóa chuyển hội thoại khi đang gửi câu hỏi', () => {
    const pending = new Subject<AssistantChatResponse>();
    const service = {
      getConversations: () => of([]),
      getConversation: () => of(conversation('current', 'Nội dung')),
      chat: () => pending,
    };
    TestBed.configureTestingModule({
      imports: [AssistantChatComponent],
      providers: [
        { provide: AssistantService, useValue: service },
        provideNzIcons([FileTextOutline, PlusOutline]),
      ],
    });
    const component = TestBed.createComponent(AssistantChatComponent).componentInstance;
    component.activeConversationId.set('current');
    component.draft.set('Deadline gần nhất?');

    component.send();
    component.startNewConversation();
    component.loadConversation('another');

    expect(component.isSending()).toBe(true);
    expect(component.activeConversationId()).toBe('current');
  });

  it('hiển thị cửa sổ chat nổi thay vì drawer toàn chiều cao', () => {
    const service = {
      getConversations: () => of([]),
      getConversation: () => of(conversation('current', 'Nội dung')),
      chat: () => new Subject<AssistantChatResponse>(),
    };
    TestBed.configureTestingModule({
      imports: [AssistantChatComponent],
      providers: [
        { provide: AssistantService, useValue: service },
        provideNzIcons([FileTextOutline, PlusOutline]),
      ],
    });
    const fixture = TestBed.createComponent(AssistantChatComponent);
    const component = fixture.componentInstance;
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.assistant-launcher')).toBeTruthy();
    expect(fixture.nativeElement.querySelector('.assistant-window')).toBeNull();

    component.open();
    fixture.detectChanges();

    const dialog = fixture.nativeElement.querySelector('.assistant-window');
    expect(dialog).toBeTruthy();
    expect(dialog.getAttribute('aria-modal')).toBe('false');
    expect(fixture.nativeElement.querySelector('nz-drawer')).toBeNull();
    expect(fixture.nativeElement.querySelector('.assistant-launcher')).toBeNull();
  });

  it('render chữ in đậm của trợ lý mà không render HTML từ nội dung AI', () => {
    const service = {
      getConversations: () => of([]),
      getConversation: () => of(conversation('current', 'Nội dung')),
      chat: () => new Subject<AssistantChatResponse>(),
    };
    TestBed.configureTestingModule({
      imports: [AssistantChatComponent],
      providers: [
        { provide: AssistantService, useValue: service },
        provideNzIcons([FileTextOutline, PlusOutline]),
      ],
    });
    const fixture = TestBed.createComponent(AssistantChatComponent);
    fixture.componentInstance.visible.set(true);
    fixture.componentInstance.messages.set(
      conversation(
        'current',
        'Mentor của bạn là **AI Mentor**.\n<img data-attack src=x onerror=alert(1)>',
      ).messages,
    );

    fixture.detectChanges();

    const bubble: HTMLElement = fixture.nativeElement.querySelector('.assistant-bubble');
    expect(bubble.querySelector('strong')?.textContent).toBe('AI Mentor');
    expect(bubble.textContent).not.toContain('**');
    expect(bubble.querySelector('[data-attack]')).toBeNull();
  });
});
