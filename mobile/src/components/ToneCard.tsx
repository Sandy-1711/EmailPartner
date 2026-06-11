import { LinearGradient } from 'expo-linear-gradient';
import React from 'react';
import { Animated, Pressable, StyleSheet, Text, View } from 'react-native';

import { EmailCard, phraseOf, senderOf, summaryOf } from '../lib/api';
import { paletteFor } from '../tones';
import type { Tilt } from '../hooks/useTilt';

interface Props {
  card: EmailCard;
  tilt: Tilt;
  playing: boolean;
  onTogglePlay: (card: EmailCard) => void;
  onRead: (card: EmailCard) => void;
  onRetry: (card: EmailCard) => void;
}

function timeAgo(iso: string | null): string {
  if (!iso) return '';
  const seconds = (Date.now() - new Date(iso).getTime()) / 1000;
  if (seconds < 60) return 'just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

export function ToneCard({ card, tilt, playing, onTogglePlay, onRead, onRetry }: Props) {
  const palette = paletteFor(card.tone);
  const busy = card.processing_status === 'pending' || card.processing_status === 'processing';
  const failed = card.processing_status === 'failed';

  // The gradient layer is oversized and slides opposite to the device tilt —
  // the inspo "background follows the phone" effect.
  const translateX = tilt.x.interpolate({
    inputRange: [-0.5, 0.5],
    outputRange: [36, -36],
  });
  const translateY = tilt.y.interpolate({
    inputRange: [-0.5, 0.5],
    outputRange: [26, -26],
  });

  return (
    <View style={styles.card}>
      <Animated.View style={[styles.bg, { transform: [{ translateX }, { translateY }] }]}>
        <LinearGradient
          colors={[palette.from, palette.to]}
          start={{ x: 0.1, y: 0 }}
          end={{ x: 0.9, y: 1 }}
          style={StyleSheet.absoluteFill}
        />
        <View style={[styles.glow, { backgroundColor: palette.glow }]} />
      </Animated.View>

      <View style={styles.content}>
        <View style={styles.topRow}>
          <Text style={[styles.tone, { color: palette.dim }]}>
            {(card.tone ?? 'email').toUpperCase()}
          </Text>
          <Text style={[styles.time, { color: palette.dim }]}>{timeAgo(card.received_at)}</Text>
        </View>

        <Text style={styles.phrase}>
          {busy ? (card.processing_status === 'processing' ? 'Painting this one…' : 'In the queue…') : phraseOf(card)}
        </Text>

        <Text style={[styles.support, { color: palette.dim }]} numberOfLines={3}>
          {failed ? "Couldn't process this email." : busy ? senderOf(card) : summaryOf(card)}
        </Text>

        <View style={styles.bottomRow}>
          <Text style={[styles.sender, { color: palette.dim }]} numberOfLines={1}>
            {senderOf(card)}
          </Text>
          <View style={styles.actions}>
            {failed ? (
              <Pressable style={styles.action} onPress={() => onRetry(card)}>
                <Text style={styles.actionText}>↻</Text>
              </Pressable>
            ) : (
              <>
                {card.audio_url ? (
                  <Pressable
                    style={[styles.action, playing && { backgroundColor: palette.glow }]}
                    onPress={() => onTogglePlay(card)}
                  >
                    <Text style={styles.actionText}>{playing ? '⏸' : '▶'}</Text>
                  </Pressable>
                ) : null}
                <Pressable style={styles.action} onPress={() => onRead(card)}>
                  <Text style={styles.actionText}>👁</Text>
                </Pressable>
              </>
            )}
          </View>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: 28,
    overflow: 'hidden',
    marginBottom: 18,
    backgroundColor: '#0a0a0c',
  },
  bg: {
    position: 'absolute',
    top: '-18%',
    left: '-18%',
    width: '136%',
    height: '136%',
  },
  glow: {
    position: 'absolute',
    top: -70,
    left: -40,
    width: 230,
    height: 230,
    borderRadius: 115,
    opacity: 0.35,
  },
  content: { padding: 22, minHeight: 210, justifyContent: 'space-between' },
  topRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 18 },
  tone: { fontSize: 11, fontWeight: '700', letterSpacing: 1.6 },
  time: { fontSize: 11, fontWeight: '500' },
  phrase: {
    color: '#ffffff',
    fontSize: 30,
    lineHeight: 35,
    fontWeight: '800',
    letterSpacing: -0.6,
    marginBottom: 10,
  },
  support: { fontSize: 14, lineHeight: 20, marginBottom: 20 },
  bottomRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  sender: { fontSize: 12, fontWeight: '600', flex: 1, marginRight: 12 },
  actions: { flexDirection: 'row', gap: 10 },
  action: {
    width: 46,
    height: 46,
    borderRadius: 23,
    backgroundColor: 'rgba(255,255,255,0.14)',
    borderColor: 'rgba(255,255,255,0.22)',
    borderWidth: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  actionText: { color: '#fff', fontSize: 17 },
});
