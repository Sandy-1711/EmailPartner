import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { CardDetail, getCard, senderOf } from '../lib/api';
import { paletteFor } from '../tones';
import { colors } from '../theme';

interface Props {
  cardId: string | null;
  onClose: () => void;
}

export function EmailModal({ cardId, onClose }: Props) {
  const [detail, setDetail] = useState<CardDetail | null>(null);

  useEffect(() => {
    setDetail(null);
    if (cardId) {
      getCard(cardId).then(setDetail).catch(() => {});
    }
  }, [cardId]);

  const palette = paletteFor(detail?.tone);

  return (
    <Modal visible={cardId !== null} animationType="slide" transparent onRequestClose={onClose}>
      <View style={styles.backdrop}>
        <View style={styles.sheet}>
          <View style={[styles.accent, { backgroundColor: palette.from }]} />
          <View style={styles.header}>
            <Text style={styles.subject} numberOfLines={2}>
              {detail?.subject ?? ' '}
            </Text>
            <Pressable onPress={onClose} style={styles.close}>
              <Text style={styles.closeText}>✕</Text>
            </Pressable>
          </View>
          {detail ? (
            <>
              <Text style={[styles.from, { color: palette.dim }]}>{senderOf(detail)}</Text>
              <ScrollView style={styles.bodyScroll} contentContainerStyle={{ paddingBottom: 30 }}>
                <Text style={styles.body}>{detail.body || detail.snippet || '(no content)'}</Text>
              </ScrollView>
            </>
          ) : (
            <View style={styles.loading}>
              <ActivityIndicator color={palette.from} />
            </View>
          )}
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: { flex: 1, backgroundColor: 'rgba(0,0,0,0.6)', justifyContent: 'flex-end' },
  sheet: {
    backgroundColor: '#101218',
    borderTopLeftRadius: 28,
    borderTopRightRadius: 28,
    maxHeight: '85%',
    minHeight: '50%',
    paddingHorizontal: 22,
    paddingTop: 10,
    overflow: 'hidden',
  },
  accent: { alignSelf: 'center', width: 44, height: 5, borderRadius: 3, marginBottom: 16 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' },
  subject: { color: colors.text, fontSize: 20, fontWeight: '800', flex: 1, marginRight: 12 },
  close: {
    width: 34,
    height: 34,
    borderRadius: 17,
    backgroundColor: 'rgba(255,255,255,0.1)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  closeText: { color: colors.text, fontSize: 14 },
  from: { fontSize: 13, fontWeight: '600', marginTop: 6, marginBottom: 16 },
  bodyScroll: { flexGrow: 0 },
  body: { color: colors.textDim, fontSize: 15, lineHeight: 23 },
  loading: { paddingVertical: 60 },
});
