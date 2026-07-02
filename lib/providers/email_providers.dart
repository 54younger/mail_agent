import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/models/email_message.dart';
import '../data/objectbox/objectbox_store.dart';
import 'sync_providers.dart';

/// Returns all emails sorted by date descending.
/// Re-fetches whenever sync state changes so the list stays fresh.
final emailListProvider = FutureProvider<List<EmailMessage>>((ref) async {
  ref.watch(syncNotifierProvider); // invalidated on each sync batch
  final store = ref.watch(objectBoxStoreProvider);
  final all = store.emails.getAll();
  all.sort((a, b) => b.date.compareTo(a.date));
  return all;
});
