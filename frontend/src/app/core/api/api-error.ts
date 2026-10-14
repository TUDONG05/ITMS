/** Lấy thông báo lỗi từ phản hồi API chuẩn của dự án ({ error: { message } }). */
export function apiMessage(err: unknown, fallback: string): string {
  const body = (err as { error?: { error?: { message?: unknown }; detail?: unknown } })?.error;
  if (typeof body?.error?.message === 'string') return body.error.message;
  if (typeof body?.detail === 'string') return body.detail;
  return fallback;
}

/** Mã lỗi nghiệp vụ của API, ví dụ CRITERION_IN_USE. */
export function apiErrorCode(err: unknown): string | null {
  const code = (err as { error?: { error?: { code?: unknown } } })?.error?.error?.code;
  return typeof code === 'string' ? code : null;
}
