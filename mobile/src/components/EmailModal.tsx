import { ChevronDown, ChevronLeft } from 'lucide-react-native';
import React, { useEffect, useState } from 'react';
import {
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import type { Tilt } from '../hooks/useTilt';
import type { Playback } from '../hooks/usePlayback';
import { CardDetail, EmailCard, getCard, phraseOf, senderOf, summaryOf } from '../lib/api';
import { fonts } from '../theme';
import { useTweaks } from '../tweaks';
import { MeshGradient } from './MeshGradient';
import { ToneDot } from './ToneCard';
import { WavePlayer } from './WavePlayer';

interface Props {
  card: EmailCard | null;
  tilt: Tilt;
  playback: Playback;
  onClose: () => void;
}

function timeOf(iso: string | null): string {
  if (!iso) return '';
  const d = new Date(iso);
  const sameDay = new Date().toDateString() === d.toDateString();
  return sameDay
    ? d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
    : d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

export function EmailDetail({ card, tilt, playback, onClose }: Props) {
  const [detail, setDetail] = useState<CardDetail | null>(null);
  const [showFull, setShowFull] = useState(false);
  const { palette: paletteOf, speed, tweaks } = useTweaks();

  useEffect(() => {
    setDetail(null);
    setShowFull(false);
    if (card) {
      getCard(card.id).then(setDetail).catch(() => {});
    }
  }, [card]);

  // Unmount the Modal entirely when closed: toggling `visible` while also
  // changing transparent/animationType breaks dismissal on Android.
  if (!card) {
    return null;
  }

  const palette = paletteOf(card.tone);
  const active = playback.playingId === card.id;
  const playing = active && playback.isPlaying;

  return (
    <Modal visible animationType="slide" onRequestClose={onClose}>
      <View style={styles.root}>
        <MeshGradient palette={palette} tilt={tilt} veil="ambient" drift={160} speed={speed} />

        <View style={styles.topBar}>
          <Pressable onPress={onClose} style={styles.circleButton}>
            <ChevronLeft size={20} color="#fff" strokeWidth={2.2} />
          </Pressable>
          <Text style={[styles.timeTop, { color: 'rgba(255,255,255,0.5)' }]}>
            {timeOf(card.received_at)}
          </Text>
        </View>

        <ScrollView style={styles.scroll} contentContainerStyle={styles.scrollInner}>
          <View style={styles.toneRow}>
            <ToneDot color={palette.dot} />
            <Text style={styles.toneLabel}>{palette.label.toUpperCase()}</Text>
          </View>

          <Text
            style={[
              styles.phrase,
              { fontSize: 40 * tweaks.fontScale, lineHeight: 41 * tweaks.fontScale },
            ]}
          >
            {phraseOf(card)}
          </Text>

          <View style={styles.senderRow}>
            <View style={styles.avatar}>
              <Text style={styles.avatarText}>{senderOf(card)[0]?.toUpperCase() ?? '?'}</Text>
            </View>
            <View style={{ flex: 1, minWidth: 0 }}>
              <Text style={styles.senderName}>{senderOf(card)}</Text>
              <Text style={styles.subject} numberOfLines={1}>
                {card.subject ?? ''}
              </Text>
            </View>
          </View>

          {card.audio_url ? (
            <View style={styles.playerCard}>
              <View style={styles.playerHeader}>
                <Text style={[styles.playerLabel, { color: palette.accent }]}>AUDIO SUMMARY</Text>
                <Text style={styles.playerSpeed}>1.0×</Text>
              </View>
              <WavePlayer
                emailId={card.id}
                palette={palette}
                playing={playing}
                progress={active ? playback.progress : 0}
                duration={active ? playback.duration : 0}
                onToggle={() => playback.toggle(card)}
                size="hero"
              />
            </View>
          ) : null}

          <Text style={styles.sectionLabel}>THE GIST</Text>
          <Text style={[styles.gist, { fontSize: 19 * tweaks.fontScale }]}>
            {summaryOf(card)}
          </Text>

          <Pressable onPress={() => setShowFull((s) => !s)} style={styles.fullToggle}>
            <Text style={styles.fullToggleText}>Read full email</Text>
            <ChevronDown
              size={18}
              color="#fff"
              strokeWidth={2.2}
              style={showFull ? { transform: [{ rotate: '180deg' }] } : undefined}
            />
          </Pressable>
          {showFull && (
            <Text style={styles.fullBody}>
              {detail ? detail.body || detail.snippet || '(no content)' : 'Loading…'}
            </Text>
          )}
          <View style={{ height: 40 }} />
        </ScrollView>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#070510' },
  topBar: {
    paddingTop: 54,
    paddingHorizontal: 18,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  circleButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.14)',
    backgroundColor: 'rgba(255,255,255,0.08)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  circleGlyph: { color: '#fff', fontSize: 24, lineHeight: 26, marginTop: -2 },
  timeTop: { fontFamily: fonts.medium, fontSize: 13 },
  scroll: { flex: 1 },
  scrollInner: { paddingHorizontal: 24 },
  toneRow: { marginTop: 24, flexDirection: 'row', alignItems: 'center', gap: 8 },
  toneLabel: {
    color: 'rgba(255,255,255,0.92)',
    fontFamily: fonts.semibold,
    fontSize: 12,
    letterSpacing: 0.7,
  },
  phrase: {
    marginTop: 14,
    color: '#fff',
    fontFamily: fonts.semibold,
    fontSize: 40,
    lineHeight: 41,
    letterSpacing: -1.1,
  },
  senderRow: { marginTop: 18, flexDirection: 'row', alignItems: 'center', gap: 11 },
  avatar: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: 'rgba(255,255,255,0.14)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  avatarText: { color: '#fff', fontFamily: fonts.semibold, fontSize: 15 },
  senderName: { color: '#fff', fontFamily: fonts.semibold, fontSize: 15 },
  subject: { color: 'rgba(255,255,255,0.55)', fontFamily: fonts.medium, fontSize: 13, marginTop: 1 },
  playerCard: {
    marginTop: 24,
    padding: 22,
    paddingBottom: 20,
    borderRadius: 26,
    backgroundColor: 'rgba(0,0,0,0.34)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.1)',
  },
  playerHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 18,
  },
  playerLabel: { fontFamily: fonts.semibold, fontSize: 12, letterSpacing: 0.7 },
  playerSpeed: { color: 'rgba(255,255,255,0.5)', fontFamily: fonts.medium, fontSize: 12 },
  sectionLabel: {
    marginTop: 22,
    marginBottom: 10,
    color: 'rgba(255,255,255,0.5)',
    fontFamily: fonts.semibold,
    fontSize: 11,
    letterSpacing: 0.8,
  },
  gist: {
    color: 'rgba(255,255,255,0.92)',
    fontFamily: fonts.regular,
    fontSize: 19,
    lineHeight: 28,
    letterSpacing: -0.2,
  },
  fullToggle: {
    marginTop: 22,
    paddingVertical: 14,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255,255,255,0.12)',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  fullToggleText: { color: '#fff', fontFamily: fonts.semibold, fontSize: 14 },
  chevron: { color: '#fff', fontSize: 16 },
  fullBody: {
    color: 'rgba(255,255,255,0.74)',
    fontFamily: fonts.regular,
    fontSize: 16,
    lineHeight: 26,
  },
});
