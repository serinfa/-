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
// 2. 명령어 해독 (속도와 튕김 거리 분리)
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

  if (action == "X-")      moveCoreXY(LOW, LOW, 200, spd, X_LEFT_LIMIT, bounce);
  else if (action == "X+") moveCoreXY(HIGH, HIGH, 200, spd, X_RIGHT_LIMIT, bounce);
  else if (action == "Y-") moveCoreXY(LOW, HIGH, 200, spd, Y_BWD_LIMIT, bounce);
  else if (action == "Y+") moveCoreXY(HIGH, LOW, 200, spd, Y_FWD_LIMIT, bounce);

  else if (action == "Z+") moveMotor(Z_STEP, Z_DIR, HIGH, 400, spd);
  else if (action == "Z-") moveMotor(Z_STEP, Z_DIR, LOW, 400, spd);

  else if (action.startsWith("G:")) {
    int angle = action.substring(2).toInt();
    if (angle < 90) angle = 90;
    if (angle > 180) angle = 180;
    gripper.write(angle);
  }

  else if (action == "HOME") {
    homeCoreXYAxis(LOW, LOW, X_LEFT_LIMIT, spd, bounce);
    homeCoreXYAxis(LOW, HIGH, Y_BWD_LIMIT, spd, bounce);
  }
}

// =====================================================================
// 3. 단일 모터 이동
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
// 4. CoreXY 전용 동시 이동 함수 (선생님 아이디어 적용: 스턴 딜레이!)
// =====================================================================
void moveCoreXY(int xDir, int yDir, int steps, int spd, int targetLimitPin, int bounceSteps) {
  digitalWrite(X_DIR, xDir);
  digitalWrite(Y_DIR, yDir);

  for (int i = 0; i < steps; i++) {
    if (digitalRead(targetLimitPin) == LOW) {

      int opX = (xDir == HIGH) ? LOW : HIGH;
      int opY = (yDir == HIGH) ? LOW : HIGH;
      digitalWrite(X_DIR, opX);
      digitalWrite(Y_DIR, opY);

      // 1. 스위치에서 확실히 떨어지도록, 설정된 튕김 거리보다 훨씬 크게 물러납니다.
      // (튕김 거리가 작으면 스위치 바로 앞에서 다시 눌려 계속 덜덜거리는 것처럼 보인다)
      int collisionBackoffSteps = bounceSteps * 4;
      for (int j = 0; j < collisionBackoffSteps; j++) {
        digitalWrite(X_STEP, HIGH); digitalWrite(Y_STEP, HIGH);
        delayMicroseconds(2000);
        digitalWrite(X_STEP, LOW);  digitalWrite(Y_STEP, LOW);
        delayMicroseconds(2000);
      }

      // 🟢 [핵심 추가] 물러난 후 0.4초(400ms) 동안 강제로 대기합니다. (스턴 효과)
      // 이 시간 동안은 파이썬에서 날아오는 "전진" 명령이 밀려나며 무시되므로,
      // 사용자가 다른 방향키를 누를 수 있는 여유가 생깁니다.
      delay(400);

      // 🟢 [버그 수정] 위 400ms 동안 파이썬이 계속 보낸 오래된 명령들이
      // 시리얼 수신 버퍼에 그대로 쌓여있다가, delay가 끝나자마자 밀린 순서대로
      // 즉시 실행되면서 스턴 효과가 무력화되는 문제가 있었다.
      // 스턴이 끝난 시점에 버퍼에 남아있는 오래된 명령은 전부 버려서,
      // 그 이후 사용자가 "새로" 누른 키만 반영되도록 한다.
      while (Serial.available() > 0) {
        Serial.read();
      }

      break; // 이동 취소
    }

    digitalWrite(X_STEP, HIGH); digitalWrite(Y_STEP, HIGH);
    delayMicroseconds(spd);
    digitalWrite(X_STEP, LOW);  digitalWrite(Y_STEP, LOW);
    delayMicroseconds(spd);
  }
}

// =====================================================================
// 5. CoreXY 전용 원점 복귀(Homing) 함수
// =====================================================================
void homeCoreXYAxis(int xDir, int yDir, int targetLimitPin, int spd, int bounceSteps) {
  digitalWrite(X_DIR, xDir);
  digitalWrite(Y_DIR, yDir);

  int homeSpd = spd + 300;

  while (digitalRead(targetLimitPin) == HIGH) {
    digitalWrite(X_STEP, HIGH); digitalWrite(Y_STEP, HIGH);
    delayMicroseconds(homeSpd);
    digitalWrite(X_STEP, LOW);  digitalWrite(Y_STEP, LOW);
    delayMicroseconds(homeSpd);
  }

  int opX = (xDir == HIGH) ? LOW : HIGH;
  int opY = (yDir == HIGH) ? LOW : HIGH;
  digitalWrite(X_DIR, opX);
  digitalWrite(Y_DIR, opY);

  for (int i = 0; i < bounceSteps; i++) {
    digitalWrite(X_STEP, HIGH); digitalWrite(Y_STEP, HIGH);
    delayMicroseconds(2000);
    digitalWrite(X_STEP, LOW);  digitalWrite(Y_STEP, LOW);
    delayMicroseconds(2000);
  }
}
