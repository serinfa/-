#include <Servo.h>

Servo gripper;

// =====================================================================
// 1. CNC Shield V3 핀 번호 설정
// =====================================================================
const int X_STEP = 2; const int X_DIR = 5;
const int Y_STEP = 3; const int Y_DIR = 6;
const int Z_STEP = 4; const int Z_DIR = 7;
const int ENABLE_PIN = 8;

// 4방향 독립 스위치 맵핑
const int X_RIGHT_LIMIT = 9;
const int X_LEFT_LIMIT = A0;
const int Y_FWD_LIMIT = 10;
const int Y_BWD_LIMIT = A1;

const int SERVO_PIN = 11;

void setup() {
  Serial.begin(115200);

  pinMode(X_STEP, OUTPUT); pinMode(X_DIR, OUTPUT);
  pinMode(Y_STEP, OUTPUT); pinMode(Y_DIR, OUTPUT);
  pinMode(Z_STEP, OUTPUT); pinMode(Z_DIR, OUTPUT);
  pinMode(ENABLE_PIN, OUTPUT);

  pinMode(X_RIGHT_LIMIT, INPUT_PULLUP);
  pinMode(X_LEFT_LIMIT, INPUT_PULLUP);
  pinMode(Y_FWD_LIMIT, INPUT_PULLUP);
  pinMode(Y_BWD_LIMIT, INPUT_PULLUP);

  digitalWrite(ENABLE_PIN, LOW);

  gripper.attach(SERVO_PIN);
  gripper.write(180);
}

void loop() {
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');
    input.trim();
    if (input.length() > 0) {
      executeCommand(input);
    }
  }
}

// =====================================================================
// 2. 명령어 해독
// =====================================================================
void executeCommand(String cmd) {
  if (cmd == "STOP" || cmd == "STOP_XY") {
    return;
  }

  int firstUnder = cmd.indexOf('_');
  int secondUnder = cmd.indexOf('_', firstUnder + 1);

  String action = cmd;
  int spd = 1200;
  int bounce = 15;

  if (firstUnder > 0 && secondUnder > 0) {
    action = cmd.substring(0, firstUnder);
    spd = cmd.substring(firstUnder + 1, secondUnder).toInt();
    bounce = cmd.substring(secondUnder + 1).toInt();
  } else if (firstUnder > 0) {
    action = cmd.substring(0, firstUnder);
    spd = cmd.substring(firstUnder + 1).toInt();
  }

  // 🟢 [핵심] 수동 조작(moveCoreXY) 시에는 더 이상 bounce 값을 넘겨주지 않습니다!
  if (action == "X-")      moveCoreXY(LOW, LOW, 200, spd, X_LEFT_LIMIT);
  else if (action == "X+") moveCoreXY(HIGH, HIGH, 200, spd, X_RIGHT_LIMIT);
  else if (action == "Y-") moveCoreXY(LOW, HIGH, 200, spd, Y_BWD_LIMIT);
  else if (action == "Y+") moveCoreXY(HIGH, LOW, 200, spd, Y_FWD_LIMIT);

  else if (action == "Z+") moveMotor(Z_STEP, Z_DIR, HIGH, 400, spd);
  else if (action == "Z-") moveMotor(Z_STEP, Z_DIR, LOW, 400, spd);

  else if (action.startsWith("G:")) {
    int angle = action.substring(2).toInt();
    if (angle < 90) angle = 90;
    if (angle > 180) angle = 180;
    gripper.write(angle);
  }

  else if (action == "HOME") {
    // HOME 기능은 기계 영점을 잡아야 하므로 튕김(bounce)과 더블 터치를 그대로 사용합니다.
    homeCoreXYAxis(LOW, LOW, X_LEFT_LIMIT, spd, bounce);
    homeCoreXYAxis(LOW, HIGH, Y_BWD_LIMIT, spd, bounce);
  }
}

// =====================================================================
// 3. 단일 모터 이동 (Z축 상하)
// =====================================================================
void moveMotor(int stepPin, int dirPin, int dir, int steps, int spd) {
  digitalWrite(dirPin, dir);
  for (int i = 0; i < steps; i++) {
    digitalWrite(stepPin, HIGH);
    delayMicroseconds(spd);
    digitalWrite(stepPin, LOW);
    delayMicroseconds(spd);
  }
}

// =====================================================================
// 4. CoreXY 전용 동시 이동 함수 (수동 조작 - 튕김 제로, 즉시 정지)
// =====================================================================
void moveCoreXY(int xDir, int yDir, int steps, int spd, int targetLimitPin) {
  // 이미 스위치가 눌려있다면(LOW), 밀려있는 명령을 버리고 그 자리에서 무시(return)
  if (digitalRead(targetLimitPin) == LOW) {
    while (Serial.available() > 0) Serial.read();
    return;
  }

  digitalWrite(X_DIR, xDir);
  digitalWrite(Y_DIR, yDir);

  for (int i = 0; i < steps; i++) {
    // 이동 중에 스위치에 부딪히면 튕기지 않고 그 자리에 즉시 정지
    if (digitalRead(targetLimitPin) == LOW) {
      while (Serial.available() > 0) Serial.read();
      return;
    }

    digitalWrite(X_STEP, HIGH); digitalWrite(Y_STEP, HIGH);
    delayMicroseconds(spd);
    digitalWrite(X_STEP, LOW);  digitalWrite(Y_STEP, LOW);
    delayMicroseconds(spd);
  }
}

// =====================================================================
// 5. CoreXY 전용 원점 복귀(Homing) 함수 (더블 터치 유지)
// =====================================================================
void homeCoreXYAxis(int xDir, int yDir, int targetLimitPin, int spd, int bounceSteps) {
  int opX = (xDir == HIGH) ? LOW : HIGH;
  int opY = (yDir == HIGH) ? LOW : HIGH;
  int homeFastSpd = spd + 300;

  digitalWrite(X_DIR, xDir);
  digitalWrite(Y_DIR, yDir);
  while (digitalRead(targetLimitPin) == HIGH) {
    digitalWrite(X_STEP, HIGH); digitalWrite(Y_STEP, HIGH);
    delayMicroseconds(homeFastSpd);
    digitalWrite(X_STEP, LOW);  digitalWrite(Y_STEP, LOW);
    delayMicroseconds(homeFastSpd);
  }

  digitalWrite(X_DIR, opX);
  digitalWrite(Y_DIR, opY);
  for (int i = 0; i < 30; i++) {
    digitalWrite(X_STEP, HIGH); digitalWrite(Y_STEP, HIGH);
    delayMicroseconds(2000);
    digitalWrite(X_STEP, LOW);  digitalWrite(Y_STEP, LOW);
    delayMicroseconds(2000);
  }

  digitalWrite(X_DIR, xDir);
  digitalWrite(Y_DIR, yDir);
  while (digitalRead(targetLimitPin) == HIGH) {
    digitalWrite(X_STEP, HIGH); digitalWrite(Y_STEP, HIGH);
    delayMicroseconds(4000);
    digitalWrite(X_STEP, LOW);  digitalWrite(Y_STEP, LOW);
    delayMicroseconds(4000);
  }

  digitalWrite(X_DIR, opX);
  digitalWrite(Y_DIR, opY);
  for (int i = 0; i < bounceSteps; i++) {
    digitalWrite(X_STEP, HIGH); digitalWrite(Y_STEP, HIGH);
    delayMicroseconds(4000);
    digitalWrite(X_STEP, LOW);  digitalWrite(Y_STEP, LOW);
    delayMicroseconds(4000);
  }
}
