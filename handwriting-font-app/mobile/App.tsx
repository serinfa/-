import React from 'react';
import { StatusBar } from 'expo-status-bar';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import HomeScreen from './src/screens/HomeScreen';
import WriteScreen from './src/screens/WriteScreen';
import CoverageScreen from './src/screens/CoverageScreen';
import ExportScreen from './src/screens/ExportScreen';

export type RootStackParamList = {
  Home: undefined;
  Write: { prompt: string };
  Coverage: undefined;
  Export: undefined;
};

const Stack = createNativeStackNavigator<RootStackParamList>();

export default function App() {
  return (
    <NavigationContainer>
      <StatusBar style="auto" />
      <Stack.Navigator screenOptions={{ headerTitleAlign: 'center' }}>
        <Stack.Screen name="Home" component={HomeScreen} options={{ title: '내 손글씨 폰트' }} />
        <Stack.Screen name="Write" component={WriteScreen} options={{ title: '손글씨 쓰기' }} />
        <Stack.Screen name="Coverage" component={CoverageScreen} options={{ title: '진행 상황' }} />
        <Stack.Screen name="Export" component={ExportScreen} options={{ title: '폰트 만들기' }} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
