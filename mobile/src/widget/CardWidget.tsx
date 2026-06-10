import React from 'react';
import {
  FlexWidget,
  ImageWidget,
  OverlapWidget,
  TextWidget,
} from 'react-native-android-widget';

export interface WidgetCard {
  id: string;
  headline: string;
  sender: string;
  imageUrl: string | null;
  hasAudio: boolean;
}

interface Props {
  card: WidgetCard | null;
  message?: string;
  width: number;
  height: number;
}

/**
 * Home-screen widget: the latest email's illustration with a frosted glass
 * panel. Tapping it deep-links into the app (and auto-plays the narration).
 */
export function CardWidget({ card, message, width, height }: Props) {
  if (!card) {
    return (
      <FlexWidget
        clickAction="OPEN_APP"
        style={{
          width: 'match_parent',
          height: 'match_parent',
          backgroundColor: '#141927',
          borderRadius: 20,
          justifyContent: 'center',
          alignItems: 'center',
          padding: 16,
        }}
      >
        <TextWidget
          text="EmailPartner"
          style={{ fontSize: 15, color: '#e9ecf2', fontWeight: 'bold' }}
        />
        <TextWidget
          text={message ?? 'Open the app to get started'}
          style={{ fontSize: 12, color: '#98a0b3', marginTop: 6 }}
        />
      </FlexWidget>
    );
  }

  const playUri = `emailpartner://play/${card.id}`;

  return (
    <OverlapWidget style={{ width: 'match_parent', height: 'match_parent' }}>
      {card.imageUrl ? (
        <ImageWidget
          clickAction="OPEN_URI"
          clickActionData={{ uri: playUri }}
          image={card.imageUrl as `https:${string}`}
          imageWidth={width}
          imageHeight={height}
          radius={20}
        />
      ) : (
        <FlexWidget
          clickAction="OPEN_URI"
          clickActionData={{ uri: playUri }}
          style={{
            width: 'match_parent',
            height: 'match_parent',
            backgroundColor: '#1b2336',
            borderRadius: 20,
          }}
        />
      )}
      <FlexWidget
        style={{
          width: 'match_parent',
          height: 'match_parent',
          justifyContent: 'flex-end',
          padding: 10,
        }}
      >
        <FlexWidget
          clickAction="OPEN_URI"
          clickActionData={{ uri: playUri }}
          style={{
            width: 'match_parent',
            backgroundColor: '#ffffff2e',
            borderRadius: 14,
            borderWidth: 1,
            borderColor: '#ffffff55',
            paddingHorizontal: 12,
            paddingVertical: 9,
          }}
        >
          <TextWidget
            text={card.headline}
            maxLines={2}
            style={{ fontSize: 14, color: '#ffffff', fontWeight: 'bold' }}
          />
          <FlexWidget
            style={{
              flexDirection: 'row',
              justifyContent: 'space-between',
              width: 'match_parent',
              marginTop: 4,
            }}
          >
            <TextWidget
              text={card.sender}
              maxLines={1}
              style={{ fontSize: 11, color: '#e9ecf2' }}
            />
            {card.hasAudio ? (
              <TextWidget text="▶ listen" style={{ fontSize: 11, color: '#ffffff' }} />
            ) : null}
          </FlexWidget>
        </FlexWidget>
      </FlexWidget>
    </OverlapWidget>
  );
}
