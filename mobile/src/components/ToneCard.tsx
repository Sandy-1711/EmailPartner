import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import type { Tilt } from '../hooks/useTilt';
import { EmailCard, phraseOf, senderOf, summaryOf } from '../lib/api';
import { fonts } from '../theme';
import { useTweaks } from '../tweaks';
import { MeshGradient } from './MeshGradient';

interface Props {
  card: EmailCard;
  tilt: Tilt;
  playing: boolean;
  onTogglePlay: (card: EmailCard) => void;
  onOpen: (card: EmailCard) => void;
  onRetry: (card: EmailCard) => void;
}

function timeOf(iso: string | null): string {
  if (!iso) return '';
  const d = new Date(iso);
  const sameDay = new Date().toDateString() === d.toDateString();
  if (sameDay) {
    return d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
  }
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

export function ToneDot({ color }: { color: string }) {
  return (
    <View
      style={{
        width: 7,
        height: 7,
        borderRadius: 4,
        backgroundColor: color,
        shadowColor: color,
        shadowOpacity: 1,
        shadowRadius: 5,
        shadowOffset: { width: 0, height: 0 },
        elevation: 2,
      }}
    />
  );
}

export function EchoCard({ card, tilt, playing, onTogglePlay, onOpen, onRetry }: Props) {
  const { palette: paletteOf, speed, tweaks } = useTweaks();
  const palette = paletteOf(card.tone);
  const busy = card.processing_status === 'pending' || card.processing_status === 'processing';
  const failed = card.processing_status === 'failed';
  const compact = tweaks.density === 'compact';

  return (
    <Pressable onPress={() => !busy && onOpen(card)} style={styles.card}>
      <MeshGradient palette={palette} tilt={tilt} veil="card" speed={speed} />

      <View style={[styles.content, compact && { paddingVertical: 12 }]}>
        <View style={styles.headerRow}>
          <View style={styles.headerLeft}>
            <ToneDot color={palette.dot} />
            <Text style={styles.sender} numberOfLines={1}>
              {senderOf(card).toUpperCase()}
            </Text>
          </View>
          <Text style={styles.time}>{timeOf(card.received_at)}</Text>
        </View>

        <Text
          style={[
            styles.phrase,
            { fontSize: 24 * tweaks.fontScale, lineHeight: 26 * tweaks.fontScale },
            compact && { marginBottom: 10 },
          ]}
        >
          {busy
            ? card.processing_status === 'processing'
              ? 'Summarizing…'
              : 'In the queue'
            : phraseOf(card)}
        </Text>

        <View style={styles.footerRow}>
          {failed ? (
            <Pressable onPress={() => onRetry(card)} style={styles.playPill}>
              <View style={[styles.playCircle, { backgroundColor: palette.accent }]}>
                <Text style={styles.playGlyph}>↻</Text>
              </View>
              <Text style={styles.playText}>Retry</Text>
            </Pressable>
          ) : card.audio_url ? (
            <Pressable onPress={() => onTogglePlay(card)} style={styles.playPill}>
              <View style={[styles.playCircle, { backgroundColor: palette.accent }]}>
                <Text style={styles.playGlyph}>{playing ? '⏸' : '▶'}</Text>
              </View>
              <Text style={styles.playText}>{playing ? 'Playing' : 'Listen'}</Text>
            </Pressable>
          ) : null}
          <Text style={styles.snippet} numberOfLines={1}>
            {failed ? "Couldn't process this email" : summaryOf(card)}
          </Text>
        </View>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: 22,
    overflow: 'hidden',
    marginBottom: 11,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.08)',
  },
  content: { padding: 18, paddingVertical: 17 },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  headerLeft: { flexDirection: 'row', alignItems: 'center', gap: 7, flexShrink: 1, paddingRight: 8 },
  sender: {
    color: 'rgba(255,255,255,0.9)',
    fontFamily: fonts.semibold,
    fontSize: 11,
    letterSpacing: 0.55,
  },
  time: { color: 'rgba(255,255,255,0.7)', fontFamily: fonts.medium, fontSize: 12, flexShrink: 0 },
  phrase: {
    color: '#fff',
    fontFamily: fonts.semibold,
    fontSize: 24,
    lineHeight: 26,
    letterSpacing: -0.5,
    marginBottom: 14,
  },
  footerRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  playPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 9,
    paddingVertical: 7,
    paddingLeft: 9,
    paddingRight: 13,
    borderRadius: 999,
    backgroundColor: 'rgba(0,0,0,0.28)',
  },
  playCircle: {
    width: 26,
    height: 26,
    borderRadius: 13,
    justifyContent: 'center',
    alignItems: 'center',
  },
  playGlyph: { color: '#0a0612', fontSize: 11, lineHeight: 13 },
  playText: { color: '#fff', fontFamily: fonts.semibold, fontSize: 12 },
  snippet: {
    flex: 1,
    color: 'rgba(255,255,255,0.6)',
    fontFamily: fonts.medium,
    fontSize: 13,
  },
});
