import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app.dart';
import 'data/objectbox/objectbox_store.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final store = await ObjectBoxStore.create();
  runApp(
    ProviderScope(
      overrides: [objectBoxStoreProvider.overrideWithValue(store)],
      child: const MailAgentApp(),
    ),
  );
}
