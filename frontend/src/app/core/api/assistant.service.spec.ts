import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { AssistantService } from './assistant.service';

describe('AssistantService', () => {
  let service: AssistantService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(AssistantService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('gửi câu hỏi với conversation hiện tại', () => {
    service.chat('Deadline gần nhất?', 'conversation-1').subscribe();

    const request = httpMock.expectOne('/api/v1/assistant/chat');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({
      message: 'Deadline gần nhất?',
      conversation_id: 'conversation-1',
    });
    request.flush({});
  });

  it('tải danh sách và chi tiết hội thoại', () => {
    service.getConversations().subscribe();
    httpMock.expectOne('/api/v1/assistant/conversations').flush([]);

    service.getConversation('conversation-1').subscribe();
    httpMock.expectOne('/api/v1/assistant/conversations/conversation-1').flush({});
  });
});
