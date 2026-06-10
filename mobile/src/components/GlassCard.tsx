import React from 'react';
import {
  ImageBackground,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { EmailCard, headlineOf, senderOf, summaryOf } from '../lib/api';
import { colors, radius } from '../theme';

interface Props {
  card: EmailCard;
  playing: boolean;
  onTogglePlay: (card: EmailCard) => void;
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

export function GlassCard({ card, playing, onTogglePlay, onRetry }: Props) {
  const busy = card.processing_status === 'pending' || card.processing_status === 'processing';
  const failed = card.processing_status === 'failed';

  return (
    <View style={styles.card}>
      <View style={styles.art}>
        {card.background_image_url ? (
          <ImageBackground
            source={{ uri: card.background_image_url }}
            style={styles.artImage}
            resizeMode="cover"
          >
            {card.audio_url ? (
              <Pressable
                style={[styles.playButton, playing && styles.playButtonActive]}
                onPress={() => onTogglePlay(card)}
              >
                <Text style={styles.playIcon}>{playing ? '⏸' : '▶'}</Text>
              </Pressable>
            ) : null}
          </ImageBackground>
        ) : (
          <View style={[styles.artImage, styles.artFallback]}>
            <Text style={styles.fallbackText}>
              {busy ? (card.processing_status === 'processing' ? 'painting…' : 'queued') : headlineOf(card)}
            </Text>
          </View>
        )}
      </View>

      <View style={styles.body}>
        <Text style={styles.headline}>{headlineOf(card)}</Text>
        {failed ? (
          <Text style={styles.failedNote}>Couldn't process this email.</Text>
        ) : (
          <Text style={styles.summary}>{summaryOf(card)}</Text>
        )}
        <View style={styles.meta}>
          <Text style={styles.from} numberOfLines={1}>
            {senderOf(card)}
          </Text>
          {failed ? (
            <Pressable style={styles.retry} onPress={() => onRetry(card)}>
              <Text style={styles.retryText}>Retry</Text>
            </Pressable>
          ) : (
            <Text style={styles.time}>{timeAgo(card.received_at)}</Text>
          )}
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.panel,
    borderColor: colors.panelBorder,
    borderWidth: 1,
    borderRadius: radius,
    overflow: 'hidden',
    marginBottom: 18,
  },
  art: { aspectRatio: 16 / 9, backgroundColor: '#131722' },
  artImage: { flex: 1, justifyContent: 'flex-end', alignItems: 'flex-end' },
  artFallback: {
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(124, 155, 255, 0.12)',
    padding: 18,
  },
  fallbackText: { color: colors.text, fontWeight: '600', fontSize: 16, textAlign: 'center' },
  playButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    margin: 12,
    backgroundColor: 'rgba(0,0,0,0.5)',
    borderColor: 'rgba(255,255,255,0.25)',
    borderWidth: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  playButtonActive: { backgroundColor: 'rgba(124,155,255,0.75)' },
  playIcon: { color: '#fff', fontSize: 16 },
  body: { padding: 16, gap: 8 },
  headline: { color: colors.text, fontWeight: '700', fontSize: 17, lineHeight: 22 },
  summary: { color: colors.textDim, fontSize: 14, lineHeight: 20 },
  failedNote: { color: colors.danger, fontSize: 14 },
  meta: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderTopColor: colors.panelBorder,
    borderTopWidth: 1,
    paddingTop: 11,
    marginTop: 4,
  },
  from: { color: colors.textDim, fontSize: 12, flex: 1, marginRight: 10 },
  time: { color: colors.textDim, fontSize: 12 },
  retry: {
    backgroundColor: 'rgba(255, 122, 122, 0.12)',
    borderColor: 'rgba(255, 122, 122, 0.35)',
    borderWidth: 1,
    borderRadius: 10,
    paddingVertical: 6,
    paddingHorizontal: 13,
  },
  retryText: { color: colors.danger, fontSize: 13 },
});
