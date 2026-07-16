// Calm, low-arousal visual system. Deliberately not gamified: muted palette,
// generous spacing, no aggressive reds/greens for "streaks", no badges.

export const colors = {
  bg: '#F5F3EF', // warm paper
  surface: '#FFFFFF',
  surfaceAlt: '#EDEAE3',
  text: '#2B2A28',
  textMuted: '#6B665E',
  primary: '#3E5C50', // muted forest — grounding, not urgent
  primarySoft: '#DCE5DF',
  accent: '#8A6D5B', // warm clay
  border: '#E2DED6',
  danger: '#7A4A45', // muted, never alarm-red
  crisisBg: '#EFEAE4', // calm, not red
  crisisAccent: '#4A6B7A',
};

export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
};

export const radius = {
  sm: 8,
  md: 14,
  lg: 22,
};

export const type = {
  h1: { fontSize: 28, fontWeight: '600' as const, color: colors.text },
  h2: { fontSize: 21, fontWeight: '600' as const, color: colors.text },
  body: { fontSize: 17, lineHeight: 26, color: colors.text },
  bodyMuted: { fontSize: 16, lineHeight: 24, color: colors.textMuted },
  small: { fontSize: 13, color: colors.textMuted },
};
