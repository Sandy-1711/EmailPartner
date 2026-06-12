import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { EmailDetail } from '../components/EmailModal';
import { MeshGradient } from '../components/MeshGradient';
import { EchoCard } from '../components/ToneCard';
import { usePlayback } from '../hooks/usePlayback';
import { useTilt } from '../hooks/useTilt';
import { ApiError, EmailCard, getCards, getMe, Me, retryCard } from '../lib/api';
import { colors, fonts } from '../theme';
import { TONES } from '../tones';
import { refreshWidget } from '../widget/refresh-widget';

const POLL_MS = 4000;

interface Props {
  onSignOut: () => void;
  playCardId: string | null;
  onPlayedRequestedCard: () => void;
  readCardId: string | null;
  onReadHandled: () => void;
}

export function FeedScreen({
  onSignOut,
  playCardId,
  onPlayedRequestedCard,
  readCardId,
  onReadHandled,
}: Props) {
  const [me, setMe] = useState<Me | null>(null);
  const [cards, setCards] = useState<EmailCard[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [openCard, setOpenCard] = useState<EmailCard | null>(null);
  const tilt = useTilt();
  const playback = usePlayback();

  const refresh = useCallback(async () => {
    try {
      const data = await getCards();
      setCards(data.items);
      refreshWidget(data.items);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        onSignOut();
      }
    }
  }, [onSignOut]);

  useEffect(() => {
    getMe()
      .then(setMe)
      .catch((e) => {
        if (e instanceof ApiError && e.status === 401) onSignOut();
      });
    refresh();
    const interval = setInterval(refresh, POLL_MS);
    return () => clearInterval(interval);
  }, [refresh, onSignOut]);

  // Widget "listen" tap: play that card's narration once cards are loaded.
  // Ref guard: playingId changes recreate toggle; without it the effect
  // re-fires and toggles playback straight back off.
  const handledPlayRef = useRef<string | null>(null);
  useEffect(() => {
    if (!playCardId || handledPlayRef.current === playCardId) return;
    const card = cards.find((c) => c.id === playCardId);
    if (card?.audio_url) {
      handledPlayRef.current = playCardId;
      playback.toggle(card);
      onPlayedRequestedCard();
    }
  }, [playCardId, cards, playback, onPlayedRequestedCard]);

  // Widget "read" tap: open the detail screen.
  useEffect(() => {
    if (!readCardId) return;
    const card = cards.find((c) => c.id === readCardId);
    if (card) {
      setOpenCard(card);
      onReadHandled();
    }
  }, [readCardId, cards, onReadHandled]);

  async function onRefreshPull() {
    setRefreshing(true);
    await refresh();
    setRefreshing(false);
  }

  async function onRetry(card: EmailCard) {
    try {
      await retryCard(card.id);
      setTimeout(refresh, 800);
    } catch {
      // surfaced on next poll
    }
  }

  return (
    <View style={styles.container}>
      {/* faint ambient mesh behind the whole inbox, like the design */}
      <View style={StyleSheet.absoluteFill}>
        <MeshGradient palette={TONES.informative} veil="ambient" drift={200} />
      </View>

      <View style={styles.header}>
        <View>
          <Text style={styles.kicker}>{me ? me.display_name || me.email : 'ECHO MAIL'}</Text>
          <Text style={styles.title}>Inbox</Text>
        </View>
        <View style={styles.headerRight}>
          <Text style={styles.count}>{cards.length} summaries</Text>
          <Pressable onPress={onSignOut} hitSlop={8}>
            <Text style={styles.signOut}>Sign out</Text>
          </Pressable>
        </View>
      </View>

      <FlatList
        data={cards}
        keyExtractor={(card) => card.id}
        contentContainerStyle={styles.list}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefreshPull} tintColor="#fff" />
        }
        ListEmptyComponent={
          <View style={styles.empty}>
            <Text style={styles.emptyTitle}>Nothing yet</Text>
            <Text style={styles.emptyText}>
              Send yourself an email and watch it become a summary you can hear.
            </Text>
          </View>
        }
        renderItem={({ item }) => (
          <EchoCard
            card={item}
            tilt={tilt}
            playing={playback.playingId === item.id && playback.isPlaying}
            onTogglePlay={playback.toggle}
            onOpen={setOpenCard}
            onRetry={onRetry}
          />
        )}
      />

      <EmailDetail
        card={openCard}
        tilt={tilt}
        playback={playback}
        onClose={() => setOpenCard(null)}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  header: {
    paddingTop: 58,
    paddingHorizontal: 22,
    paddingBottom: 16,
    flexDirection: 'row',
    alignItems: 'flex-end',
    justifyContent: 'space-between',
  },
  kicker: {
    color: 'rgba(255,255,255,0.55)',
    fontFamily: fonts.semibold,
    fontSize: 12,
    letterSpacing: 0.6,
    marginBottom: 8,
  },
  title: { color: '#fff', fontFamily: fonts.semibold, fontSize: 30, letterSpacing: -0.6 },
  headerRight: { alignItems: 'flex-end', gap: 6, paddingBottom: 4 },
  count: { color: 'rgba(255,255,255,0.5)', fontFamily: fonts.medium, fontSize: 13 },
  signOut: { color: 'rgba(255,255,255,0.35)', fontFamily: fonts.semibold, fontSize: 12 },
  list: { paddingHorizontal: 14, paddingBottom: 28 },
  empty: { alignItems: 'center', paddingTop: 110, paddingHorizontal: 36 },
  emptyTitle: { color: '#fff', fontFamily: fonts.semibold, fontSize: 22, marginBottom: 10 },
  emptyText: {
    color: 'rgba(255,255,255,0.55)',
    fontFamily: fonts.regular,
    fontSize: 15,
    lineHeight: 22,
    textAlign: 'center',
  },
});
