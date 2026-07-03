import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/models/account.dart';
import '../../data/objectbox/objectbox_store.dart';
import '../../providers/sync_providers.dart';
import '../router.dart';
import '../screens/classify/classify_screen.dart';
import '../screens/inbox/inbox_screen.dart';
import '../screens/jobs/jobs_screen.dart';
import '../screens/search/search_screen.dart';
import '../screens/settings/settings_screen.dart';
import '../widgets/index_progress_bar.dart';

/// A single destination hosted by the [AppShell].
class _Destination {
  const _Destination(this.icon, this.selectedIcon, this.label, this.screen);
  final IconData icon;
  final IconData selectedIcon;
  final String label;
  final Widget screen;
}

const _destinations = <_Destination>[
  _Destination(Icons.inbox_outlined, Icons.inbox, '收件箱', InboxScreen()),
  _Destination(Icons.search_outlined, Icons.search, '语义搜索', SearchScreen()),
  _Destination(
      Icons.auto_awesome_outlined, Icons.auto_awesome, '智能分类', ClassifyScreen()),
  _Destination(Icons.work_outline, Icons.work, '求职追踪', JobsScreen()),
  _Destination(Icons.settings_outlined, Icons.settings, '设置', SettingsScreen()),
];

/// Main post-binding surface: a persistent navigation shell wrapping every
/// feature screen. Replaces the previous single-inbox view and hosts the
/// sync progress bar + account menu so they are reachable from any tab.
class AppShell extends ConsumerStatefulWidget {
  const AppShell({super.key, this.initialIndex = 0});
  final int initialIndex;

  @override
  ConsumerState<AppShell> createState() => _AppShellState();
}

class _AppShellState extends ConsumerState<AppShell> {
  late int _index = widget.initialIndex;

  @override
  void initState() {
    super.initState();
    // Kick off an incremental launch sync so the progress bar appears on
    // reopen — but only if a sync isn't already in flight (e.g. right after
    // first bind, where a full initial sync is already streaming).
    WidgetsBinding.instance.addPostFrameCallback((_) => _maybeLaunchSync());
  }

  void _maybeLaunchSync() {
    if (!mounted) return;
    if (ref.read(syncNotifierProvider) is! SyncIdle) return;
    final account = _account();
    if (account == null) return;
    // Fire-and-forget; progress streams into syncNotifierProvider.
    ref.read(syncNotifierProvider.notifier).syncAccount(account);
  }

  Account? _account() {
    final all = ref.read(objectBoxStoreProvider).accounts.getAll();
    return all.isEmpty ? null : all.first;
  }

  Future<void> _resync() async {
    final account = _account();
    if (account == null) return;
    await ref.read(syncNotifierProvider.notifier).syncAccount(account);
  }

  Future<void> _rebind() async {
    await ref.read(syncNotifierProvider.notifier).resetForResetup();
    if (mounted) appRouterDelegate.navigateTo(AppRoutes.setup);
  }

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.sizeOf(context).width;
    final useRail = width >= 640;

    final content = Column(
      children: [
        const IndexProgressBar(),
        Expanded(
          child: IndexedStack(
            index: _index,
            children: [for (final d in _destinations) d.screen],
          ),
        ),
      ],
    );

    if (useRail) {
      return Scaffold(
        body: Row(
          children: [
            _Rail(
              index: _index,
              extended: width >= 1000,
              account: _account(),
              onSelected: (i) => setState(() => _index = i),
              onResync: _resync,
              onRebind: _rebind,
            ),
            const VerticalDivider(width: 1),
            Expanded(child: content),
          ],
        ),
      );
    }

    // Narrow / iOS: bottom navigation.
    return Scaffold(
      appBar: AppBar(
        title: Text(_destinations[_index].label),
        actions: [
          _AccountMenu(
            account: _account(),
            onResync: _resync,
            onRebind: _rebind,
          ),
        ],
      ),
      body: content,
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() => _index = i),
        destinations: [
          for (final d in _destinations)
            NavigationDestination(
              icon: Icon(d.icon),
              selectedIcon: Icon(d.selectedIcon),
              label: d.label,
            ),
        ],
      ),
    );
  }
}

// ── NavigationRail (wide / desktop) ────────────────────────────────────────────

class _Rail extends StatelessWidget {
  const _Rail({
    required this.index,
    required this.extended,
    required this.account,
    required this.onSelected,
    required this.onResync,
    required this.onRebind,
  });

  final int index;
  final bool extended;
  final Account? account;
  final ValueChanged<int> onSelected;
  final Future<void> Function() onResync;
  final Future<void> Function() onRebind;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final tt = Theme.of(context).textTheme;

    return NavigationRail(
      selectedIndex: index,
      extended: extended,
      // Extended rails must not set a label type; compact rails show labels
      // under each icon for clearer affordance on medium widths.
      labelType:
          extended ? NavigationRailLabelType.none : NavigationRailLabelType.all,
      onDestinationSelected: onSelected,
      backgroundColor: cs.surfaceContainerLow,
      leading: Padding(
        padding: EdgeInsets.symmetric(
          horizontal: extended ? 16 : 0,
          vertical: 8,
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.mail_rounded, color: cs.primary),
            if (extended) ...[
              const SizedBox(width: 8),
              Text('Mail Agent', style: tt.titleMedium),
            ],
          ],
        ),
      ),
      trailing: Expanded(
        child: Align(
          alignment: Alignment.bottomCenter,
          child: Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: _AccountMenu(
              account: account,
              extended: extended,
              onResync: onResync,
              onRebind: onRebind,
            ),
          ),
        ),
      ),
      destinations: [
        for (final d in _destinations)
          NavigationRailDestination(
            icon: Icon(d.icon),
            selectedIcon: Icon(d.selectedIcon),
            label: Text(d.label),
          ),
      ],
    );
  }
}

// ── Account menu (shared by rail + bottom-bar app bar) ──────────────────────────

enum _AccountAction { resync, rebind }

class _AccountMenu extends StatelessWidget {
  const _AccountMenu({
    required this.account,
    required this.onResync,
    required this.onRebind,
    this.extended = false,
  });

  final Account? account;
  final Future<void> Function() onResync;
  final Future<void> Function() onRebind;
  final bool extended;

  @override
  Widget build(BuildContext context) {
    final email = account?.username ?? '';

    return PopupMenuButton<_AccountAction>(
      tooltip: email.isEmpty ? '账户' : email,
      onSelected: (a) => switch (a) {
        _AccountAction.resync => onResync(),
        _AccountAction.rebind => onRebind(),
      },
      itemBuilder: (context) => [
        if (email.isNotEmpty)
          PopupMenuItem<_AccountAction>(
            enabled: false,
            child: Text(email, style: Theme.of(context).textTheme.labelMedium),
          ),
        const PopupMenuItem(
          value: _AccountAction.resync,
          child: ListTile(
            leading: Icon(Icons.sync),
            title: Text('立即同步'),
            contentPadding: EdgeInsets.zero,
          ),
        ),
        const PopupMenuItem(
          value: _AccountAction.rebind,
          child: ListTile(
            leading: Icon(Icons.swap_horiz),
            title: Text('重新绑定邮箱'),
            contentPadding: EdgeInsets.zero,
          ),
        ),
      ],
      child: extended
          ? Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const CircleAvatar(radius: 14, child: Icon(Icons.person, size: 16)),
                const SizedBox(width: 8),
                ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 120),
                  child: Text(
                    email.isEmpty ? '账户' : email,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.labelMedium,
                  ),
                ),
              ],
            )
          : const CircleAvatar(radius: 16, child: Icon(Icons.person, size: 18)),
    );
  }
}
