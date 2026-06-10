import { getServerUrl, getToken } from './config';

export type ProcessingStatus = 'pending' | 'processing' | 'ready' | 'failed';

export interface EmailCard {
  id: string;
  gmail_message_id: string;
  subject: string | null;
  from_email: string | null;
  snippet: string | null;
  received_at: string | null;
  processing_status: ProcessingStatus;
  background_image_url: string | null;
  text: string | null;
  audio_url: string | null;
}

export interface CardListResponse {
  items: EmailCard[];
  limit: number;
  offset: number;
  next_offset: number | null;
}

export interface Me {
  user_id: string;
  email: string;
  display_name: string | null;
  picture_url: string | null;
  gmail_connected: boolean;
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const base = await getServerUrl();
  const token = await getToken();
  const headers: Record<string, string> = {
    ...(init?.headers as Record<string, string> | undefined),
  };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  const response = await fetch(`${base}${path}`, { ...init, headers });
  if (!response.ok) {
    throw new ApiError(response.status, `HTTP ${response.status} for ${path}`);
  }
  return (await response.json()) as T;
}

export function getMe(): Promise<Me> {
  return request<Me>('/v1/auth/me');
}

export function getCards(limit = 50): Promise<CardListResponse> {
  return request<CardListResponse>(`/v1/cards/?limit=${limit}`);
}

export function retryCard(cardId: string): Promise<{ status: string }> {
  return request<{ status: string }>(`/v1/cards/${cardId}/retry`, { method: 'POST' });
}

export async function getSignInUrl(): Promise<string> {
  const { auth_url } = await request<{ auth_url: string }>(
    '/v1/auth/google/start?client=mobile'
  );
  return auth_url;
}

export function headlineOf(card: EmailCard): string {
  const [headline] = (card.text ?? '').split('\n\n');
  return headline || card.subject || '(no subject)';
}

export function summaryOf(card: EmailCard): string {
  const [, ...rest] = (card.text ?? '').split('\n\n');
  return rest.join(' ') || card.snippet || '';
}

export function senderOf(card: EmailCard): string {
  const from = card.from_email ?? '';
  const match = from.match(/^\s*"?([^"<]+?)"?\s*</);
  return (match ? match[1] : from).trim() || 'Unknown sender';
}
