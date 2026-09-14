"""
햄스터봇 바퀴 방향 단순 테스트 (카메라/비전 없이 하드웨어만 확인)

지금까지 HamsterBot_Soccer.py에서 각도 계산/조향 로직을 여러 번 고쳐도
로봇이 계속 제자리에서 도는 문제가 해결되지 않았다. 이 스크립트는 카메라,
공/마커 인식, 조향 계산을 전부 빼고 robot.wheels()만 직접 호출해서,
문제가 소프트웨어 로직에 있는지 하드웨어/통신 쪽에 있는지 구분하기 위한
것이다.

사용법:
1. 로봇 전원을 켜고 PC와 연결한다 (블루투스 페어링 상태 확인).
2. 로봇을 바닥에 평평하게 놓고, 앞에서 잘 보이는 곳에 앉는다.
3. 이 스크립트를 실행한다: python wheel_test.py
4. 화면 안내에 따라 진행하면서, 로봇이 실제로 어떻게 움직이는지 눈으로 보고
   터미널에 그대로 입력한다 (예: 직진했는지, 시계/반시계 방향으로 돌았는지).

각 동작은 3초간 실행되고 자동으로 멈춘다.
"""
import time
from roboid import *


def test_robot(robot, name):
    print(f"\n===== {name} 테스트 시작 =====")
    input("로봇을 평평한 바닥에 놓고 Enter를 누르세요...")

    print(f"[{name}] 1) 직진 테스트: wheels(50, 50) - 3초간 앞으로 가야 합니다.")
    robot.wheels(50, 50)
    time.sleep(3)
    robot.wheels(0, 0)
    fwd = input("실제로 앞으로 똑바로 갔나요? (y = 그렇다 / n = 아니다, 어떻게 움직였는지 설명): ").strip()

    print(f"[{name}] 2) 회전 테스트 A: wheels(50, -50) - 3초간 제자리에서 도는지 잘 보세요.")
    robot.wheels(50, -50)
    time.sleep(3)
    robot.wheels(0, 0)
    dir_a = input("어느 방향으로 돌았나요? (시계방향 = cw / 반시계방향 = ccw / 안 돎 = none): ").strip().lower()

    print(f"[{name}] 3) 회전 테스트 B: wheels(-50, 50) - 이번엔 반대 방향으로 돌아야 정상입니다.")
    robot.wheels(-50, 50)
    time.sleep(3)
    robot.wheels(0, 0)
    dir_b = input("어느 방향으로 돌았나요? (cw / ccw / none): ").strip().lower()

    robot.stop()
    return fwd, dir_a, dir_b


if __name__ == "__main__":
    print("햄스터봇 연결 시도 중...")
    try:
        h1 = Hamster(0)
        print("로봇 1 (H1, ID0) 연결 성공")
    except Exception as e:
        h1 = None
        print("로봇 1 (H1, ID0) 연결 실패:", e)

    try:
        h2 = Hamster(1)
        print("로봇 2 (H2, ID1) 연결 성공")
    except Exception as e:
        h2 = None
        print("로봇 2 (H2, ID1) 연결 실패:", e)

    results = {}
    if h1:
        results["R1 (H1)"] = test_robot(h1, "로봇 1 (H1)")
    if h2:
        results["R2 (H2)"] = test_robot(h2, "로봇 2 (H2)")

    print("\n===== 결과 요약 =====")
    for name, (fwd, dir_a, dir_b) in results.items():
        print(f"{name}: 직진={fwd} / wheels(+50,-50)->{dir_a} / wheels(-50,+50)->{dir_b}")

    print("\n[판단 기준]")
    print("- 직진 테스트에서 옆으로 크게 휘거나 제자리에서 돌았다면: 배선/모터 자체의 하드웨어 문제일 가능성이 큽니다.")
    print("- 두 회전 테스트(A, B) 결과가 서로 반대 방향(cw/ccw)이 아니라 같은 방향이거나 안 돌았다면: 통신/명령 전달 문제일 가능성이 큽니다.")
    print("- 두 회전 테스트가 서로 반대 방향으로 '정상적으로' 잘 돈다면: 하드웨어는 정상이고, 원래 앱의 각도 계산(카메라로 본 로봇 방향)이 실제와 다르게 잡히고 있다는 뜻이니 그쪽을 다시 봐야 합니다.")

    if h1: h1.stop()
    if h2: h2.stop()
