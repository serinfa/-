export type Point = { x: number; y: number };
export type Stroke = Point[];

export type StoredSample = {
  char: string;
  strokes: Stroke[];
  cellSize: number;
  sampleCount: number;
  updatedAt: string;
};
