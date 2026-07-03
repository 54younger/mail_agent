import 'package:objectbox/objectbox.dart';

@Entity()
class Account {
  @Id()
  int id = 0;

  String host = '';
  int port = 993;
  bool useSsl = true;
  String username = '';

  /// Key used to look up the actual password from SecureStorage.
  String credentialKey = '';

  /// Display name shown in the sidebar.
  String displayName = '';

  /// IMAP UIDVALIDITY — detects server-side folder resets.
  int uidValidity = 0;

  /// ISO-8601 timestamp of the last successful full sync.
  String? lastSyncAt;
}
