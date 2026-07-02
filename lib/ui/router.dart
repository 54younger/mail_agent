import 'package:flutter/material.dart';

import 'screens/setup/account_setup_screen.dart';
import 'shell/app_shell.dart';

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
  routerDelegate: AppRouterDelegate(),
  routeInformationParser: _AppRouteParser(),
  routeInformationProvider: PlatformRouteInformationProvider(
    initialRouteInformation: RouteInformation(
      uri: Uri.parse(AppRoutes.setup),
    ),
  ),
);

/// Convenience accessor used by screens to trigger navigation.
AppRouterDelegate get appRouterDelegate =>
    appRouter.routerDelegate as AppRouterDelegate;

class _AppRouteParser extends RouteInformationParser<Object> {
  @override
  Future<Object> parseRouteInformation(RouteInformation info) async =>
      info.uri.path;

  @override
  RouteInformation restoreRouteInformation(Object config) =>
      RouteInformation(uri: Uri.parse(config as String));
}

class AppRouterDelegate extends RouterDelegate<Object>
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
        key: ValueKey(route == AppRoutes.setup ? AppRoutes.setup : 'shell'),
        child: route == AppRoutes.setup
            ? const AccountSetupScreen()
            : AppShell(initialIndex: _tabIndex(route)),
      );

  /// Maps a legacy route constant to the shell's tab index.
  static int _tabIndex(String route) => switch (route) {
        AppRoutes.search => 1,
        AppRoutes.classify => 2,
        AppRoutes.jobs => 3,
        AppRoutes.settings => 4,
        _ => 0, // inbox
      };

  @override
  Future<void> setNewRoutePath(Object config) async =>
      _route = config as String;
}
