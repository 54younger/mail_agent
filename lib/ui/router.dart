import 'package:flutter/material.dart';

import 'screens/classify/classify_screen.dart';
import 'screens/inbox/inbox_screen.dart';
import 'screens/jobs/jobs_screen.dart';
import 'screens/search/search_screen.dart';
import 'screens/settings/settings_screen.dart';
import 'screens/setup/account_setup_screen.dart';

class AppRoutes {
  AppRoutes._();
  static const setup = '/setup';
  static const inbox = '/inbox';
  static const search = '/search';
  static const classify = '/classify';
  static const jobs = '/jobs';
  static const settings = '/settings';
}

/// Simple router. Phase 2 will upgrade to go_router for deep-linking.
final appRouter = RouterConfig<Object>(
  routerDelegate: _AppRouterDelegate(),
  routeInformationParser: _AppRouteParser(),
);

class _AppRouteParser extends RouteInformationParser<Object> {
  @override
  Future<Object> parseRouteInformation(RouteInformation info) async =>
      info.uri.path;

  @override
  RouteInformation restoreRouteInformation(Object config) =>
      RouteInformation(uri: Uri.parse(config as String));
}

class _AppRouterDelegate extends RouterDelegate<Object>
    with ChangeNotifier, PopNavigatorRouterDelegateMixin<Object> {
  @override
  final GlobalKey<NavigatorState> navigatorKey = GlobalKey<NavigatorState>();

  String _route = AppRoutes.setup;

  @override
  Object? get currentConfiguration => _route;

  void navigateTo(String route) {
    _route = route;
    notifyListeners();
  }

  @override
  Widget build(BuildContext context) {
    return Navigator(
      key: navigatorKey,
      pages: [_page(_route)],
      onDidRemovePage: (_) {},
    );
  }

  MaterialPage<void> _page(String route) => MaterialPage<void>(
        key: ValueKey(route),
        child: switch (route) {
          AppRoutes.inbox => const InboxScreen(),
          AppRoutes.search => const SearchScreen(),
          AppRoutes.classify => const ClassifyScreen(),
          AppRoutes.jobs => const JobsScreen(),
          AppRoutes.settings => const SettingsScreen(),
          _ => const AccountSetupScreen(),
        },
      );

  @override
  Future<void> setNewRoutePath(Object config) async => _route = config as String;
}
