import { AudioPlayer, createAudioPlayer, setAudioModeAsync } from 'expo-audio';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { GlassCard } from '../components/GlassCard';
import { ApiError, EmailCard, getCards, getMe, Me, retryCard } from '../lib/api';
import { colors } from '../theme';
import { refreshWidget } from '../widget/refresh-widget';

const POLL_MS = 4000;

interface Props {
  onSignOut: () => void;
  playCardId: string | null;
  onPlayedRequestedCard: () => void;
}

export function FeedScreen({ onSignOut, playCardId, onPlayedRequestedCard }: Props) {
  const [me, setMe] = useState<Me | null>(null);
  const [cards, setCards] = useState<EmailCard[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [playingId, setPlayingId] = useState<string | null>(null);
  const playerRef = useRef<AudioPlayer | null>(null);

  const stopAudio = useCallback(() => {
    playerRef.current?.remove();
    playerRef.current = null;
    setPlayingId(null);
  }, []);

  const togglePlay = useCallback(
    (card: EmailCard) => {
      if (!card.audio_url) return;
      if (playingId === card.id) {
        stopAudio();
        return;
      }
      playerRef.current?.remove();
      const player = createAudioPlayer({ uri: card.audio_url });
      player.addListener('playbackStatusUpdate', (status) => {
        if (status.didJustFinish) {
          stopAudio();
        }
      });
      playerRef.current = player;
      setPlayingId(card.id);
      player.play();
    },
    [playingId, stopAudio]
  );

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
    setAudioModeAsync({ playsInSilentMode: true }).catch(() => {});
    getMe()
      .then(setMe)
      .catch((e) => {
        if (e instanceof ApiError && e.status === 401) onSignOut();
      });
    refresh();
    const interval = setInterval(refresh, POLL_MS);
    return () => {
      clearInterval(interval);
      playerRef.current?.remove();
    };
  }, [refresh, onSignOut]);

  // Deep link from the widget: play a specific card's narration on open.
  useEffect(() => {
    if (!playCardId) return;
    const card = cards.find((c) => c.id === playCardId);
    if (card?.audio_url) {
      togglePlay(card);
      onPlayedRequestedCard();
    }
  }, [playCardId, cards, togglePlay, onPlayedRequestedCard]);

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
      <View style={styles.header}>
        <View>
          <Text style={styles.brand}>EmailPartner</Text>
          <Text style={styles.tagline}>
            {me ? me.display_name || me.email : 'your inbox, illustrated'}
          </Text>
        </View>
        <Pressable onPress={onSignOut} style={styles.signOut}>
          <Text style={styles.signOutText}>Sign out</Text>
        </Pressable>
      </View>

      <FlatList
        data={cards}
        keyExtractor={(card) => card.id}
        contentContainerStyle={styles.list}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefreshPull} tintColor={colors.text} />
        }
        ListEmptyComponent={
          <View style={styles.empty}>
            <Text style={styles.emptyBig}>🎨</Text>
            <Text style={styles.emptyText}>
              No cards yet. Send yourself an email and watch it become art.
            </Text>
          </View>
        }
        renderItem={({ item }) => (
          <GlassCard
            card={item}
            playing={playingId === item.id}
            onTogglePlay={togglePlay}
            onRetry={onRetry}
          />
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingTop: 58,
    paddingBottom: 14,
    borderBottomColor: colors.panelBorder,
    borderBottomWidth: 1,
  },
  brand: { color: colors.text, fontWeight: '800', fontSize: 18 },
  tagline: { color: colors.textDim, fontSize: 12, marginTop: 2 },
  signOut: {
    borderColor: colors.panelBorder,
    borderWidth: 1,
    borderRadius: 10,
    paddingVertical: 6,
    paddingHorizontal: 12,
  },
  signOutText: { color: colors.textDim, fontSize: 12 },
  list: { padding: 18, paddingBottom: 60 },
  empty: { alignItems: 'center', paddingTop: 120, paddingHorizontal: 30 },
  emptyBig: { fontSize: 40, marginBottom: 12 },
  emptyText: { color: colors.textDim, textAlign: 'center', fontSize: 14, lineHeight: 21 },
});
