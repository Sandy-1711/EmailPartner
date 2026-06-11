import { LinearGradient } from 'expo-linear-gradient';
import React from 'react';
import { Animated, Image, Pressable, StyleSheet, Text, View } from 'react-native';

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

const TONE_GLYPH: Record<string, string> = {
  urgent: '!',
  informative: 'i',
  social: '☺',
  promotional: '%',
  transactional: '✓',
};

export function ToneCard({ card, tilt, playing, onTogglePlay, onRead, onRetry }: Props) {
  const palette = paletteFor(card.tone);
  const busy = card.processing_status === 'pending' || card.processing_status === 'processing';
  const failed = card.processing_status === 'failed';

  // Oversized glow layer sliding against device tilt — the background itself
  // moves, content stays put.
  const translateX = tilt.x.interpolate({ inputRange: [-0.5, 0.5], outputRange: [70, -70] });
  const translateY = tilt.y.interpolate({ inputRange: [-0.5, 0.5], outputRange: [50, -50] });

  return (
    <View style={styles.card}>
      <Animated.View style={[styles.bg, { transform: [{ translateX }, { translateY }] }]}>
        {/* deep base */}
        <LinearGradient
          colors={['#101013', '#0a0a0c']}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={StyleSheet.absoluteFill}
        />
        {/* dominant corner glow, stacked for a soft radial falloff */}
        <View style={[styles.glowHuge, { backgroundColor: palette.from }]} />
        <View style={[styles.glowMid, { backgroundColor: palette.from }]} />
        <View style={[styles.glowCore, { backgroundColor: palette.glow }]} />
      </Animated.View>

      <View style={styles.content}>
        <View style={styles.topRow}>
          <View style={styles.topLeft}>
            <View style={styles.glyphCircle}>
              <Text style={[styles.glyph, { color: palette.glow }]}>
                {TONE_GLYPH[card.tone ?? ''] ?? '✉'}
              </Text>
            </View>
            <Text style={styles.toneLabel}>{(card.tone ?? 'email').toUpperCase()}</Text>
          </View>
          <View style={styles.topRight}>
            <View style={styles.senderPill}>
              <Text style={styles.senderPillText} numberOfLines={1}>
                {senderOf(card)}
              </Text>
            </View>
            <Pressable style={styles.arrowCircle} onPress={() => onRead(card)}>
              <Text style={styles.arrowText}>↗</Text>
            </Pressable>
          </View>
        </View>

        <View style={styles.middle}>
          <Text style={styles.phrase}>
            {busy ? (card.processing_status === 'processing' ? 'Working on it…' : 'Queued…') : phraseOf(card)}
            <Text style={[styles.phraseMark, { color: palette.glow }]}>{busy || failed ? '' : ' ↗'}</Text>
          </Text>
          {failed ? (
            <Text style={styles.body}>
              <Text style={styles.bodyBold}>Couldn't process this email. </Text>
              <Text style={styles.bodyDim}>Tap retry to run it again.</Text>
            </Text>
          ) : (
            <Text style={styles.body} numberOfLines={3}>
              <Text style={styles.bodyBold}>{busy ? senderOf(card) : `${summaryOf(card).split('. ')[0]}`} </Text>
              <Text style={styles.bodyDim}>{busy ? '' : summaryOf(card).split('. ').slice(1).join('. ')}</Text>
            </Text>
          )}
        </View>

        <View style={styles.bottomRow}>
          <View style={styles.bottomLeft}>
            {failed ? (
              <Pressable style={styles.listenPill} onPress={() => onRetry(card)}>
                <Text style={styles.listenText}>↻  Retry</Text>
              </Pressable>
            ) : card.audio_url ? (
              <Pressable
                style={[styles.listenPill, playing && { backgroundColor: palette.from }]}
                onPress={() => onTogglePlay(card)}
              >
                <Text style={styles.listenText}>{playing ? '⏸  Playing' : '▶  Listen'}</Text>
              </Pressable>
            ) : null}
            {card.background_image_url ? (
              <Image source={{ uri: card.background_image_url }} style={styles.thumb} />
            ) : null}
          </View>
        </View>

        <View style={styles.dots}>
          <View style={[styles.dot, styles.dotActive]} />
          {[...Array(5)].map((_, i) => (
            <View key={i} style={styles.dot} />
          ))}
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: 34,
    overflow: 'hidden',
    marginBottom: 20,
    backgroundColor: '#0a0a0c',
  },
  bg: {
    position: 'absolute',
    top: '-25%',
    left: '-25%',
    width: '150%',
    height: '150%',
  },
  glowHuge: {
    position: 'absolute',
    top: '-22%',
    left: '-18%',
    width: 460,
    height: 460,
    borderRadius: 230,
    opacity: 0.42,
  },
  glowMid: {
    position: 'absolute',
    top: '-12%',
    left: '-10%',
    width: 320,
    height: 320,
    borderRadius: 160,
    opacity: 0.5,
  },
  glowCore: {
    position: 'absolute',
    top: '-6%',
    left: '-4%',
    width: 190,
    height: 190,
    borderRadius: 95,
    opacity: 0.55,
  },
  content: { padding: 22, minHeight: 330 },

  topRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  topLeft: { flexDirection: 'row', alignItems: 'center', flexShrink: 1 },
  glyphCircle: {
    width: 34,
    height: 34,
    borderRadius: 17,
    backgroundColor: 'rgba(255,255,255,0.16)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.22)',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 9,
  },
  glyph: { fontSize: 15, fontWeight: '800' },
  toneLabel: { color: '#ffffff', fontSize: 13, fontWeight: '600', letterSpacing: 0.3 },
  topRight: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  senderPill: {
    maxWidth: 150,
    borderRadius: 19,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.3)',
    backgroundColor: 'rgba(255,255,255,0.07)',
    paddingHorizontal: 14,
    paddingVertical: 9,
  },
  senderPillText: { color: '#ffffff', fontSize: 12.5, fontWeight: '600' },
  arrowCircle: {
    width: 38,
    height: 38,
    borderRadius: 19,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.3)',
    backgroundColor: 'rgba(255,255,255,0.07)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  arrowText: { color: '#ffffff', fontSize: 16, fontWeight: '600' },

  middle: { flex: 1, justifyContent: 'center', paddingVertical: 26 },
  phrase: {
    color: '#ffffff',
    fontSize: 40,
    lineHeight: 46,
    fontWeight: '800',
    letterSpacing: -1,
    marginBottom: 16,
  },
  phraseMark: { fontSize: 26, fontWeight: '700' },
  body: { fontSize: 15, lineHeight: 22 },
  bodyBold: { color: '#ffffff', fontWeight: '700' },
  bodyDim: { color: 'rgba(255,255,255,0.45)', fontWeight: '400' },

  bottomRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  bottomLeft: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  listenPill: {
    borderRadius: 22,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.3)',
    backgroundColor: 'rgba(255,255,255,0.1)',
    paddingHorizontal: 18,
    paddingVertical: 11,
  },
  listenText: { color: '#ffffff', fontSize: 13, fontWeight: '700' },
  thumb: {
    width: 86,
    height: 54,
    borderRadius: 27,
    opacity: 0.9,
  },

  dots: { flexDirection: 'row', gap: 6, marginTop: 18 },
  dot: {
    flex: 1,
    height: 3,
    borderRadius: 2,
    backgroundColor: 'rgba(255,255,255,0.16)',
  },
  dotActive: { backgroundColor: '#ffffff' },
});
