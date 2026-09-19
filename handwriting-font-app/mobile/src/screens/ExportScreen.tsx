import React, { useEffect, useState } from 'react';
import { ActivityIndicator, Alert, ScrollView, StyleSheet, Text, TextInput, TouchableOpacity, View } from 'react-native';
import * as FileSystem from 'expo-file-system/legacy';
import * as Sharing from 'expo-sharing';
import { getAllSamples, getServerUrl, setServerUrl } from '../lib/storage';
import { buildFont, checkHealth, syncSamples } from '../lib/api';

export default function ExportScreen() {
  const [serverUrl, setServerUrlState] = useState('');
  const [familyName, setFamilyName] = useState('My Handwriting');
  const [busy, setBusy] = useState<string | null>(null);
  const [lastStats, setLastStats] = useState<any>(null);

  useEffect(() => {
    getServerUrl().then(setServerUrlState);
  }, []);

  const onChangeUrl = (url: string) => {
    setServerUrlState(url);
    setServerUrl(url).catch(() => {});
  };

  const buildAndShare = async () => {
    setBusy('연결 확인 중...');
    try {
      const ok = await checkHealth(serverUrl);
      if (!ok) {
        Alert.alert(
          '서버에 연결할 수 없어요',
          '먼저 컴퓨터에서 폰트 생성 서버(server 폴더)를 실행하고, 같은 Wi-Fi에서 그 컴퓨터의 주소를 입력해 주세요. 예: http://192.168.0.10:4000'
        );
        return;
      }

      setBusy('학습 데이터 동기화 중...');
      const samples = await getAllSamples();
      if (Object.keys(samples).length === 0) {
        Alert.alert('아직 학습된 글자가 없어요', '먼저 손글씨를 몇 글자 써 주세요.');
        return;
      }
      await syncSamples(serverUrl, samples);

      setBusy('폰트 생성 중...');
      const { base64, stats } = await buildFont(serverUrl, familyName);
      setLastStats(stats);

      const fileUri = `${FileSystem.documentDirectory}${familyName.replace(/[^a-z0-9-_]/gi, '_')}.ttf`;
      await FileSystem.writeAsStringAsync(fileUri, base64, { encoding: FileSystem.EncodingType.Base64 });

      if (await Sharing.isAvailableAsync()) {
        await Sharing.shareAsync(fileUri, { mimeType: 'font/ttf', dialogTitle: '내 손글씨 폰트 저장/공유' });
      } else {
        Alert.alert('폰트 파일 생성 완료', `저장 위치: ${fileUri}`);
      }
    } catch (err: any) {
      Alert.alert('오류가 발생했어요', String(err?.message ?? err));
    } finally {
      setBusy(null);
    }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.label}>폰트 생성 서버 주소</Text>
      <TextInput
        style={styles.input}
        value={serverUrl}
        onChangeText={onChangeUrl}
        placeholder="http://192.168.0.10:4000"
        autoCapitalize="none"
        autoCorrect={false}
      />
      <Text style={styles.hint}>
        같은 Wi-Fi에 연결된 컴퓨터에서 handwriting-font-app/server 를 실행한 뒤, 그 컴퓨터의 IP 주소와 포트(기본 4000)를 입력하세요.
      </Text>

      <Text style={[styles.label, { marginTop: 20 }]}>폰트 이름</Text>
      <TextInput style={styles.input} value={familyName} onChangeText={setFamilyName} />

      <TouchableOpacity style={styles.primaryBtn} onPress={buildAndShare} disabled={!!busy}>
        {busy ? <ActivityIndicator color="#fff" /> : <Text style={styles.primaryBtnText}>동기화하고 폰트 만들기</Text>}
      </TouchableOpacity>
      {busy && <Text style={styles.busyText}>{busy}</Text>}

      {lastStats && (
        <View style={styles.statsCard}>
          <Text style={styles.statsLine}>직접 쓴 글자: {lastStats.capturedCount}</Text>
          <Text style={styles.statsLine}>자동 합성된 글자: {lastStats.synthesizedCount}</Text>
          <Text style={styles.statsLine}>폰트에 포함된 총 글자 수: {lastStats.totalGlyphs}</Text>
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fafafa' },
  content: { padding: 20 },
  label: { fontWeight: '600', marginBottom: 6, color: '#333' },
  input: { borderWidth: 1, borderColor: '#ddd', borderRadius: 10, padding: 12, backgroundColor: '#fff', fontSize: 15 },
  hint: { color: '#999', fontSize: 12, marginTop: 6, lineHeight: 18 },
  primaryBtn: { backgroundColor: '#4c8bf5', borderRadius: 12, paddingVertical: 16, alignItems: 'center', marginTop: 28 },
  primaryBtnText: { color: '#fff', fontWeight: '700', fontSize: 16 },
  busyText: { textAlign: 'center', color: '#888', marginTop: 10 },
  statsCard: { marginTop: 24, backgroundColor: '#fff', borderRadius: 12, borderWidth: 1, borderColor: '#eee', padding: 16 },
  statsLine: { color: '#444', marginBottom: 4 },
});
