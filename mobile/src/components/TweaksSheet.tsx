import React from 'react';
import { Modal, Pressable, StyleSheet, Text, View } from 'react-native';

import { fonts } from '../theme';
import {
  Density,
  FONT_OPTIONS,
  HUE_OPTIONS,
  Motion,
  useTweaks,
} from '../tweaks';

interface Props {
  visible: boolean;
  onClose: () => void;
}

function Chip({
  label,
  active,
  onPress,
}: {
  label: string;
  active: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable
      onPress={onPress}
      style={[styles.chip, active && styles.chipActive]}
    >
      <Text style={[styles.chipText, active && styles.chipTextActive]}>{label}</Text>
    </Pressable>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <View style={styles.row}>
      <Text style={styles.rowLabel}>{label.toUpperCase()}</Text>
      <View style={styles.chips}>{children}</View>
    </View>
  );
}

export function TweaksSheet({ visible, onClose }: Props) {
  const { tweaks, setTweak } = useTweaks();
  if (!visible) return null;

  const motions: { label: string; value: Motion }[] = [
    { label: 'Off', value: 'off' },
    { label: 'Calm', value: 'calm' },
    { label: 'Normal', value: 'normal' },
    { label: 'Lively', value: 'lively' },
  ];
  const densities: { label: string; value: Density }[] = [
    { label: 'Compact', value: 'compact' },
    { label: 'Cozy', value: 'cozy' },
  ];

  return (
    <Modal visible transparent animationType="slide" onRequestClose={onClose}>
      <Pressable style={styles.backdrop} onPress={onClose}>
        <Pressable style={styles.sheet} onPress={() => {}}>
          <View style={styles.handle} />
          <Text style={styles.title}>Tweaks</Text>

          <Row label="Motion">
            {motions.map((m) => (
              <Chip
                key={m.value}
                label={m.label}
                active={tweaks.motion === m.value}
                onPress={() => setTweak('motion', m.value)}
              />
            ))}
          </Row>

          <Row label="Hue">
            {HUE_OPTIONS.map((h) => (
              <Chip
                key={h.label}
                label={h.label}
                active={tweaks.hue === h.value}
                onPress={() => setTweak('hue', h.value)}
              />
            ))}
          </Row>

          <Row label="Font size">
            {FONT_OPTIONS.map((f) => (
              <Chip
                key={f.label}
                label={f.label}
                active={tweaks.fontScale === f.value}
                onPress={() => setTweak('fontScale', f.value)}
              />
            ))}
          </Row>

          <Row label="Density">
            {densities.map((d) => (
              <Chip
                key={d.value}
                label={d.label}
                active={tweaks.density === d.value}
                onPress={() => setTweak('density', d.value)}
              />
            ))}
          </Row>
        </Pressable>
      </Pressable>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: { flex: 1, backgroundColor: 'rgba(0,0,0,0.55)', justifyContent: 'flex-end' },
  sheet: {
    backgroundColor: '#0d0a1a',
    borderTopLeftRadius: 26,
    borderTopRightRadius: 26,
    paddingHorizontal: 22,
    paddingBottom: 34,
    paddingTop: 10,
    borderTopWidth: 1,
    borderColor: 'rgba(255,255,255,0.1)',
  },
  handle: {
    alignSelf: 'center',
    width: 44,
    height: 5,
    borderRadius: 3,
    backgroundColor: 'rgba(255,255,255,0.25)',
    marginBottom: 16,
  },
  title: { color: '#fff', fontFamily: fonts.semibold, fontSize: 22, marginBottom: 18 },
  row: { marginBottom: 18 },
  rowLabel: {
    color: 'rgba(255,255,255,0.5)',
    fontFamily: fonts.semibold,
    fontSize: 11,
    letterSpacing: 0.8,
    marginBottom: 10,
  },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  chip: {
    paddingHorizontal: 16,
    paddingVertical: 9,
    borderRadius: 999,
    backgroundColor: 'rgba(255,255,255,0.08)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.12)',
  },
  chipActive: { backgroundColor: '#f0d6ff', borderColor: '#f0d6ff' },
  chipText: { color: 'rgba(255,255,255,0.8)', fontFamily: fonts.semibold, fontSize: 13 },
  chipTextActive: { color: '#0a0612' },
});
