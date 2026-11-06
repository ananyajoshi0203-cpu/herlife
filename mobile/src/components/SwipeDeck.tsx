import type { ReactNode } from "react";
import { useWindowDimensions, View } from "react-native";
import { GestureDetector, usePanGesture } from "react-native-gesture-handler";
import Animated, { interpolate, useAnimatedStyle, useSharedValue, withSpring, withTiming } from "react-native-reanimated";
import { scheduleOnRN } from "react-native-worklets";

import type { Habit } from "../api";
import { Body, Button, Card, Eyebrow, styles, Title, usePhaseTheme } from "./ui";

export type SwipeDirection = "right" | "left";

const SWIPE_THRESHOLD = 90;
const VISIBLE_CARDS = 3;

/** Right is done, left is not today. The buttons below do the same thing for anyone who cannot swipe. */
export function SwipeDeck({ habits, onResolve }: { habits: Habit[]; onResolve: (habit: Habit, direction: SwipeDirection) => void }): ReactNode {
  const [top, ...rest] = habits;
  if (!top) {
    return (
      <Card>
        <Title level="h3">You're checked in for today</Title>
        <Body muted>Swipe again tomorrow morning.</Body>
      </Card>
    );
  }
  return (
    <View style={{ gap: 14 }}>
      <View style={{ height: 190 }}>
        {rest
          .slice(0, VISIBLE_CARDS - 1)
          .reverse()
          .map((habit, index, behind) => (
            <StackedCard key={habit.id} habit={habit} depth={behind.length - index} />
          ))}
        <TopCard key={top.id} habit={top} onResolve={(direction) => onResolve(top, direction)} />
      </View>
      <View style={[styles.row, { justifyContent: "center", gap: 14 }]}>
        <Button kind="ghost" label="Not today" onPress={() => onResolve(top, "left")} />
        <Button label="Done" onPress={() => onResolve(top, "right")} />
      </View>
      <Body muted style={{ textAlign: "center", fontSize: 12 }}>
        Swipe right for done, left for not today
      </Body>
    </View>
  );
}

function HabitFace({ habit }: { habit: Habit }): ReactNode {
  const theme = usePhaseTheme();
  return (
    <Card style={{ height: 180 }}>
      <Eyebrow color={theme.accent}>{habit.goal}</Eyebrow>
      <Title>{habit.title}</Title>
      <Body muted>{habit.why}</Body>
    </Card>
  );
}

function StackedCard({ habit, depth }: { habit: Habit; depth: number }): ReactNode {
  return (
    <View
      pointerEvents="none"
      style={{ position: "absolute", left: 0, right: 0, transform: [{ translateY: depth * 8 }, { scale: 1 - depth * 0.04 }], opacity: 1 - depth * 0.25 }}
    >
      <HabitFace habit={habit} />
    </View>
  );
}

function TopCard({ habit, onResolve }: { habit: Habit; onResolve: (direction: SwipeDirection) => void }): ReactNode {
  const { width } = useWindowDimensions();
  const translateX = useSharedValue(0);

  const pan = usePanGesture({
    activeOffsetX: [-12, 12],
    onUpdate: (event) => {
      "worklet";
      translateX.value = event.translationX;
    },
    onDeactivate: (event) => {
      "worklet";
      if (Math.abs(event.translationX) < SWIPE_THRESHOLD) {
        translateX.value = withSpring(0);
        return;
      }
      const direction: SwipeDirection = event.translationX > 0 ? "right" : "left";
      translateX.value = withTiming(Math.sign(event.translationX) * width * 1.4, { duration: 220 }, (finished) => {
        if (finished) scheduleOnRN(onResolve, direction);
      });
    },
  });

  const animated = useAnimatedStyle(() => ({
    transform: [{ translateX: translateX.value }, { rotate: `${interpolate(translateX.value, [-width, width], [-14, 14])}deg` }],
  }));

  return (
    <GestureDetector gesture={pan}>
      <Animated.View
        accessible
        accessibilityLabel={`${habit.title}. Swipe right for done, left for not today.`}
        style={[{ position: "absolute", left: 0, right: 0 }, animated]}
      >
        <HabitFace habit={habit} />
      </Animated.View>
    </GestureDetector>
  );
}
