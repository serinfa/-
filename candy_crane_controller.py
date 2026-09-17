import threading
import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import numpy as np
import PIL.Image
import PIL.ImageTk
import mediapipe as mp
import serial
import serial.tools.list_ports
import time
import math

class CandyRobotApp:
    def __init__(self, root):
        self.root = root
        self.root.title("내가 지휘하는 AI 사탕뽑기 로봇 (튕김 거리 가변 설정)")
        self.root.geometry("1024x680")
        self.root.minsize(900, 600)
        self.root.configure(bg="#F8F9FA")

        try:
            self.root.attributes('-zoomed', True)
        except:
            pass

        self.x_speed = tk.IntVar(value=10)
        self.y_speed = tk.IntVar(value=10)
        self.z_speed = tk.IntVar(value=10)
        self.z_time = tk.DoubleVar(value=2.0)
        self.grab_delay = tk.DoubleVar(value=2.0)
        self.safe_zone_scale = tk.IntVar(value=30)
        self.home_delay = tk.DoubleVar(value=5.0)

        # 🟢 [추가됨] 설정창에서 조절할 튕김 거리 변수 (기본값: 15스텝)
        self.bounce_steps = tk.IntVar(value=15)

        self.gripper_open_angle = tk.IntVar(value=180)
        self.gripper_close_angle = tk.IntVar(value=90)
        self.gripper_delay = tk.DoubleVar(value=1.5)

        self.camera_index = tk.IntVar(value=0)
        self.ai_confidence = tk.DoubleVar(value=0.7)
        self.pinch_grab_dist = tk.DoubleVar(value=0.05)
        self.pinch_drop_dist = tk.DoubleVar(value=0.1)

        self.key_forward = tk.StringVar(value="W")
        self.key_backward = tk.StringVar(value="S")
        self.key_left = tk.StringVar(value="A")
        self.key_right = tk.StringVar(value="D")
        self.key_up = tk.StringVar(value="Q")
        self.key_down = tk.StringVar(value="E")
        self.key_g_open = tk.StringVar(value="J")
        self.key_g_close = tk.StringVar(value="K")
        self.key_stop = tk.StringVar(value="SPACE")

        self.baudrate = tk.IntVar(value=115200)
        self.cmd_cooldown = tk.DoubleVar(value=0.08)
        self.frame_delay = tk.DoubleVar(value=0.015)

        self.serial_port = None
        self.is_emergency_stop = False
        self.session_active = False
        self.is_sequence_running = False
        self.is_blur_on = False

        self.control_mode = tk.StringVar(value="AUTO")
        self.hardware_mode = tk.StringVar(value="VIRTUAL")

        self.display_status = "대기중"
        self.arduino_status_var = tk.StringVar(value="시스템 실시간 로그 : 대기중")
        self.last_cmd_time = 0.0
        self.was_in_safe_zone = False
        self.safe_zone_enter_time = 0.0

        self.init_ai_models()
        self.create_main_ui()
        self.root.bind("<Key>", self.on_keyboard_press)

        self.init_camera()

        self.video_thread = threading.Thread(target=self.video_loop, daemon=True)
        self.video_thread.start()

    def init_ai_models(self):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            max_num_hands=1,
            min_detection_confidence=self.ai_confidence.get(),
            min_tracking_confidence=self.ai_confidence.get()
        )
        self.mp_draw = mp.solutions.drawing_utils
        self.mp_selfie_segmentation = mp.solutions.selfie_segmentation
        self.selfie_segmentation = self.mp_selfie_segmentation.SelfieSegmentation(model_selection=1)

    def init_camera(self):
        if hasattr(self, 'cap') and self.cap.isOpened():
            self.cap.release()
        self.cap = cv2.VideoCapture(self.camera_index.get())
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    def create_main_ui(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        title_lbl = tk.Label(self.root, text="내가 지휘하는 AI 사탕뽑기 로봇", bg="#343A40", fg="white", font=("맑은 고딕", 20, "bold"), pady=5)
        title_lbl.pack(fill=tk.X)

        main_frame = tk.Frame(self.root, bg="#F8F9FA", padx=5, pady=5)
        main_frame.pack(fill=tk.BOTH, expand=True)

        left_frame = tk.Frame(main_frame, bg="#F8F9FA")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        self.canvas = tk.Canvas(left_frame, bg='black', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        self.canvas_img = self.canvas.create_image(0, 0, anchor=tk.NW)
        self.canvas_text_shadow = self.canvas.create_text(22, 22, text="", fill="black", font=("맑은 고딕", 28, "bold"), anchor=tk.NW)
        self.canvas_text = self.canvas.create_text(20, 20, text="", fill="white", font=("맑은 고딕", 28, "bold"), anchor=tk.NW)

        status_frame = tk.Frame(left_frame, bg="#4A78D0", height=30)
        status_frame.pack(fill=tk.X)
        status_frame.pack_propagate(False)
        self.log_lbl = tk.Label(status_frame, textvariable=self.arduino_status_var, bg="#4A78D0", fg="white", font=("맑은 고딕", 12, "bold"))
        self.log_lbl.pack(fill=tk.BOTH, expand=True)

        right_outer_frame = tk.Frame(main_frame, bg="#F8F9FA", width=350)
        right_outer_frame.pack(side=tk.RIGHT, fill=tk.Y)
        right_outer_frame.pack_propagate(False)

        canvas_scroll = tk.Canvas(right_outer_frame, bg="#F8F9FA", highlightthickness=0)
        scrollbar = ttk.Scrollbar(right_outer_frame, orient="vertical", command=canvas_scroll.yview)
        right_frame = tk.Frame(canvas_scroll, bg="#F8F9FA")
        right_frame.bind("<Configure>", lambda e: canvas_scroll.configure(scrollregion=canvas_scroll.bbox("all")))
        canvas_scroll.create_window((0, 0), window=right_frame, anchor="nw", width=330)
        canvas_scroll.configure(yscrollcommand=scrollbar.set)
        canvas_scroll.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        def _on_mousewheel(event):
            canvas_scroll.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas_scroll.bind_all("<MouseWheel>", _on_mousewheel)

        btn_style = {"bg": "#4A78D0", "fg": "white", "font": ("맑은 고딕", 10, "bold"), "relief": "raised", "bd": 3}
        red_style = {"bg": "#F44336", "fg": "white", "font": ("맑은 고딕", 10, "bold"), "relief": "raised", "bd": 3}
        j_style = {"bg": "#4A78D0", "fg": "white", "font": ("맑은 고딕", 9, "bold"), "width": 11, "relief": "raised", "bd": 3}

        conn_frame = ttk.LabelFrame(right_frame, text=" 아두이노 통신 연결 ")
        conn_frame.pack(fill=tk.X, pady=(0, 5), ipady=2)
        port_frame = tk.Frame(conn_frame)
        port_frame.pack(fill=tk.X, padx=5, pady=2)
        self.port_combobox = ttk.Combobox(port_frame, values=[p.device for p in serial.tools.list_ports.comports()], state="readonly")
        self.port_combobox.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        tk.Button(port_frame, text="새로고침", command=self.refresh_ports, **btn_style).pack(side=tk.RIGHT)

        btn_conn_frame = tk.Frame(conn_frame)
        btn_conn_frame.pack(fill=tk.X, padx=5, pady=2)
        tk.Button(btn_conn_frame, text="가상(테스트)", command=self.enable_virtual_mode, **btn_style).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        tk.Button(btn_conn_frame, text="실제 연결", command=lambda: self.connect_arduino(self.port_combobox.get()), **btn_style).pack(side=tk.RIGHT, fill=tk.X, expand=True)

        core_frame = ttk.LabelFrame(right_frame, text=" 로봇 운전 제어 ")
        core_frame.pack(fill=tk.X, pady=(0, 5), ipady=2)

        mode_frame = tk.Frame(core_frame)
        mode_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Radiobutton(mode_frame, text="🤖 자동", variable=self.control_mode, value="AUTO").pack(side=tk.LEFT, expand=True)
        ttk.Radiobutton(mode_frame, text="🕹️ 수동", variable=self.control_mode, value="MANUAL").pack(side=tk.RIGHT, expand=True)

        self.btn_blur = tk.Button(core_frame, text="🌫️ 배경 흐림: OFF", command=self.toggle_blur, bg="#6C757D", fg="white", font=("맑은 고딕", 10, "bold"), relief="raised", bd=3)
        self.btn_blur.pack(fill=tk.X, padx=5, pady=2)

        btn_core_frame1 = tk.Frame(core_frame)
        btn_core_frame1.pack(fill=tk.X, padx=5, pady=2)
        tk.Button(btn_core_frame1, text="▶ 체험 시작", command=self.on_start, **btn_style).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        tk.Button(btn_core_frame1, text="⏹ 대기", command=self.on_end, **red_style).pack(side=tk.RIGHT, fill=tk.X, expand=True)

        tk.Button(core_frame, text="🏠 기계 원점(Home) 복귀", command=lambda: self.execute_hardware_cmd("HOME"), **btn_style).pack(fill=tk.X, padx=5, pady=2)
        tk.Button(core_frame, text="⚙️ 파라미터 종합 설정", command=self.open_settings_window, **btn_style).pack(fill=tk.X, padx=5, pady=2)

        joy_frame = ttk.LabelFrame(right_frame, text=" 수동 조이스틱 (키보드 매핑) ")
        joy_frame.pack(fill=tk.BOTH, expand=True, ipady=2)
        joy_grid = tk.Frame(joy_frame)
        joy_grid.pack(expand=True)

        self.btn_joy_fw = tk.Button(joy_grid, text=f"전진[{self.key_forward.get()}]", command=lambda: self.execute_hardware_cmd("Y+"), **j_style)
        self.btn_joy_fw.grid(row=0, column=1, pady=2)
        self.btn_joy_l = tk.Button(joy_grid, text=f"좌측[{self.key_left.get()}]", command=lambda: self.execute_hardware_cmd("X-"), **j_style)
        self.btn_joy_l.grid(row=1, column=0, padx=2)
        self.btn_joy_stop = tk.Button(joy_grid, text=f"정지[{self.key_stop.get()}]", command=lambda: self.execute_hardware_cmd("STOP_XY"), bg="#F44336", fg="white", font=("맑은 고딕", 9, "bold"), width=11, relief="raised", bd=3)
        self.btn_joy_stop.grid(row=1, column=1, padx=2)
        self.btn_joy_r = tk.Button(joy_grid, text=f"우측[{self.key_right.get()}]", command=lambda: self.execute_hardware_cmd("X+"), **j_style)
        self.btn_joy_r.grid(row=1, column=2, padx=2)
        self.btn_joy_bw = tk.Button(joy_grid, text=f"후진[{self.key_backward.get()}]", command=lambda: self.execute_hardware_cmd("Y-"), **j_style)
        self.btn_joy_bw.grid(row=2, column=1, pady=2)
        self.btn_joy_up = tk.Button(joy_grid, text=f"상승[{self.key_up.get()}]", command=lambda: self.execute_hardware_cmd("Z+"), **j_style)
        self.btn_joy_up.grid(row=3, column=0, pady=2)
        self.btn_joy_dn = tk.Button(joy_grid, text=f"하강[{self.key_down.get()}]", command=lambda: self.execute_hardware_cmd("Z-"), **j_style)
        self.btn_joy_dn.grid(row=3, column=2, pady=2)
        self.btn_joy_g_open = tk.Button(joy_grid, text=f"집게열기[{self.key_g_open.get()}]", command=lambda: self.execute_hardware_cmd(f"G:{self.gripper_open_angle.get()}"), **j_style)
        self.btn_joy_g_open.grid(row=4, column=0, pady=2)
        self.btn_joy_g_close = tk.Button(joy_grid, text=f"집게닫기[{self.key_g_close.get()}]", command=lambda: self.execute_hardware_cmd(f"G:{self.gripper_close_angle.get()}"), **j_style)
        self.btn_joy_g_close.grid(row=4, column=2, pady=2)

    def apply_settings(self, win):
        self.btn_joy_fw.config(text=f"전진[{self.key_forward.get()}]")
        self.btn_joy_l.config(text=f"좌측[{self.key_left.get()}]")
        self.btn_joy_stop.config(text=f"정지[{self.key_stop.get()}]")
        self.btn_joy_r.config(text=f"우측[{self.key_right.get()}]")
        self.btn_joy_bw.config(text=f"후진[{self.key_backward.get()}]")
        self.btn_joy_up.config(text=f"상승[{self.key_up.get()}]")
        self.btn_joy_dn.config(text=f"하강[{self.key_down.get()}]")
        self.btn_joy_g_open.config(text=f"집게열기[{self.key_g_open.get()}]")
        self.btn_joy_g_close.config(text=f"집게닫기[{self.key_g_close.get()}]")

        self.init_ai_models()
        self.init_camera()
        win.destroy()

    def toggle_blur(self):
        self.is_blur_on = not self.is_blur_on
        if self.is_blur_on:
            self.btn_blur.config(text="🌫️ 배경 흐림: ON", bg="#4A78D0")
        else:
            self.btn_blur.config(text="🌫️ 배경 흐림: OFF", bg="#6C757D")

    def open_settings_window(self):
        set_win = tk.Toplevel(self.root)
        set_win.title("종합 환경 설정")
        set_win.geometry("450x580")
        set_win.transient(self.root)
        set_win.grab_set()

        notebook = ttk.Notebook(set_win)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 5))

        tab1, tab2, tab3, tab4 = ttk.Frame(notebook), ttk.Frame(notebook), ttk.Frame(notebook), ttk.Frame(notebook)
        notebook.add(tab1, text="모터 및 환경")
        notebook.add(tab2, text="비전 및 집게")
        notebook.add(tab3, text="통신 및 성능")
        notebook.add(tab4, text="단축키 맵")

        # 🟢 [추가됨] 설정창 탭1에 "충돌 시 튕김 거리(스텝)" 옵션 추가
        opts1 = [("X축 이동 속도:", self.x_speed), ("Y축 이동 속도:", self.y_speed),
                 ("Z축 승강 속도:", self.z_speed), ("Z축 승강 시간(초):", self.z_time),
                 ("안전구역 대기시간(초):", self.grab_delay), ("안전구역 크기(%, 10~100):", self.safe_zone_scale),
                 ("원점 복귀 대기시간(초):", self.home_delay), ("충돌 시 튕김 거리(Step):", self.bounce_steps)]
        for i, (lbl, var) in enumerate(opts1):
            ttk.Label(tab1, text=lbl).grid(row=i, column=0, pady=12, padx=15, sticky="w")
            ttk.Entry(tab1, textvariable=var, width=12).grid(row=i, column=1)

        opts2 = [("집게 열림 각도(°):", self.gripper_open_angle), ("집게 닫힘 각도(°):", self.gripper_close_angle),
                 ("집게 동작 지연시간(초):", self.gripper_delay), ("카메라 장치 번호(0, 1..):", self.camera_index),
                 ("AI 인식 신뢰도(0.0~1.0):", self.ai_confidence), ("꼬집기(Grab) 민감도:", self.pinch_grab_dist),
                 ("놓기(Drop) 민감도:", self.pinch_drop_dist)]
        for i, (lbl, var) in enumerate(opts2):
            ttk.Label(tab2, text=lbl).grid(row=i, column=0, pady=12, padx=15, sticky="w")
            ttk.Entry(tab2, textvariable=var, width=12).grid(row=i, column=1)

        opts3 = [("시리얼 속도(bps):", self.baudrate), ("명령어 쿨다운(초):", self.cmd_cooldown),
                 ("카메라 화면 갱신율(초):", self.frame_delay)]
        for i, (lbl, var) in enumerate(opts3):
            ttk.Label(tab3, text=lbl).grid(row=i, column=0, pady=20, padx=15, sticky="w")
            ttk.Entry(tab3, textvariable=var, width=12).grid(row=i, column=1)

        keys = [("전진 (Y+)", self.key_forward), ("후진 (Y-)", self.key_backward),
                ("좌측 (X-)", self.key_left), ("우측 (X+)", self.key_right),
                ("상승 (Z+)", self.key_up), ("하강 (Z-)", self.key_down),
                ("집게 열기", self.key_g_open), ("집게 닫기", self.key_g_close),
                ("정지 (SPACE)", self.key_stop)]
        for i, (lbl, var) in enumerate(keys):
            ttk.Label(tab4, text=lbl).grid(row=i, column=0, pady=8, padx=15, sticky="w")
            ttk.Entry(tab4, textvariable=var, width=12).grid(row=i, column=1)

        btn_frame = tk.Frame(set_win)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=10, padx=10)
        tk.Button(btn_frame, text="💾 설정 저장 (실시간 반영)", command=lambda: self.apply_settings(set_win), bg="#4A78D0", fg="white", font=("맑은 고딕", 11, "bold"), relief="raised", bd=4).pack(fill=tk.X, ipady=5)

    def start_return_home_sequence(self):
        if self.is_sequence_running or self.is_emergency_stop or not self.session_active: return
        self.is_sequence_running = True
        self.display_status = "사탕뽑는 중"
        self.arduino_status_var.set("시스템 실시간 로그 : 🤖 사탕을 뽑고 있습니다. 원점으로 자동 복귀합니다.")

        def sequence_thread():
            try:
                if self.is_emergency_stop or not self.session_active: return
                self.execute_hardware_cmd(f"G:{self.gripper_close_angle.get()}")
                time.sleep(self.gripper_delay.get())

                if self.is_emergency_stop or not self.session_active: return
                self.execute_hardware_cmd("Z+")
                time.sleep(self.z_time.get())
                self.execute_hardware_cmd("STOP_XY")
                time.sleep(1.0)

                if self.is_emergency_stop or not self.session_active: return
                self.execute_hardware_cmd("HOME")
                time.sleep(self.home_delay.get())

                if self.is_emergency_stop or not self.session_active: return
                self.execute_hardware_cmd(f"G:{self.gripper_open_angle.get()}")
                time.sleep(self.gripper_delay.get())

            finally:
                self.is_sequence_running = False
                if not self.is_emergency_stop:
                    self.root.after(500, self.on_end)

        threading.Thread(target=sequence_thread, daemon=True).start()

    def refresh_ports(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combobox['values'] = ports
        if ports: self.port_combobox.current(0)

    def connect_arduino(self, port):
        if not port:
            messagebox.showwarning("포트 선택", "연결할 COM 포트를 선택하세요.")
            return
        try:
            self.serial_port = serial.Serial(port, self.baudrate.get(), timeout=0.1, write_timeout=0.1)
            time.sleep(1.5)
            self.hardware_mode.set("REAL")
            self.arduino_status_var.set(f"시스템 실시간 로그 : 아두이노 실제 연결 완료 ({port})")
        except Exception as e:
            messagebox.showerror("연결 오류", f"아두이노 연결 실패:\n{e}")

    def enable_virtual_mode(self):
        self.hardware_mode.set("VIRTUAL")
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
            self.serial_port = None
        self.arduino_status_var.set("시스템 실시간 로그 : 가상 테스트 모드 가동 중")

    def on_start(self):
        self.session_active = True
        self.is_emergency_stop = False
        if self.control_mode.get() == "AUTO":
            self.display_status = "체험중(Autotrack)"
            self.arduino_status_var.set("시스템 실시간 로그 : 체험 시작! [자동 모드]")
        else:
            self.display_status = "체험중(수동조작)"
            self.arduino_status_var.set("시스템 실시간 로그 : 체험 시작! [수동 모드]")

    def on_end(self):
        self.session_active = False
        self.was_in_safe_zone = False
        self.execute_hardware_cmd("STOP_XY")
        self.display_status = "대기중"
        self.arduino_status_var.set("시스템 실시간 로그 : 🛑 체험 종료 (시스템 안전 대기 상태)")

    def execute_hardware_cmd(self, command_str):
        if self.is_emergency_stop: return

        if not self.session_active and command_str != "HOME":
            return

        current_time = time.time()
        if command_str not in ["STOP", "STOP_XY", "HOME"] and not command_str.startswith("G:"):
            if current_time - getattr(self, 'last_cmd_time', 0) < self.cmd_cooldown.get():
                return
        self.last_cmd_time = current_time

        xy_delay = max(600, 2200 - (self.x_speed.get() * 100))
        z_delay = max(600, 2200 - (self.z_speed.get() * 100))
        bounce = self.bounce_steps.get() # 설정창의 튕김 스텝 값 가져오기

        # 🟢 [핵심] 명령어 포맷을 "방향_속도_튕김거리" 형태로 전송합니다 (예: "X+_1200_15")
        final_cmd = command_str
        if command_str in ["X+", "X-", "Y+", "Y-"]:
            final_cmd = f"{command_str}_{xy_delay}_{bounce}"
        elif command_str in ["Z+", "Z-"]:
            final_cmd = f"{command_str}_{z_delay}_{bounce}"
        elif command_str == "HOME":
            final_cmd = f"HOME_{xy_delay}_{bounce}"

        if self.hardware_mode.get() == "REAL" and hasattr(self, 'serial_port') and self.serial_port and self.serial_port.is_open:
            try: self.serial_port.write(f"{final_cmd}\n".encode('utf-8'))
            except serial.SerialTimeoutException: pass
            except Exception as e: print(f"Serial Error: {e}")

    def on_keyboard_press(self, event):
        if event.keysym.upper() == "SPACE" or event.keysym.upper() == self.key_stop.get().upper():
            self.execute_hardware_cmd("STOP_XY")
            if self.control_mode.get() == "AUTO": self.on_end()
            return

        if self.is_emergency_stop or not self.session_active or self.control_mode.get() == "AUTO": return

        p_sym = event.keysym.upper()
        p_char = event.char.upper() if event.char else ""
        target = None

        if p_sym == self.key_forward.get().upper() or p_char == self.key_forward.get().upper(): target = "Y+"
        elif p_sym == self.key_backward.get().upper() or p_char == self.key_backward.get().upper(): target = "Y-"
        elif p_sym == self.key_left.get().upper() or p_char == self.key_left.get().upper(): target = "X-"
        elif p_sym == self.key_right.get().upper() or p_char == self.key_right.get().upper(): target = "X+"
        elif p_sym == self.key_up.get().upper() or p_char == self.key_up.get().upper(): target = "Z+"
        elif p_sym == self.key_down.get().upper() or p_char == self.key_down.get().upper(): target = "Z-"
        elif p_sym == self.key_g_open.get().upper() or p_char == self.key_g_open.get().upper(): target = f"G:{self.gripper_open_angle.get()}"
        elif p_sym == self.key_g_close.get().upper() or p_char == self.key_g_close.get().upper(): target = f"G:{self.gripper_close_angle.get()}"

        if target: self.execute_hardware_cmd(target)

    def video_loop(self):
        while True:
            if not hasattr(self, 'cap') or not self.cap.isOpened():
                time.sleep(0.1)
                continue
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.1)
                continue

            frame = cv2.flip(frame, 1)
            h, w, c = frame.shape

            if self.is_blur_on:
                rgb_for_blur = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                seg_results = self.selfie_segmentation.process(rgb_for_blur)
                condition = np.stack((seg_results.segmentation_mask,) * 3, axis=-1) > 0.1
                blurred_frame = cv2.GaussianBlur(frame, (55, 55), 0)
                frame = np.where(condition, frame, blurred_frame)

            cv2.line(frame, (int(w/2), 0), (int(w/2), h), (0, 0, 255), 1)
            cv2.line(frame, (0, int(h/2)), (w, int(h/2)), (0, 0, 255), 1)

            scale_ratio = self.safe_zone_scale.get() / 200.0
            safe_x1 = max(0.0, 0.5 - scale_ratio)
            safe_x2 = min(1.0, 0.5 + scale_ratio)
            safe_y1 = max(0.0, 0.5 - scale_ratio)
            safe_y2 = min(1.0, 0.5 + scale_ratio)

            overlay = frame.copy()
            cv2.rectangle(overlay, (int(w * safe_x1), int(h * safe_y1)), (int(w * safe_x2), int(h * safe_y2)), (220, 170, 140), -1)
            cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)
            cv2.putText(frame, "SAFE ZONE (GRAB ONLY)", (int(w/2)-90, int(h/2)-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

            if self.session_active and self.control_mode.get() == "AUTO":
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                hand_results = self.hands.process(rgb_frame)

                if hand_results.multi_hand_landmarks:
                    for hand_landmarks in hand_results.multi_hand_landmarks:
                        self.mp_draw.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)

                        center = hand_landmarks.landmark[9]
                        cv2.circle(frame, (int(center.x * w), int(center.y * h)), 8, (255, 0, 0), -1)

                        is_in_safe_zone = (safe_x1 <= center.x <= safe_x2) and (safe_y1 <= center.y <= safe_y2)

                        if is_in_safe_zone:
                            self.execute_hardware_cmd("STOP_XY")

                            if not self.was_in_safe_zone:
                                self.was_in_safe_zone = True
                                self.safe_zone_enter_time = time.time()

                            elapsed = time.time() - self.safe_zone_enter_time

                            if not self.is_sequence_running:
                                if elapsed < self.grab_delay.get():
                                    remain = self.grab_delay.get() - elapsed
                                    cv2.putText(frame, f"WAIT... {remain:.1f}s", (w - 200, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
                                else:
                                    cv2.putText(frame, "READY TO GRAB", (w - 200, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                                    thumb = hand_landmarks.landmark[4]
                                    index = hand_landmarks.landmark[8]
                                    pinch_dist = math.hypot(thumb.x - index.x, thumb.y - index.y)

                                    if pinch_dist < self.pinch_grab_dist.get():
                                        self.start_return_home_sequence()
                                    elif pinch_dist > self.pinch_drop_dist.get():
                                        self.execute_hardware_cmd(f"G:{self.gripper_open_angle.get()}")
                        else:
                            self.was_in_safe_zone = False
                            if not self.is_sequence_running:
                                if center.x < safe_x1:
                                    self.execute_hardware_cmd("X-")
                                    cv2.putText(frame, "TRACK: LEFT", (w - 180, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                                elif center.x > safe_x2:
                                    self.execute_hardware_cmd("X+")
                                    cv2.putText(frame, "TRACK: RIGHT", (w - 180, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)

                                if center.y < safe_y1:
                                    self.execute_hardware_cmd("Y+")
                                    cv2.putText(frame, "TRACK: FWD", (w - 180, 125), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                                elif center.y > safe_y2:
                                    self.execute_hardware_cmd("Y-")
                                    cv2.putText(frame, "TRACK: BWD", (w - 180, 125), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                else:
                    self.was_in_safe_zone = False
                    if not self.is_sequence_running:
                        self.execute_hardware_cmd("STOP_XY")
            else:
                self.was_in_safe_zone = False

            img = PIL.Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            canvas_w = self.canvas.winfo_width()
            canvas_h = self.canvas.winfo_height()

            if canvas_w > 20 and canvas_h > 20:
                img = img.resize((canvas_w, canvas_h), PIL.Image.Resampling.LANCZOS)

            imgtk = PIL.ImageTk.PhotoImage(image=img)

            self.canvas.itemconfig(self.canvas_img, image=imgtk)
            self.canvas.imgtk = imgtk

            if self.display_status == "대기중": text_color = "#FF3B30"
            elif self.display_status == "사탕뽑는 중": text_color = "#F59E0B"
            else: text_color = "#10B981"

            self.canvas.itemconfig(self.canvas_text_shadow, text=self.display_status)
            self.canvas.itemconfig(self.canvas_text, text=self.display_status, fill=text_color)

            time.sleep(self.frame_delay.get())

    def on_closing(self):
        self.is_emergency_stop = True
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        if hasattr(self, 'cap') and self.cap.isOpened():
            self.cap.release()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = CandyRobotApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
