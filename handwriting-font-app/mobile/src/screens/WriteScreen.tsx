import React, { useCallback, useMemo, useState } from 'react';
import { Alert, ScrollView, StyleSheet, Text, TextInput, TouchableOpacity, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import DrawingCell, { CELL_SIZE } from '../components/DrawingCell';
import { saveSample } from '../lib/storage';
import type { RootStackParamList } from '../../App';
import type { Stroke } from '../lib/types';

type Props = NativeStackScreenProps<RootStackParamList, 'Write'>;

function splitToChars(text: string): string[] {
  // Split on grapheme boundaries well enough for Hangul + Latin + digits,
  // and drop plain whitespace (spaces aren't glyphs worth capturing).
  return Array.from(text).filter((c) => c.trim().length > 0);
}

export default function WriteScreen({ route, navigation }: Props) {
  const initialPrompt = route.params?.prompt ?? '';
  const [promptText, setPromptText] = useState(initialPrompt);
  const [editingPrompt, setEditingPrompt] = useState(initialPrompt.length === 0);
  const chars = useMemo(() => splitToChars(promptText), [promptText]);
  const [cellStrokes, setCellStrokes] = useState<Record<number, Stroke[]>>({});

  const handleChange = useCallback((index: number, strokes: Stroke[]) => {
    setCellStrokes((prev) => ({ ...prev, [index]: strokes }));
  }, []);

  const written = Object.values(cellStrokes).filter((s) => s.length > 0).length;

  const save = async () => {
    const entries = chars
      .map((char, i) => ({ char, strokes: cellStrokes[i] }))
      .filter((e) => e.strokes && e.strokes.length > 0);
    if (entries.length === 0) {
      Alert.alert('아직 쓴 글자가 없어요', '적어도 한 글자는 써 주세요.');
      return;
    }
    for (const e of entries) {
      await saveSample(e.char, e.strokes as Stroke[], CELL_SIZE);
    }
    Alert.alert('저장 완료', `${entries.length}글자를 학습 데이터에 저장했어요.`, [
      { text: '확인', onPress: () => navigation.goBack() },
    ]);
  };

  if (editingPrompt) {
    return (
      <View style={styles.center}>
        <Text style={styles.title}>오늘은 어떤 문장을 쓸까요?</Text>
        <TextInput
          style={styles.input}
          placeholder="평소처럼 아무 문장이나 입력하세요"
          value={promptText}
          onChangeText={setPromptText}
          multiline
          autoFocus
        />
        <TouchableOpacity
          style={[styles.primaryBtn, promptText.trim().length === 0 && styles.btnDisabled]}
          disabled={promptText.trim().length === 0}
          onPress={() => setEditingPrompt(false)}
        >
          <Text style={styles.primaryBtnText}>이 문장 쓰기 시작</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.promptLabel}>이 문장을 손글씨로 따라 써 보세요</Text>
      <Text style={styles.promptText}>{promptText}</Text>
      <ScrollView contentContainerStyle={styles.grid}>
        {chars.map((char, i) => (
          <DrawingCell
            key={`${char}-${i}`}
            label={char}
            hasSample={(cellStrokes[i]?.length ?? 0) > 0}
            onChangeStrokes={(strokes) => handleChange(i, strokes)}
          />
        ))}
      </ScrollView>
      <View style={styles.footer}>
        <Text style={styles.progressText}>{written} / {chars.length}자 작성됨</Text>
        <TouchableOpacity style={styles.primaryBtn} onPress={save}>
          <Text style={styles.primaryBtnText}>저장하기</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fafafa', paddingTop: 12 },
  center: { flex: 1, justifyContent: 'center', padding: 24, backgroundColor: '#fafafa' },
  title: { fontSize: 18, fontWeight: '600', marginBottom: 16, textAlign: 'center' },
  input: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 10,
    padding: 14,
    minHeight: 80,
    fontSize: 16,
    backgroundColor: '#fff',
    textAlignVertical: 'top',
  },
  promptLabel: { textAlign: 'center', color: '#888', fontSize: 13, marginBottom: 4 },
  promptText: { textAlign: 'center', fontSize: 20, fontWeight: '600', marginBottom: 12, paddingHorizontal: 16 },
  grid: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'center', paddingHorizontal: 8, paddingBottom: 100 },
  footer: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    padding: 16,
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderTopColor: '#eee',
    alignItems: 'center',
  },
  progressText: { marginBottom: 8, color: '#666' },
  primaryBtn: { backgroundColor: '#4c8bf5', paddingVertical: 14, paddingHorizontal: 28, borderRadius: 10 },
  btnDisabled: { opacity: 0.4 },
  primaryBtnText: { color: '#fff', fontWeight: '700', fontSize: 16 },
});
