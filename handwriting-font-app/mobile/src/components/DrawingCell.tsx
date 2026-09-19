import React, { useMemo, useRef, useState } from 'react';
import { GestureResponderEvent, PanResponder, Pressable, StyleSheet, Text, View } from 'react-native';
import Svg, { Polyline } from 'react-native-svg';
import type { Point, Stroke } from '../lib/types';

export const CELL_SIZE = 84;

type Props = {
  label: string;
  initialStrokes?: Stroke[];
  onChangeStrokes: (strokes: Stroke[]) => void;
  hasSample?: boolean;
};

export default function DrawingCell({ label, initialStrokes, onChangeStrokes, hasSample }: Props) {
  const [strokes, setStrokes] = useState<Stroke[]>(initialStrokes ?? []);
  const [current, setCurrent] = useState<Point[] | null>(null);
  const strokesRef = useRef(strokes);
  strokesRef.current = strokes;
  const currentRef = useRef<Point[] | null>(null);

  const panResponder = useMemo(
    () =>
      PanResponder.create({
        onStartShouldSetPanResponder: () => true,
        onMoveShouldSetPanResponder: () => true,
        onPanResponderGrant: (e: GestureResponderEvent) => {
          const { locationX, locationY } = e.nativeEvent;
          currentRef.current = [{ x: locationX, y: locationY }];
          setCurrent(currentRef.current);
        },
        onPanResponderMove: (e: GestureResponderEvent) => {
          const { locationX, locationY } = e.nativeEvent;
          currentRef.current = [...(currentRef.current ?? []), { x: locationX, y: locationY }];
          setCurrent(currentRef.current);
        },
        onPanResponderRelease: () => {
          const finished = currentRef.current;
          currentRef.current = null;
          setCurrent(null);
          if (finished && finished.length > 0) {
            const next = [...strokesRef.current, finished];
            setStrokes(next);
            onChangeStrokes(next);
          }
        },
      }),
    [onChangeStrokes]
  );

  const clear = () => {
    currentRef.current = null;
    setStrokes([]);
    setCurrent(null);
    onChangeStrokes([]);
  };

  const toPointsAttr = (stroke: Point[]) => stroke.map((p) => `${p.x},${p.y}`).join(' ');

  return (
    <View style={styles.wrap}>
      <View style={[styles.cell, hasSample && styles.cellFilled]} {...panResponder.panHandlers}>
        {strokes.length === 0 && !current && (
          <Text style={[styles.guide, { pointerEvents: 'none' }]}>{label}</Text>
        )}
        <Svg width={CELL_SIZE} height={CELL_SIZE}>
          {strokes.map((s, i) => (
            <Polyline key={i} points={toPointsAttr(s)} stroke="#1a1a1a" strokeWidth={4} fill="none" strokeLinecap="round" strokeLinejoin="round" />
          ))}
          {current && <Polyline points={toPointsAttr(current)} stroke="#1a1a1a" strokeWidth={4} fill="none" strokeLinecap="round" strokeLinejoin="round" />}
        </Svg>
        {strokes.length > 0 && (
          <Pressable style={styles.clearBtn} onPress={clear} hitSlop={8}>
            <Text style={styles.clearBtnText}>×</Text>
          </Pressable>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { alignItems: 'center', margin: 4 },
  cell: {
    width: CELL_SIZE,
    height: CELL_SIZE,
    borderWidth: 1,
    borderColor: '#ccc',
    borderRadius: 8,
    backgroundColor: '#fff',
    overflow: 'hidden',
  },
  cellFilled: { borderColor: '#4c8bf5', borderWidth: 1.5 },
  guide: {
    position: 'absolute',
    width: CELL_SIZE,
    height: CELL_SIZE,
    textAlign: 'center',
    textAlignVertical: 'center',
    lineHeight: CELL_SIZE,
    fontSize: CELL_SIZE * 0.55,
    color: '#e2e2e2',
  },
  clearBtn: {
    position: 'absolute',
    top: 2,
    right: 4,
    width: 18,
    height: 18,
    alignItems: 'center',
    justifyContent: 'center',
  },
  clearBtnText: { color: '#bbb', fontSize: 14, fontWeight: '600' },
});
