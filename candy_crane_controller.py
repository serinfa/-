"""
전시회 부스용 사탕뽑기로봇 제어 프로그램 (Candy Crane Controller)

- 좌측: 웹캠 영상 + 화면 위 가상 버튼(Air Touch)
- 우측: 아두이노 연결, 상태 표시, 조작 안내, 긴급 정지

조작 방법
  화면의 가상 버튼에 검지 손가락을 올리면 로봇이 이동합니다.
  키보드로도 동일하게 조작할 수 있습니다.
    W/S : 전진/후진 (Y+/Y-)   A/D : 좌/우 (X-/X+)
    Q/E : Z축 상승/하강        SPACE : 집게 열기/닫기 토글
    H   : 원점 복귀(HOME)
"""

import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk

import cv2
import mediapipe as mp
import PIL.Image
import PIL.ImageTk
import serial
import serial.tools.list_ports

# ---------------------------------------------------------------------------
# 설정값
# ---------------------------------------------------------------------------
WINDOW_TITLE = "전시회 부스용 사탕뽑기로봇 (Virtual Button Edition)"
WINDOW_SIZE = "1024x720"
WINDOW_MIN_SIZE = (800, 550)

CAMERA_INDEX = 0
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
VIDEO_LOOP_INTERVAL_MS = 15  # 화면 갱신 주기

# 화면에는 원본 해상도(FRAME_WIDTH x FRAME_HEIGHT)를 그대로 보여주고,
# MediaPipe 손 인식에는 이 축소된 사본만 넘겨서 연산량을 줄인다.
# (랜드마크 좌표는 0~1 정규화 값이라 화질 손해 없이 원본 프레임에 그대로 매핑된다)
HAND_DETECTION_WIDTH = 320
HAND_DETECTION_HEIGHT = 240

SERIAL_BAUDRATE = 115200
SERIAL_TIMEOUT = 0.1
SERIAL_BOOT_DELAY_SEC = 2.0  # 아두이노 재부팅 대기 시간

MOVE_COOLDOWN_SEC = 0.08  # 이동 명령 과부하 방지 쿨다운
NO_COOLDOWN_COMMANDS = {"STOP", "HOME"}  # 쿨다운 없이 즉시 전송할 명령

GRIPPER_OPEN_ANGLE_DEFAULT = 180
GRIPPER_CLOSE_ANGLE_DEFAULT = 90

# 가상 버튼 방향별 키보드 매핑
KEY_TO_COMMAND = {
    "w": "Y+", "s": "Y-",
    "a": "X-", "d": "X+",
    "q": "Z+", "e": "Z-",
    "h": "HOME",
}

BUTTON_COLOR_IDLE = (255, 0, 0)
BUTTON_COLOR_ACTIVE = (0, 255, 0)
POINTER_COLOR = (0, 0, 255)


class CandyRobotApp:
    def __init__(self, root):
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.geometry(WINDOW_SIZE)
        self.root.minsize(*WINDOW_MIN_SIZE)
        try:
            self.root.attributes("-zoomed", True)
        except tk.TclError:
            pass

        # 집게 각도 설정
        self.is_gripper_closed = False

        # 하드웨어 통신 상태
        self.serial_port = None
        self.arduino_status_var = tk.StringVar(value="연결 안 됨")
        self.is_emergency_stop = False
        self._last_move_time = 0.0

        # 카메라/영상 처리 상태
        self.cap = None
        self.is_running = True
        self._latest_photo_image = None
        self._frame_lock = threading.Lock()
        self._pending_bgr_frame = None

        # MediaPipe 손 인식 (필요할 때만 초기화 실패를 잡아낸다)
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            max_num_hands=1,
            model_complexity=0,  # 라이트 모델: 라즈베리파이 같은 저사양 환경에서 인식 속도 개선
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7,
        )
        self.mp_draw = mp.solutions.drawing_utils

        self.setup_ui()
        self.bind_keys()
        self.start_camera()

        # 영상 처리는 백그라운드 스레드, 화면 갱신은 메인(Tk) 스레드에서 수행
        self.video_thread = threading.Thread(target=self.video_loop, daemon=True)
        self.video_thread.start()
        self.root.after(VIDEO_LOOP_INTERVAL_MS, self.refresh_canvas)

    # ------------------------------------------------------------------
    # UI 구성
    # ------------------------------------------------------------------
    def setup_ui(self):
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(main_frame, width=FRAME_WIDTH, height=FRAME_HEIGHT, bg="black")
        self.canvas.pack(side=tk.LEFT, padx=10, pady=10)

        control_frame = tk.Frame(main_frame)
        control_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        self._build_connection_section(control_frame)
        self._build_guide_section(control_frame)
        self._build_stop_section(control_frame)

    def _build_connection_section(self, parent):
        tk.Label(parent, text="[ 아두이노 연결 ]", font=("Arial", 14, "bold")).pack(pady=5)

        self.port_combobox = ttk.Combobox(parent, values=self._list_serial_ports())
        self.port_combobox.pack(pady=5)

        tk.Button(parent, text="포트 새로고침", command=self.refresh_ports).pack(pady=5)
        tk.Button(
            parent, text="연결하기", bg="green", fg="white", font=("Arial", 12),
            command=lambda: self.connect_arduino(self.port_combobox.get()),
        ).pack(pady=5)

        tk.Label(parent, textvariable=self.arduino_status_var, fg="blue").pack(pady=5)

    def _build_guide_section(self, parent):
        tk.Label(parent, text="[ 로봇 제어 안내 ]", font=("Arial", 14, "bold")).pack(pady=15)
        tk.Label(parent, text="화면의 가상 버튼에 검지 손가락을 올려보세요!").pack(pady=5)
        tk.Label(parent, text="< 키보드 보조 조작 >").pack(pady=5)
        tk.Label(parent, text="W/S : 전진/후진 (Y+, Y-)").pack()
        tk.Label(parent, text="A/D : 좌측/우측 (X-, X+)").pack()
        tk.Label(parent, text="Q/E : Z축 상승/하강").pack()
        tk.Label(parent, text="SPACE : 집게 열기/닫기 토글").pack()
        tk.Label(parent, text="H : 원점 복귀 (HOME)").pack()

    def _build_stop_section(self, parent):
        tk.Button(
            parent, text="긴급 정지 (STOP)", bg="red", fg="white", font=("Arial", 14, "bold"),
            command=self.emergency_stop,
        ).pack(pady=20, fill=tk.X)

    # ------------------------------------------------------------------
    # 아두이노 시리얼 통신
    # ------------------------------------------------------------------
    @staticmethod
    def _list_serial_ports():
        return [p.device for p in serial.tools.list_ports.comports()]

    def refresh_ports(self):
        ports = self._list_serial_ports()
        self.port_combobox["values"] = ports
        if ports:
            self.port_combobox.current(0)

    def connect_arduino(self, port):
        if not port:
            messagebox.showwarning("포트 선택", "연결할 COM 포트를 선택하세요.")
            return

        self.disconnect_arduino()
        try:
            self.serial_port = serial.Serial(
                port, SERIAL_BAUDRATE, timeout=SERIAL_TIMEOUT, write_timeout=SERIAL_TIMEOUT
            )
            time.sleep(SERIAL_BOOT_DELAY_SEC)
            self.arduino_status_var.set(f"연결됨: {port}")
            self.execute_hardware_cmd("HOME")  # 연결 직후 원점으로 자동 복귀
            messagebox.showinfo("연결 성공", f"아두이노가 {port}에 연결되었습니다.")
        except serial.SerialException as e:
            self.serial_port = None
            self.arduino_status_var.set("연결 실패")
            messagebox.showerror("연결 오류", f"아두이노 연결 실패:\n{e}")

    def disconnect_arduino(self):
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.close()
            except serial.SerialException:
                pass
        self.serial_port = None

    def execute_hardware_cmd(self, command_str):
        if self.is_emergency_stop:
            return

        now = time.time()
        if command_str not in NO_COOLDOWN_COMMANDS and not command_str.startswith("G:"):
            if now - self._last_move_time < MOVE_COOLDOWN_SEC:
                return
        self._last_move_time = now

        if not (self.serial_port and self.serial_port.is_open):
            return

        try:
            self.serial_port.write(f"{command_str}\n".encode("utf-8"))
        except serial.SerialTimeoutException:
            pass  # 시리얼 버퍼가 꽉 찬 경우, 다음 명령에서 재시도
        except serial.SerialException as e:
            self.arduino_status_var.set("통신 오류")
            print(f"Serial Error: {e}")

    def emergency_stop(self):
        self.is_emergency_stop = True
        self.arduino_status_var.set("긴급 정지됨")
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.write(b"STOP\n")
            except serial.SerialException:
                pass
        messagebox.showwarning("긴급 정지", "모든 하드웨어 동작을 중지합니다.")

    # ------------------------------------------------------------------
    # 키보드 조작
    # ------------------------------------------------------------------
    def bind_keys(self):
        self.root.bind("<KeyPress>", self.on_key_press)

    def on_key_press(self, event):
        key = event.keysym.lower()
        if key == "space":
            self.toggle_gripper()
        elif key in KEY_TO_COMMAND:
            self.execute_hardware_cmd(KEY_TO_COMMAND[key])

    def toggle_gripper(self):
        target_angle = GRIPPER_OPEN_ANGLE_DEFAULT if self.is_gripper_closed else GRIPPER_CLOSE_ANGLE_DEFAULT
        self.execute_hardware_cmd(f"G:{target_angle}")
        self.is_gripper_closed = not self.is_gripper_closed

    # ------------------------------------------------------------------
    # 카메라 / 영상 처리
    # ------------------------------------------------------------------
    def start_camera(self):
        self.cap = cv2.VideoCapture(CAMERA_INDEX)
        if not self.cap.isOpened():
            messagebox.showerror(
                "카메라 오류",
                f"카메라({CAMERA_INDEX}번)를 열 수 없습니다.\n연결 상태를 확인 후 프로그램을 재시작하세요.",
            )
            self.cap = None
            return
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

    @staticmethod
    def _virtual_button_boxes(w, h):
        return {
            "Y+": (int(w / 2) - 50, 20, int(w / 2) + 50, 100),
            "Y-": (int(w / 2) - 50, h - 100, int(w / 2) + 50, h - 20),
            "X-": (20, int(h / 2) - 50, 100, int(h / 2) + 50),
            "X+": (w - 100, int(h / 2) - 50, w - 20, int(h / 2) + 50),
        }

    def video_loop(self):
        """백그라운드 스레드: 카메라 캡처 + 손 인식 처리만 수행 (Tk 위젯은 건드리지 않음)."""
        while self.is_running:
            if self.cap is None:
                time.sleep(0.5)
                continue

            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.1)
                continue

            frame = cv2.flip(frame, 1)  # 거울 모드
            h, w, _ = frame.shape
            boxes = self._virtual_button_boxes(w, h)

            # 인식용 사본은 버튼/골격이 그려지기 전, 축소된 상태로 먼저 만든다.
            # 작은 이미지에서 색변환을 하므로 풀해상도 변환을 한 번 아낄 수 있다.
            small_bgr = cv2.resize(frame, (HAND_DETECTION_WIDTH, HAND_DETECTION_HEIGHT))
            detection_frame = cv2.cvtColor(small_bgr, cv2.COLOR_BGR2RGB)
            hand_results = self.hands.process(detection_frame)

            for cmd, (x1, y1, x2, y2) in boxes.items():
                cv2.rectangle(frame, (x1, y1), (x2, y2), BUTTON_COLOR_IDLE, 2)
                cv2.putText(frame, cmd, (x1 + 15, y1 + 50), cv2.FONT_HERSHEY_SIMPLEX, 1, BUTTON_COLOR_IDLE, 2)

            if hand_results.multi_hand_landmarks:
                for hand_landmarks in hand_results.multi_hand_landmarks:
                    self.mp_draw.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)

                    index_finger_tip = hand_landmarks.landmark[8]
                    cx, cy = int(index_finger_tip.x * w), int(index_finger_tip.y * h)
                    cv2.circle(frame, (cx, cy), 15, POINTER_COLOR, cv2.FILLED)

                    for cmd, (x1, y1, x2, y2) in boxes.items():
                        if x1 < cx < x2 and y1 < cy < y2:
                            cv2.rectangle(frame, (x1, y1), (x2, y2), BUTTON_COLOR_ACTIVE, cv2.FILLED)
                            cv2.putText(frame, cmd, (x1 + 15, y1 + 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                            self.execute_hardware_cmd(cmd)
                            break

            rgb_display = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            with self._frame_lock:
                self._pending_bgr_frame = rgb_display

    def refresh_canvas(self):
        """메인(Tk) 스레드에서 주기적으로 호출되어 최신 프레임을 화면에 그린다."""
        with self._frame_lock:
            frame = self._pending_bgr_frame
            self._pending_bgr_frame = None

        if frame is not None:
            img = PIL.Image.fromarray(frame)
            self._latest_photo_image = PIL.ImageTk.PhotoImage(image=img)
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self._latest_photo_image)

        if self.is_running:
            self.root.after(VIDEO_LOOP_INTERVAL_MS, self.refresh_canvas)

    # ------------------------------------------------------------------
    # 종료 처리
    # ------------------------------------------------------------------
    def on_closing(self):
        self.is_running = False
        self.is_emergency_stop = True
        self.video_thread.join(timeout=1.0)

        self.disconnect_arduino()
        if self.cap is not None:
            self.cap.release()
        self.hands.close()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = CandyRobotApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
