// API integration service for Landslide Monitoring Agent backend

export interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface SessionInfo {
  session_id: string;
  name: string;
  token: {
    access_token: string;
    token_type: string;
    expires_at: string;
  };
  isGeneratingTitle?: boolean;
}

export interface UserResponse {
  id: number;
  email: string;
  username: string | null;
  token: {
    access_token: string;
    token_type: string;
    expires_at: string;
  };
}

// LocalStorage helpers
export const getStoredUserToken = () => localStorage.getItem('lma_user_token');
export const setStoredUserToken = (token: string) => localStorage.setItem('lma_user_token', token);
export const removeStoredUserToken = () => localStorage.removeItem('lma_user_token');

export const getStoredUsername = () => localStorage.getItem('lma_username') || '';
export const setStoredUsername = (username: string) => localStorage.setItem('lma_username', username);
export const removeStoredUsername = () => localStorage.removeItem('lma_username');

// Authentication API
export async function register(email: string, password: string, username?: string): Promise<UserResponse> {
  const response = await fetch('/api/v1/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, username }),
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Registration failed' }));
    throw new Error(errorData.detail || 'Registration failed');
  }
  return response.json();
}

export async function login(email: string, password: string): Promise<{ access_token: string }> {
  const formData = new URLSearchParams();
  formData.append('email', email);
  formData.append('password', password);
  formData.append('grant_type', 'password');

  const response = await fetch('/api/v1/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: formData.toString(),
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Login failed' }));
    throw new Error(errorData.detail || 'Login failed');
  }
  return response.json();
}

// Session Management API (uses User Token)
export async function getSessions(userToken: string): Promise<SessionInfo[]> {
  const response = await fetch('/api/v1/auth/sessions', {
    headers: { 'Authorization': `Bearer ${userToken}` },
  });
  if (!response.ok) {
    if (response.status === 401) {
      removeStoredUserToken();
      window.location.reload();
    }
    throw new Error('Failed to fetch sessions');
  }
  return response.json();
}

export async function createSession(userToken: string): Promise<SessionInfo> {
  const response = await fetch('/api/v1/auth/session', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${userToken}` },
  });
  if (!response.ok) {
    throw new Error('Failed to create session');
  }
  return response.json();
}

// Individual Session API (uses Session Specific Token)
export async function renameSession(sessionToken: string, sessionId: string, newName: string): Promise<SessionInfo> {
  const formData = new URLSearchParams();
  formData.append('name', newName);

  const response = await fetch(`/api/v1/auth/session/${sessionId}/name`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
      'Authorization': `Bearer ${sessionToken}`,
    },
    body: formData.toString(),
  });
  if (!response.ok) {
    throw new Error('Failed to rename session');
  }
  return response.json();
}

export async function deleteSession(sessionToken: string, sessionId: string): Promise<void> {
  const response = await fetch(`/api/v1/auth/session/${sessionId}`, {
    method: 'DELETE',
    headers: { 'Authorization': `Bearer ${sessionToken}` },
  });
  if (!response.ok) {
    throw new Error('Failed to delete session');
  }
}

// Chatbot messages API (uses Session Specific Token)
export async function getSessionMessages(sessionToken: string): Promise<Message[]> {
  const response = await fetch('/api/v1/chatbot/messages', {
    headers: { 'Authorization': `Bearer ${sessionToken}` },
  });
  if (!response.ok) {
    throw new Error('Failed to load chat history');
  }
  const data = await response.json();
  return data.messages || [];
}

export async function clearChatHistory(sessionToken: string): Promise<void> {
  const response = await fetch('/api/v1/chatbot/messages', {
    method: 'DELETE',
    headers: { 'Authorization': `Bearer ${sessionToken}` },
  });
  if (!response.ok) {
    throw new Error('Failed to clear chat history');
  }
}

// SSE Stream Chat API (uses Session Specific Token)
export async function streamChat(
  messages: Message[],
  sessionToken: string,
  onChunk: (text: string) => void,
  onDone: () => void,
  onError: (err: any) => void
) {
  try {
    const response = await fetch('/api/v1/chatbot/chat/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${sessionToken}`,
      },
      body: JSON.stringify({ messages }),
    });

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(errText || `Stream request failed with status ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('ReadableStream not supported by browser.');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed.startsWith('data: ')) {
          const jsonStr = trimmed.slice(6).trim();
          if (!jsonStr) continue;
          try {
            const parsed = JSON.parse(jsonStr);
            if (parsed.done) {
              onDone();
              return;
            } else if (parsed.content) {
              onChunk(parsed.content);
            }
          } catch (e) {
            console.error('Error parsing SSE line:', trimmed, e);
          }
        }
      }
    }
  } catch (error) {
    onError(error);
  }
}
