// Short, everyday sentences to copy in your own handwriting. Rotating through
// these over a few sessions naturally covers most common jamo/characters
// without ever asking the user to fill in a rigid "grid of every letter".
export const DAILY_PROMPTS = [
  '오늘 점심 뭐 먹었어?',
  '내일 날씨 진짜 좋대ㅋㅋ',
  '이따 저녁에 만날까?',
  '오늘 하루도 고생했어',
  '주말에 뭐 할 계획이야?',
  '이거 진짜 맛있다!',
  '조금만 더 힘내자',
  '너무 졸려서 눈이 감겨ㅠㅠ',
  '커피 한 잔 하러 갈래?',
  '오랜만이야, 잘 지냈어?',
  '이번 주는 정말 바빴다',
  '비 오는 날엔 파전이지',
  '생일 축하해!! 행복한 하루 보내',
  '숙제 다 했어? 나는 아직...',
  '집에 가는 길에 편의점 들를게',
  '요즘 재밌는 드라마 있어?',
  '늦어서 미안, 금방 갈게',
  '오늘도 화이팅입니다',
  '심심한데 영화나 볼까',
  'Hello! Nice to meet you 123',
];

export function promptForIndex(index: number): string {
  return DAILY_PROMPTS[((index % DAILY_PROMPTS.length) + DAILY_PROMPTS.length) % DAILY_PROMPTS.length];
}
