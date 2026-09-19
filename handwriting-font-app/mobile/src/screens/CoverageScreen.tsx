import React, { useCallback, useState } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { getAllSamples } from '../lib/storage';
import { LEAD_JAMO, VOWEL_JAMO, TRAIL_JAMO, isHangulSyllable, isCompatJamo } from '../lib/hangul';

function Bar({ label, captured, total }: { label: string; captured: number; total: number }) {
  const pct = total === 0 ? 0 : Math.round((captured / total) * 100);
  return (
    <View style={styles.barRow}>
      <Text style={styles.barLabel}>{label}</Text>
      <View style={styles.barTrack}>
        <View style={[styles.barFill, { width: `${pct}%` }]} />
      </View>
      <Text style={styles.barCount}>{captured}/{total}</Text>
    </View>
  );
}

export default function CoverageScreen() {
  const [chars, setChars] = useState<string[]>([]);

  useFocusEffect(
    useCallback(() => {
      getAllSamples().then((all) => setChars(Object.keys(all)));
    }, [])
  );

  const leadsCaptured = LEAD_JAMO.filter((j) => chars.includes(j)).length;
  const vowelsCaptured = VOWEL_JAMO.filter((j) => chars.includes(j)).length;
  const trailsCaptured = TRAIL_JAMO.filter((j) => chars.includes(j)).length;
  const syllablesDirect = chars.filter((c) => isHangulSyllable(c)).length;
  const estimatedSynthesizable = leadsCaptured * vowelsCaptured * (1 + trailsCaptured);
  const otherChars = chars.filter((c) => !isCompatJamo(c) && !isHangulSyllable(c));

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.sectionTitle}>한글 자모 커버리지</Text>
      <Bar label="초성" captured={leadsCaptured} total={LEAD_JAMO.length} />
      <Bar label="중성(모음)" captured={vowelsCaptured} total={VOWEL_JAMO.length} />
      <Bar label="종성" captured={trailsCaptured} total={TRAIL_JAMO.length} />

      <View style={styles.summaryCard}>
        <Text style={styles.summaryNumber}>{syllablesDirect}</Text>
        <Text style={styles.summaryLabel}>직접 쓴 완성 글자</Text>
      </View>
      <View style={styles.summaryCard}>
        <Text style={styles.summaryNumber}>~{estimatedSynthesizable}</Text>
        <Text style={styles.summaryLabel}>자모 조합으로 자동 생성 가능한 글자 수 (추정)</Text>
      </View>

      {otherChars.length > 0 && (
        <>
          <Text style={styles.sectionTitle}>기타 문자 ({otherChars.length}자)</Text>
          <Text style={styles.otherChars}>{otherChars.join(' ')}</Text>
        </>
      )}

      <Text style={styles.tip}>
        초성·중성·종성을 다양하게 쓸수록(예: "ㅋㅋㅋ", "ㅠㅠ" 같은 평소 표현도 포함) 안 써본 글자도 자동으로 조합돼요.
      </Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fafafa' },
  content: { padding: 20 },
  sectionTitle: { fontSize: 16, fontWeight: '700', marginTop: 16, marginBottom: 10 },
  barRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 10 },
  barLabel: { width: 72, color: '#555' },
  barTrack: { flex: 1, height: 10, backgroundColor: '#eee', borderRadius: 5, overflow: 'hidden', marginHorizontal: 8 },
  barFill: { height: '100%', backgroundColor: '#4c8bf5' },
  barCount: { width: 48, textAlign: 'right', color: '#888', fontSize: 12 },
  summaryCard: { backgroundColor: '#fff', borderRadius: 12, borderWidth: 1, borderColor: '#eee', padding: 16, alignItems: 'center', marginTop: 12 },
  summaryNumber: { fontSize: 28, fontWeight: '800', color: '#4c8bf5' },
  summaryLabel: { color: '#888', marginTop: 4, textAlign: 'center' },
  otherChars: { fontSize: 18, lineHeight: 28 },
  tip: { marginTop: 24, color: '#999', fontSize: 13, lineHeight: 20 },
});
