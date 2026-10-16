import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

export interface AssistantCitation {
  type: 'database';
  tool: string;
  label: string;
  intern_ids?: string[];
  scope_role?: 'ADMIN' | 'MENTOR' | 'INTERN';
}

export interface AssistantMessage {
  id: string;
  role: 'USER' | 'ASSISTANT';
  content: string;
  citations: AssistantCitation[] | null;
  created_at: string;
}

export interface AssistantConversationSummary {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export interface AssistantConversationDetail extends AssistantConversationSummary {
  messages: AssistantMessage[];
}

export interface AssistantChatResponse {
  conversation_id: string;
  message: AssistantMessage;
}

@Injectable({ providedIn: 'root' })
export class AssistantService {
  private readonly http = inject(HttpClient);

  chat(message: string, conversationId?: string | null): Observable<AssistantChatResponse> {
    return this.http.post<AssistantChatResponse>('/api/v1/assistant/chat', {
      message,
      conversation_id: conversationId || null,
    });
  }

  getConversations(): Observable<AssistantConversationSummary[]> {
    return this.http.get<AssistantConversationSummary[]>('/api/v1/assistant/conversations');
  }

  getConversation(conversationId: string): Observable<AssistantConversationDetail> {
    return this.http.get<AssistantConversationDetail>(
      `/api/v1/assistant/conversations/${conversationId}`,
    );
  }
}
