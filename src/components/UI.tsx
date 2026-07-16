// Small shared UI kit. Kept intentionally minimal and dependency-light.
import React from 'react';
import {
  Text,
  TouchableOpacity,
  View,
  StyleSheet,
  ScrollView,
  TextInput,
  TextInputProps,
  ViewStyle,
} from 'react-native';
import { colors, spacing, radius, type } from '../theme/theme';

export function Screen({ children, scroll = true }: { children: React.ReactNode; scroll?: boolean }) {
  if (scroll) {
    return (
      <ScrollView style={styles.screen} contentContainerStyle={styles.screenContent} keyboardShouldPersistTaps="handled">
        {children}
      </ScrollView>
    );
  }
  return <View style={[styles.screen, styles.screenContent]}>{children}</View>;
}

export function H1({ children }: { children: React.ReactNode }) {
  return <Text style={[type.h1, { marginBottom: spacing.md }]}>{children}</Text>;
}
export function H2({ children }: { children: React.ReactNode }) {
  return <Text style={[type.h2, { marginBottom: spacing.sm }]}>{children}</Text>;
}
export function Body({ children, muted }: { children: React.ReactNode; muted?: boolean }) {
  return <Text style={[muted ? type.bodyMuted : type.body, { marginBottom: spacing.md }]}>{children}</Text>;
}
export function Small({ children }: { children: React.ReactNode }) {
  return <Text style={type.small}>{children}</Text>;
}

export function Card({ children, style }: { children: React.ReactNode; style?: ViewStyle }) {
  return <View style={[styles.card, style]}>{children}</View>;
}

export function Button({
  label,
  onPress,
  variant = 'primary',
  disabled,
}: {
  label: string;
  onPress: () => void;
  variant?: 'primary' | 'soft' | 'ghost';
  disabled?: boolean;
}) {
  const bg =
    variant === 'primary' ? colors.primary : variant === 'soft' ? colors.primarySoft : 'transparent';
  const fg = variant === 'primary' ? '#fff' : colors.primary;
  return (
    <TouchableOpacity
      style={[styles.button, { backgroundColor: bg, opacity: disabled ? 0.5 : 1, borderWidth: variant === 'ghost' ? 1 : 0, borderColor: colors.border }]}
      onPress={onPress}
      disabled={disabled}
      accessibilityRole="button"
    >
      <Text style={[styles.buttonText, { color: fg }]}>{label}</Text>
    </TouchableOpacity>
  );
}

export function ChoiceButton({ label, onPress }: { label: string; onPress: () => void }) {
  return (
    <TouchableOpacity style={styles.choice} onPress={onPress} accessibilityRole="button">
      <Text style={styles.choiceText}>{label}</Text>
    </TouchableOpacity>
  );
}

export function Field(props: TextInputProps) {
  return (
    <TextInput
      {...props}
      style={[styles.field, props.multiline && { minHeight: 120, textAlignVertical: 'top' }, props.style]}
      placeholderTextColor={colors.textMuted}
    />
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  screenContent: { padding: spacing.lg, paddingBottom: spacing.xxl },
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    padding: spacing.lg,
    marginBottom: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
  },
  button: {
    paddingVertical: 14,
    paddingHorizontal: spacing.lg,
    borderRadius: radius.md,
    alignItems: 'center',
    marginTop: spacing.sm,
  },
  buttonText: { fontSize: 17, fontWeight: '600' },
  choice: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    padding: spacing.md,
    marginBottom: spacing.sm,
    borderWidth: 1,
    borderColor: colors.border,
  },
  choiceText: { fontSize: 17, color: colors.text, lineHeight: 24 },
  field: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    padding: spacing.md,
    fontSize: 17,
    color: colors.text,
    borderWidth: 1,
    borderColor: colors.border,
    marginBottom: spacing.md,
  },
});
