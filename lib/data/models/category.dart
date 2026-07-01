import 'package:objectbox/objectbox.dart';

@Entity()
class Category {
  @Id()
  int id = 0;

  String name = '';

  /// Hex color string, e.g. "#2563EB".
  String colorHex = '#6B7280';

  /// IMAP folder name where emails of this category are archived.
  String targetFolder = '';

  /// Optional prompt fragment passed to Claude when classifying.
  String? aiHint;
}
