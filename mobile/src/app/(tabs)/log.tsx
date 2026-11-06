import { useEffect, useState, type ReactNode } from "react";
import { TextInput, View } from "react-native";

import { api, type LogEntry } from "../../api";
import { Body, Button, Card, ErrorNote, Eyebrow, friendlyError, Heading, Screen, styles, Title, usePhaseTheme } from "../../components/ui";
import { CATEGORIES } from "../../copy";
import { dictation } from "../../speech/dictation";
import { useUser } from "../../session";

export default function Log(): ReactNode {
  const user = useUser();
  const theme = usePhaseTheme();
  const [draft, setDraft] = useState("");
  const [entries, setEntries] = useState<LogEntry[]>([]);
  const [usedAi, setUsedAi] = useState(false);
  const [listening, setListening] = useState(false);
  const [canDictate, setCanDictate] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    dictation.isAvailable().then(setCanDictate).catch(() => setCanDictate(false));
  }, []);

  const toggleMic = async (): Promise<void> => {
    if (listening) {
      await dictation.stop();
      setListening(false);
      return;
    }
    setListening(true);
    await dictation.start(setDraft);
  };

  const sort = async (): Promise<void> => {
    setBusy(true);
    setError(null);
    try {
      const result = await api.logVoice(user.id, draft.trim());
      setEntries((current) => [...result.entries, ...current]);
      setUsedAi(result.used_ai);
      setDraft("");
    } catch (cause) {
      setError(friendlyError(cause));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Screen>
      <Heading eyebrow="Log composer" title="Say it all at once." sub="Ramble about your day. We'll sort it into sleep, movement, food, mood, and symptoms." />
      <Card>
        {canDictate ? <Button kind="soft" label={listening ? "Listening. Tap to stop." : "Tap to talk"} onPress={toggleMic} /> : null}
        <TextInput
          multiline
          value={draft}
          onChangeText={setDraft}
          placeholder="Slept badly, had oatmeal and a latte, walked 20 minutes, headache after lunch..."
          placeholderTextColor={theme.muted}
          style={[styles.input, { minHeight: 120, textAlignVertical: "top", borderColor: theme.line, backgroundColor: theme.surface, color: theme.ink }]}
        />
        <ErrorNote error={error} />
        <Button label={busy ? "Sorting..." : "Sort my log"} busy={busy} disabled={!draft.trim()} onPress={sort} />
      </Card>
      {entries.length ? (
        <Card>
          <View style={[styles.row, { justifyContent: "space-between" }]}>
            <Title>Added to your record</Title>
            <Eyebrow>{usedAi ? "Sorted by Claude" : "Sorted by Bloom"}</Eyebrow>
          </View>
          {entries.map((entry) => {
            const category = CATEGORIES[entry.category];
            return (
              <View key={entry.id} style={{ gap: 2 }}>
                <Eyebrow color={category.tone === "warn" ? theme.warn : theme.phase[category.tone]}>{category.label}</Eyebrow>
                <Body>{entry.text}</Body>
                {entry.detail ? <Body muted style={{ fontSize: 13 }}>{entry.detail}</Body> : null}
              </View>
            );
          })}
        </Card>
      ) : (
        <Body muted>Nothing logged yet today. Your first voice note will show up here, sorted.</Body>
      )}
    </Screen>
  );
}
