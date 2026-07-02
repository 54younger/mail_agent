/// IMAP error classification and user-facing messages.
enum ImapErrorKind {
  authFailed,
  imapDisabled,
  accountLocked,
  networkError,
  tlsError,
  serverError,
  unknown,
}

/// Maps a raw IMAP/socket exception to an [ImapErrorKind] by pattern matching
/// on the lowercased exception string.
ImapErrorKind classifyImapError(Object e) {
  final s = e.toString().toLowerCase();

  // Security block before or after auth — 163/QQ "Unsafe Login", suspended accounts
  if (s.contains('unsafe login') ||
      s.contains('account locked') ||
      s.contains('login disabled') ||
      s.contains('account suspended')) {
    return ImapErrorKind.accountLocked;
  }

  // Wrong password / wrong auth code
  if (s.contains('login failed') ||
      s.contains('authentication failed') ||
      s.contains('invalid credentials') ||
      s.contains('invalid login') ||
      s.contains('[authenticationfailed]') ||
      s.contains('incorrect password')) {
    return ImapErrorKind.authFailed;
  }

  // IMAP not enabled on the provider side
  if (s.contains('[noperm]') ||
      (s.contains('imap') && s.contains('disabled')) ||
      (s.contains('imap') && s.contains('not enabled')) ||
      (s.contains('imap') && s.contains('not opened'))) {
    return ImapErrorKind.imapDisabled;
  }

  // SSL / TLS handshake failure
  if (s.contains('ssl') ||
      s.contains('tls') ||
      s.contains('certificate') ||
      s.contains('handshake')) {
    return ImapErrorKind.tlsError;
  }

  // Network / socket errors
  if (s.contains('connection refused') ||
      s.contains('connection timed out') ||
      s.contains('connection reset') ||
      s.contains('timeout') ||
      s.contains('socketexception') ||
      s.contains('no such host') ||
      s.contains('host unreachable') ||
      s.contains('network is unreachable') ||
      s.contains('dns')) {
    return ImapErrorKind.networkError;
  }

  // Server overloaded, rate-limited, temporary failure
  if (s.contains('unavailable') ||
      s.contains('too many') ||
      s.contains('rate limit') ||
      s.contains('try again later') ||
      s.contains('service not available')) {
    return ImapErrorKind.serverError;
  }

  return ImapErrorKind.unknown;
}

extension ImapErrorKindX on ImapErrorKind {
  /// Short title shown in the error banner.
  String get userMessage => switch (this) {
        ImapErrorKind.authFailed => '密码或授权码错误',
        ImapErrorKind.imapDisabled => 'IMAP 服务未启用',
        ImapErrorKind.accountLocked => '账户登录被安全拦截',
        ImapErrorKind.networkError => '网络连接失败',
        ImapErrorKind.tlsError => 'SSL 加密连接失败',
        ImapErrorKind.serverError => '邮件服务器暂时不可用',
        ImapErrorKind.unknown => '同步失败',
      };

  /// Actionable guidance shown below the title.
  String get hint => switch (this) {
        ImapErrorKind.authFailed =>
          '163、QQ、Gmail 等邮箱需使用「授权码」而非登录密码。\n'
              '请在网页版邮箱 → 设置 → 账户安全 → 开启 IMAP → 生成授权码，然后重新绑定。',
        ImapErrorKind.imapDisabled =>
          '请在网页版邮箱开启 IMAP 服务：\n'
              '设置 → POP3/SMTP/IMAP → 开启 IMAP 服务，再重新绑定账号。',
        ImapErrorKind.accountLocked =>
          '163/QQ 邮箱检测到新设备登录，已触发安全保护。\n'
              '请登录网页版邮箱完成安全验证，或改用「授权码」代替密码后重新绑定。',
        ImapErrorKind.networkError =>
          '请检查网络连接，并确认防火墙未屏蔽 IMAP 端口（993）。',
        ImapErrorKind.tlsError =>
          '请确认未使用拦截 HTTPS 流量的代理或企业防火墙，或切换至其他网络后重试。',
        ImapErrorKind.serverError =>
          '邮件服务器临时故障，请等待几分钟后点击「重试」。',
        ImapErrorKind.unknown =>
          '请检查邮箱地址、密码和服务器配置是否正确，或重新绑定账号。',
      };

  /// True when simply retrying the sync makes sense (transient failures).
  bool get canRetry =>
      this == ImapErrorKind.networkError || this == ImapErrorKind.serverError;

  /// True when the user should go back to the setup screen.
  bool get shouldResetup => !canRetry;
}
