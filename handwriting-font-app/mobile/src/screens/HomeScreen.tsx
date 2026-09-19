import React, { useCallback, useState } from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../../App';
import { getAllSamples } from '../lib/storage';
import { promptForIndex } from '../lib/prompts';

type Props = NativeStackScreenProps<RootStackParamList, 'Home'>;

export default function HomeScreen({ navigation }: Props) {
  const [count, setCount] = useState(0);
  const [promptIndex] = useState(() => Math.floor(Date.now() / (1000 * 60 * 60 * 24)));

  useFocusEffect(
    useCallback(() => {
      getAllSamples().then((all) => setCount(Object.keys(all).length));
    }, [])
  );

  const todayPrompt = promptForIndex(promptIndex);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>내 손글씨 폰트</Text>
      <Text style={styles.subtitle}>평소 쓰던 대로, 조금씩 써서 나만의 폰트를 만들어요</Text>

      <View style={styles.statCard}>
        <Text style={styles.statNumber}>{count}</Text>
        <Text style={styles.statLabel}>지금까지 학습된 글자 수</Text>
      </View>

      <TouchableOpacity style={styles.primaryBtn} onPress={() => navigation.navigate('Write', { prompt: todayPrompt })}>
        <Text style={styles.primaryBtnText}>오늘의 한 줄 쓰기</Text>
        <Text style={styles.primaryBtnSub}>"{todayPrompt}"</Text>
      </TouchableOpacity>

      <TouchableOpacity style={styles.secondaryBtn} onPress={() => navigation.navigate('Write', { prompt: '' })}>
        <Text style={styles.secondaryBtnText}>내가 원하는 문장 직접 쓰기</Text>
      </TouchableOpacity>

      <View style={styles.row}>
        <TouchableOpacity style={styles.smallBtn} onPress={() => navigation.navigate('Coverage')}>
          <Text style={styles.smallBtnText}>진행 상황</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.smallBtn} onPress={() => navigation.navigate('Export')}>
          <Text style={styles.smallBtnText}>폰트 만들기</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fafafa', padding: 24, justifyContent: 'center' },
  title: { fontSize: 26, fontWeight: '800', textAlign: 'center' },
  subtitle: { textAlign: 'center', color: '#888', marginTop: 6, marginBottom: 28 },
  statCard: { alignItems: 'center', backgroundColor: '#fff', borderRadius: 14, paddingVertical: 20, marginBottom: 28, borderWidth: 1, borderColor: '#eee' },
  statNumber: { fontSize: 36, fontWeight: '800', color: '#4c8bf5' },
  statLabel: { color: '#888', marginTop: 4 },
  primaryBtn: { backgroundColor: '#4c8bf5', borderRadius: 14, paddingVertical: 18, alignItems: 'center', marginBottom: 12 },
  primaryBtnText: { color: '#fff', fontWeight: '700', fontSize: 17 },
  primaryBtnSub: { color: '#e6edff', marginTop: 4, fontSize: 13 },
  secondaryBtn: { borderWidth: 1, borderColor: '#4c8bf5', borderRadius: 14, paddingVertical: 16, alignItems: 'center', marginBottom: 20 },
  secondaryBtnText: { color: '#4c8bf5', fontWeight: '600' },
  row: { flexDirection: 'row', justifyContent: 'space-between' },
  smallBtn: { flex: 1, marginHorizontal: 4, paddingVertical: 12, borderRadius: 10, backgroundColor: '#eef2ff', alignItems: 'center' },
  smallBtnText: { color: '#444', fontWeight: '600' },
});
