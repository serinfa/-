#include <Servo.h>

// [수정 금지] CNC Shield V3 하드웨어 핀 배열
const int stepX = 2; const int dirX = 5;
const int stepY = 3; const int dirY = 6;
const int stepZ = 4; const int dirZ = 7;
const int enPin = 8;

// [수정 금지] 4방향 리미트 스위치 핀
const int limitX_Home = 9;   // X- 방향 리미트
const int limitY_Home = 10;  // Y- 방향 리미트
const int limitX_Max  = A0;  // X+ 방향 리미트
const int limitY_Max  = A1;  // Y+ 방향 리미트

Servo gripperServo;
const int servoPin = 11;

String inputString = "";
const int moveSteps = 80;

#define SWITCH_PRESSED LOW
#define SWITCH_RELEASED HIGH

void setup() {
  Serial.begin(115200);

  pinMode(stepX, OUTPUT); pinMode(dirX, OUTPUT);
  pinMode(stepY, OUTPUT); pinMode(dirY, OUTPUT);
  pinMode(stepZ, OUTPUT); pinMode(dirZ, OUTPUT);
  pinMode(enPin, OUTPUT);

  // 리미트 스위치 4개 모두 내부 풀업 설정
  pinMode(limitX_Home, INPUT_PULLUP);
  pinMode(limitY_Home, INPUT_PULLUP);
  pinMode(limitX_Max,  INPUT_PULLUP);
  pinMode(limitY_Max,  INPUT_PULLUP);

  digitalWrite(enPin, LOW); // 모터 드라이버 활성화

  gripperServo.attach(servoPin);
  gripperServo.write(180);  // 초기에 집게 열기

  inputString.reserve(200);
  Serial.println("Arduino Candy Crane Ready!");
}

void loop() {
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    if (inChar == '\n') {
      inputString.trim();
      if (inputString.length() > 0) {
        processCommand(inputString);
        inputString = "";
      }
    } else {
      inputString += inChar;
    }
  }
}

// 명령어 처리 함수
void processCommand(String cmd) {
  // 1. X+ 이동 (기존 HIGH, HIGH에서 LOW, LOW로 반전)
  if (cmd == "X+") {
    stepDualMotorSafe(LOW, LOW, moveSteps, limitX_Max);
  } 
  // 2. X- 이동 (기존 LOW, LOW에서 HIGH, HIGH로 반전)
  else if (cmd == "X-") {
    stepDualMotorSafe(HIGH, HIGH, moveSteps, limitX_Home);
  } 
  // 3. Y+ 이동 (X: 반시계방향 LOW, Y: 시계방향 HIGH)
  else if (cmd == "Y+") {
    stepDualMotorSafe(LOW, HIGH, moveSteps, limitY_Max);
  } 
  // 4. Y- 이동 (X: 시계방향 HIGH, Y: 반시계방향 LOW)
  else if (cmd == "Y-") {
    stepDualMotorSafe(HIGH, LOW, moveSteps, limitY_Home);
  }
  
  // Z축 이동
  else if (cmd == "Z+") stepMotorZ(dirZ, stepZ, HIGH, moveSteps * 2);
  else if (cmd == "Z-") stepMotorZ(dirZ, stepZ, LOW, moveSteps * 2);
  
  // 서보 모터(집게) 제어
  else if (cmd.startsWith("G:")) {
    int angle = cmd.substring(2).toInt();
    angle = constrain(angle, 0, 180);
    delay(200); 
    gripperServo.write(angle);
    delay(300); 
  }
  
  // 4방향 리미트 스위치를 활용한 원점 복귀
  else if (cmd == "HOME") {
    executeHoming();
  }
}

// [CoreXY 두 모터 동시 안전 구동]
void stepDualMotorSafe(boolean dirX_val, boolean dirY_val, int steps, int limitPin) {
  digitalWrite(dirX, dirX_val);
  digitalWrite(dirY, dirY_val);
  
  for (int i = 0; i < steps; i++) {
    // 이동 중 해당 방향 리미트 스위치가 눌리면 즉시 중단 (대기 상태 전환)
    if (digitalRead(limitPin) == SWITCH_PRESSED) {
      break; 
    }
    digitalWrite(stepX, HIGH);
    digitalWrite(stepY, HIGH);
    delayMicroseconds(800);
    digitalWrite(stepX, LOW);
    digitalWrite(stepY, LOW);
    delayMicroseconds(800);
  }
}

// Z축 독립 구동 함수
void stepMotorZ(int dirPin, int stepPin, boolean dir, int steps) {
  digitalWrite(dirPin, dir);
  for (int i = 0; i < steps; i++) {
    digitalWrite(stepPin, HIGH);
    delayMicroseconds(1500);
    digitalWrite(stepPin, LOW);
    delayMicroseconds(1500);
  }
}

// [CoreXY 및 4방향 리미트 스위치 기반 원점 복귀(Homing) 함수]
void executeHoming() {
  // Step 1. Y축 원점 복귀 (Y- 방향: X=HIGH, Y=LOW)
  digitalWrite(dirX, HIGH);
  digitalWrite(dirY, LOW);
  int timeoutY = 0;
  while (digitalRead(limitY_Home) == SWITCH_RELEASED && timeoutY < 10000) {
    digitalWrite(stepX, HIGH);
    digitalWrite(stepY, HIGH);
    delayMicroseconds(800);
    digitalWrite(stepX, LOW);
    digitalWrite(stepY, LOW);
    delayMicroseconds(800);
    timeoutY++;
  }
  
  // Y축 스위치 텐션 해제 (Y+ 방향으로 미세 이동하여 스위치 떨어뜨리기)
  digitalWrite(dirX, LOW);
  digitalWrite(dirY, HIGH);
  for (int i = 0; i < 35; i++) {
    digitalWrite(stepX, HIGH);
    digitalWrite(stepY, HIGH);
    delayMicroseconds(800);
    digitalWrite(stepX, LOW);
    digitalWrite(stepY, LOW);
    delayMicroseconds(800);
  }
  delay(500);

  // Step 2. X축 원점 복귀 (X- 방향이 HIGH, HIGH로 변경되었으므로 이에 맞춤)
  digitalWrite(dirX, HIGH);
  digitalWrite(dirY, HIGH);
  int timeoutX = 0;
  while (digitalRead(limitX_Home) == SWITCH_RELEASED && timeoutX < 10000) {
    digitalWrite(stepX, HIGH);
    digitalWrite(stepY, HIGH);
    delayMicroseconds(800);
    digitalWrite(stepX, LOW);
    digitalWrite(stepY, LOW);
    delayMicroseconds(800);
    timeoutX++;
  }
  
  // X축 스위치 텐션 해제 (X+ 방향인 LOW, LOW로 미세 이동하여 스위치 떨어뜨리기)
  digitalWrite(dirX, LOW);
  digitalWrite(dirY, LOW);
  for (int i = 0; i < 35; i++) {
    digitalWrite(stepX, HIGH);
    digitalWrite(stepY, HIGH);
    delayMicroseconds(800);
    digitalWrite(stepX, LOW);
    digitalWrite(stepY, LOW);
    delayMicroseconds(800);
  }
  
  delay(500);
  gripperServo.write(180); // 집게 열기
  delay(500);
}