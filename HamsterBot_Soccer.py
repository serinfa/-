import cv2
import cv2.aruco as aruco
import numpy as np
import math
import time
import tkinter as tk
from tkinter import font, messagebox, simpledialog
from PIL import Image, ImageTk
from roboid import *

class HamsterSoccerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("햄스터봇 AI 로봇축구 (아루코 마커 추적 모드)")
        self.root.geometry("1100x780")
        self.root.minsize(1000, 700)
        self.root.configure(bg="white")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.bg_color = "#537bc4"
        self.button_color = "#7f8c8d"
        self.text_color = "white"
        self.title_font = font.Font(family="맑은 고딕", size=20, weight="bold")
        self.score_font = font.Font(family="맑은 고딕", size=48, weight="bold")
        self.btn_font = font.Font(family="맑은 고딕", size=12, weight="bold")
        self.section_font = font.Font(family="맑은 고딕", size=11, weight="bold")
        self.status_font = font.Font(family="맑은 고딕", size=12, weight="bold")

        self.is_playing = False
        self.game_time_minutes = 3
        self.remaining_seconds = self.game_time_minutes * 60
        self.timer_id = None

        self.base_speed = 50

        self.detected_status = {'ball': False, 'r1': False, 'r2': False, 'camera': False}
        # 상태등에 표시할 (인식됨/연결됨 문구, 미인식/끊김 문구)
        self.status_text_map = {
            'ball': ("인식됨", "미인식"),
            'r1': ("인식됨", "미인식"),
            'r2': ("인식됨", "미인식"),
            'camera': ("연결됨", "연결 끊김"),
        }

        # 로봇에 실제로 부착된 아루코 마커 ID. 카메라 화면의 "Detected marker IDs"
        # 표시로 확인한 실제 값으로 맞춰야 함 (라벨을 다시 인쇄할 필요 없음).
        self.robot_marker_ids = {'r1': 0, 'r2': 1}

        self.active_mode = tk.StringVar(value="both")
        self.show_debug = tk.BooleanVar(value=False)

        self.h1, self.h2 = None, None
        try:
            self.h1 = Hamster(0)
            self.h2 = Hamster(1)
        except Exception as e:
            print("초기 연결 실패:", e)

        self.camera_url = "http://192.168.66.1:9527/videostream.cgi?loginuse=admin&loginpas=admin"
        self.cap = cv2.VideoCapture(self.camera_url, cv2.CAP_FFMPEG)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
        self.detected_status['camera'] = self.cap.isOpened()
        self.camera_fail_count = 0
        self.camera_fail_limit = 10  # 이 횟수만큼 연속으로 프레임을 못 받으면 "연결 끊김"으로 표시

        self.ball_lower = np.array([15, 90, 90])
        self.ball_upper = np.array([45, 255, 255])

        # 골대 색상 - 빨강: AI 골대, 파랑: 플레이어 골대. 조명에 따라 값 조정 필요.
        # 빨강은 HSV 색상환의 양 끝(0 근처와 180 근처)에 걸쳐 있어 두 구간을 합쳐서 사용.
        self.goal_ai_lower1 = np.array([0, 110, 70])
        self.goal_ai_upper1 = np.array([10, 255, 255])
        self.goal_ai_lower2 = np.array([170, 110, 70])
        self.goal_ai_upper2 = np.array([180, 255, 255])
        self.goal_player_lower = np.array([95, 110, 70])
        self.goal_player_upper = np.array([135, 255, 255])
        self.min_goal_area = 800

        # 공격 로봇이 공을 "상대(Player) 골대" 쪽으로 밀도록 유도하는 접근 전략 파라미터.
        # 공만 보고 바로 돌진하면 접근 방향에 따라 자책골이 날 수 있어서,
        # 골대 반대편(공 뒤쪽)으로 먼저 돌아가게 한 뒤에 공을 미는 방식을 사용한다.
        self.attack_behind_offset = 55   # 공-골대 연장선에서 공 뒤쪽으로 경유할 거리(px)
        self.attack_align_threshold = 45  # 이 거리 이내면 이미 공 뒤에 있다고 보고 바로 공을 밀어붙임

        self.score = {'ai': 0, 'player': 0}
        # 공이 골대 밖으로 나갔다가 다시 들어오기 전까지는 그 골대에서 재득점되지 않도록 하는 잠금 상태
        self.goal_armed = {'ai': True, 'player': True}
        self.goal_pause_until = 0.0      # 득점 직후 잠깐 로봇을 멈춰 "득점 정지"처럼 보이게 함
        self.goal_flash_text = None
        self.goal_flash_until = 0.0

        # 골대 위치를 색상 대신 영상에서 직접 드래그로 지정한 경우 (x, y, w, h), 원본 프레임 좌표 기준.
        # None이면 해당 골대는 색상(빨강/파랑) 자동 인식을 사용.
        self.manual_goal_rects = {'ai': None, 'player': None}
        self.goal_pick_side = None       # 드래그로 지정 중인 골대: 'ai' / 'player' / None
        self.goal_drag_start = None
        self.goal_drag_current = None

        # 밝기 채널만 평준화해서 색상(H)은 건드리지 않고 조명 변화에 대한 민감도를 낮춘다
        self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

        # 공 추적 안정화용 상태값
        self.ball_ema = None            # 지수이동평균으로 부드럽게 만든 공 좌표
        self.ball_lost_count = 0        # 공을 놓친 연속 프레임 수
        self.max_lost_frames = 8        # 이 프레임 수까지는 마지막 위치를 유지 (약 0.1~0.2초)
        self.ball_ema_alpha = 0.55

        # 실시간 색상 보정(클릭)용 상태값
        self.calibrating = False
        self.current_hsv = None
        self.orig_frame_shape = (0, 0)
        self.disp_size = (0, 0)

        self.aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_ARUCO_ORIGINAL)
        try:
            self.aruco_params = aruco.DetectorParameters()
            self.is_new_cv2 = True
        except AttributeError:
            self.aruco_params = aruco.DetectorParameters_create()
            self.is_new_cv2 = False

        # 마커가 카메라와 거리가 다르거나 각도가 기울어져도 잡히도록 임계값 탐색 범위를 넓힘
        # (기본값 max=23 은 카메라에 가까이 있는 큰 마커를 놓치기 쉬움)
        self.aruco_params.adaptiveThreshWinSizeMin = 3
        self.aruco_params.adaptiveThreshWinSizeMax = 53
        self.aruco_params.adaptiveThreshWinSizeStep = 4
        self.aruco_params.minMarkerPerimeterRate = 0.02
        self.aruco_params.cornerRefinementMethod = aruco.CORNER_REFINE_SUBPIX
        # 완전히 안 잡히는(후보로도 안 걸리는) 마커를 위한 추가 완화:
        # 기울어진 각도/블러/조명 얼룩으로 정사각형 윤곽이 살짝 틀어지거나
        # 테두리 셀 일부가 오염돼도 후보로 살아남도록 허용 폭을 넓힘.
        self.aruco_params.polygonalApproxAccuracyRate = 0.06
        self.aruco_params.maxErroneousBitsInBorderRate = 0.5
        self.aruco_params.perspectiveRemoveIgnoredMarginPerCell = 0.20
        self.aruco_params.minOtsuStdDev = 3.0

        if self.is_new_cv2:
            self.aruco_detector = aruco.ArucoDetector(self.aruco_dict, self.aruco_params)

        self.setup_ui()
        self.update_frame()

    def _section_frame(self, parent, title):
        """상단 제어 영역에서 기능별로 묶어 보여줄 그룹 박스."""
        frame = tk.LabelFrame(parent, text=title, bg="white", fg=self.bg_color,
                               font=self.section_font, padx=10, pady=5,
                               relief="groove", bd=2)
        return frame

    def setup_ui(self):
        top_frame = tk.Frame(self.root, bg="white")
        top_frame.pack(fill="x", pady=8, padx=20)
        # 중앙(타이머/스코어) 칸만 창 너비에 맞춰 늘어나고 나머지는 내용 크기 유지
        for col, weight in ((0, 0), (1, 0), (2, 1), (3, 0)):
            top_frame.grid_columnconfigure(col, weight=weight)

        # 1. 경기 제어 (시작/정지, 시간 설정)
        game_frame = self._section_frame(top_frame, "경기 제어")
        game_frame.grid(row=0, column=0, sticky="ns", padx=(0, 10))
        self.btn_start = tk.Button(game_frame, text="시작", bg=self.button_color, fg=self.text_color,
                                   font=self.btn_font, width=12, height=2, relief="raised", bd=4, command=self.toggle_play)
        self.btn_start.pack(pady=3)
        tk.Button(game_frame, text="시간 설정", bg=self.button_color, fg=self.text_color,
                  font=self.btn_font, width=12, relief="raised", bd=3, command=self.set_time).pack(pady=3)
        tk.Button(game_frame, text="점수 초기화", bg=self.button_color, fg=self.text_color,
                  font=self.btn_font, width=12, relief="raised", bd=3, command=self.reset_score).pack(pady=3)

        # 2. 로봇 설정 (동작 로봇 선택, 속도, 색상 보정)
        robot_frame = self._section_frame(top_frame, "로봇 설정")
        robot_frame.grid(row=0, column=1, sticky="ns", padx=10)
        mode_sub = tk.Frame(robot_frame, bg="white")
        mode_sub.pack(anchor="w", pady=(0, 6))
        tk.Radiobutton(mode_sub, text=f"1번(ID{self.robot_marker_ids['r1']})만", variable=self.active_mode, value="r1", bg="white").pack(anchor="w")
        tk.Radiobutton(mode_sub, text=f"2번(ID{self.robot_marker_ids['r2']})만", variable=self.active_mode, value="r2", bg="white").pack(anchor="w")
        tk.Radiobutton(mode_sub, text="두 대 모두", variable=self.active_mode, value="both", bg="white").pack(anchor="w")
        tk.Button(robot_frame, text="속도 조절", bg=self.button_color, fg=self.text_color,
                  font=self.btn_font, width=16, relief="raised", bd=3, command=self.set_speed).pack(pady=3, fill="x")
        self.btn_calibrate = tk.Button(robot_frame, text="공 색상 보정(영상 클릭)", bg=self.button_color, fg=self.text_color,
                                        font=self.btn_font, width=16, relief="raised", bd=3, command=self.start_calibration)
        self.btn_calibrate.pack(pady=3, fill="x")

        # 골대 위치: 영상에서 드래그로 직접 지정 (미지정 시 색상 자동 인식)
        tk.Label(robot_frame, text="골대 지정(영상 드래그)", bg="white", font=self.status_font).pack(anchor="w", pady=(4, 0))
        goal_btn_row = tk.Frame(robot_frame, bg="white")
        goal_btn_row.pack(pady=(3, 0), fill="x")
        self.btn_set_ai_goal = tk.Button(goal_btn_row, text="AI골대", bg=self.button_color, fg="white",
                                          font=self.btn_font, width=6, relief="raised", bd=3,
                                          command=lambda: self.start_goal_pick('ai'))
        self.btn_set_ai_goal.pack(side="left", expand=True, fill="x", padx=1)
        self.btn_set_player_goal = tk.Button(goal_btn_row, text="P골대", bg=self.button_color, fg="white",
                                              font=self.btn_font, width=6, relief="raised", bd=3,
                                              command=lambda: self.start_goal_pick('player'))
        self.btn_set_player_goal.pack(side="left", expand=True, fill="x", padx=1)
        tk.Button(goal_btn_row, text="초기화", bg=self.button_color, fg=self.text_color,
                  font=self.btn_font, width=6, relief="raised", bd=3, command=self.reset_goal_zones).pack(side="left", expand=True, fill="x", padx=1)

        # 3. 중앙 타이머 및 점수 (남는 폭을 모두 차지)
        center_frame = tk.Frame(top_frame, bg=self.bg_color, padx=30, pady=10, relief="sunken", bd=2)
        center_frame.grid(row=0, column=2, sticky="nsew", padx=10)
        self.timer_label = tk.Label(center_frame, text="남은 시간 03:00", bg=self.bg_color, fg="yellow", font=self.title_font)
        self.timer_label.pack()

        score_row = tk.Frame(center_frame, bg=self.bg_color)
        score_row.pack(pady=(5, 0))
        score_color = "#ff9500"
        tk.Label(score_row, text="AI", bg=self.bg_color, fg=score_color, font=self.score_font).pack(side="left")
        self.score_mid_label = tk.Label(score_row, text="  0 : 0  ", bg=self.bg_color, fg=score_color, font=self.score_font)
        self.score_mid_label.pack(side="left")
        tk.Label(score_row, text="Player", bg=self.bg_color, fg=score_color, font=self.score_font).pack(side="left")

        # 4. 연결/인식 상태 (실시간 상태등 + 카메라 재연결 + 하드웨어 점검)
        status_frame = self._section_frame(top_frame, "연결 / 인식 상태")
        status_frame.grid(row=0, column=3, sticky="ns", padx=(10, 0))
        self.status_labels = {}
        status_texts = (
            ("camera", "카메라"),
            ("ball", "축구공(노랑)"),
            ("r1", f"로봇 1 (ID{self.robot_marker_ids['r1']})"),
            ("r2", f"로봇 2 (ID{self.robot_marker_ids['r2']})"),
        )
        for key, label_text in status_texts:
            row = tk.Frame(status_frame, bg="white")
            row.pack(anchor="w", fill="x", pady=1)
            tk.Label(row, text=label_text, bg="white", font=self.status_font, width=11, anchor="w").pack(side="left")
            dot = tk.Label(row, text="● 미확인", bg="white", fg="#e74c3c", font=self.status_font)
            dot.pack(side="left")
            self.status_labels[key] = dot
        tk.Button(status_frame, text="카메라 재연결", bg=self.button_color, fg=self.text_color,
                  font=self.btn_font, width=16, relief="raised", bd=3, command=self.reconnect_camera).pack(pady=(8, 0), fill="x")
        tk.Button(status_frame, text="연결/하드웨어 점검", bg=self.button_color, fg=self.text_color,
                  font=self.btn_font, width=16, relief="raised", bd=3, command=self.check_status).pack(pady=3, fill="x")
        tk.Checkbutton(status_frame, text="디버그 정보 표시", variable=self.show_debug,
                        bg="white", font=self.status_font).pack(anchor="w", pady=(3, 0))

        self.video_label = tk.Label(self.root, bg=self.bg_color)
        self.video_label.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        self.video_label.bind("<ButtonPress-1>", self.on_video_press)
        self.video_label.bind("<B1-Motion>", self.on_video_drag)
        self.video_label.bind("<ButtonRelease-1>", self.on_video_release)

        self.update_status_indicators()

    def update_status_indicators(self):
        for key, label in self.status_labels.items():
            ok = self.detected_status[key]
            on_text, off_text = self.status_text_map[key]
            label.config(text=f"● {on_text}" if ok else f"● {off_text}", fg=("#2ecc71" if ok else "#e74c3c"))

    def update_score_display(self):
        self.score_mid_label.config(text=f"  {self.score['ai']} : {self.score['player']}  ")

    def reset_score(self):
        self.score = {'ai': 0, 'player': 0}
        self.goal_armed = {'ai': True, 'player': True}
        self.update_score_display()

    def set_speed(self):
        val = simpledialog.askinteger("속도 조절", "로봇의 직진 속도를 입력하세요 (10~100):", minvalue=10, maxvalue=100, initialvalue=self.base_speed)
        if val:
            self.base_speed = val
            messagebox.showinfo("속도 조절", f"전진 속도가 {self.base_speed}으로 설정되었습니다.")

    def set_time(self):
        if self.is_playing: return
        val = simpledialog.askinteger("시간 설정", "경기 시간을 입력하세요 (1~5분):", minvalue=1, maxvalue=5, initialvalue=self.game_time_minutes)
        if val:
            self.game_time_minutes = val
            self.remaining_seconds = val * 60
            self.update_timer_display()

    def update_timer_display(self):
        mins, secs = divmod(self.remaining_seconds, 60)
        self.timer_label.config(text=f"남은 시간 {mins:02d}:{secs:02d}")

    def start_calibration(self):
        self.calibrating = True
        self.btn_calibrate.config(text="공을 클릭하세요...", bg="orange")

    def _to_frame_coords(self, disp_x, disp_y):
        """화면에 표시된(리사이즈된) 좌표를 실제 카메라 프레임 좌표로 환산."""
        orig_h, orig_w = self.orig_frame_shape
        disp_w, disp_h = self.disp_size
        if orig_w == 0 or orig_h == 0 or disp_w == 0 or disp_h == 0:
            return None, None
        fx = int(disp_x * orig_w / disp_w)
        fy = int(disp_y * orig_h / disp_h)
        fx = max(0, min(orig_w - 1, fx))
        fy = max(0, min(orig_h - 1, fy))
        return fx, fy

    def on_video_press(self, event):
        if self.calibrating:
            fx, fy = self._to_frame_coords(event.x, event.y)
            if fx is not None:
                self._calibrate_ball_at(fx, fy)
            return
        if self.goal_pick_side:
            fx, fy = self._to_frame_coords(event.x, event.y)
            if fx is not None:
                self.goal_drag_start = (fx, fy)
                self.goal_drag_current = (fx, fy)

    def on_video_drag(self, event):
        if self.goal_pick_side and self.goal_drag_start:
            fx, fy = self._to_frame_coords(event.x, event.y)
            if fx is not None:
                self.goal_drag_current = (fx, fy)

    def on_video_release(self, event):
        if not (self.goal_pick_side and self.goal_drag_start):
            return

        fx, fy = self._to_frame_coords(event.x, event.y)
        if fx is None:
            fx, fy = self.goal_drag_current

        x0, y0 = self.goal_drag_start
        x, y = min(x0, fx), min(y0, fy)
        w, h = abs(fx - x0), abs(fy - y0)
        side = self.goal_pick_side

        if w < 10 or h < 10:
            messagebox.showwarning("골대 지정", "너무 작게 선택했습니다. 다시 드래그해 주세요.")
        else:
            self.manual_goal_rects[side] = (x, y, w, h)
            self.goal_armed[side] = True
            label = "AI" if side == 'ai' else "Player"
            messagebox.showinfo("골대 지정 완료", f"{label} 골대 위치가 저장되었습니다.")

        btn = self.btn_set_ai_goal if side == 'ai' else self.btn_set_player_goal
        btn.config(text=("AI골대" if side == 'ai' else "P골대"), bg=self.button_color)
        self.goal_pick_side = None
        self.goal_drag_start = None
        self.goal_drag_current = None

    def start_goal_pick(self, side):
        self.goal_pick_side = side
        self.goal_drag_start = None
        self.goal_drag_current = None
        btn = self.btn_set_ai_goal if side == 'ai' else self.btn_set_player_goal
        btn.config(text="드래그...", bg="orange")

    def reset_goal_zones(self):
        self.manual_goal_rects = {'ai': None, 'player': None}
        self.goal_armed = {'ai': True, 'player': True}
        messagebox.showinfo("골대 위치 초기화", "골대 위치가 초기화되어 다시 색상(빨강/파랑) 자동 인식을 사용합니다.")

    def _calibrate_ball_at(self, fx, fy):
        if self.current_hsv is None:
            return
        orig_h, orig_w = self.orig_frame_shape
        fx = max(5, min(orig_w - 6, fx))
        fy = max(5, min(orig_h - 6, fy))

        patch = self.current_hsv[fy - 5:fy + 5, fx - 5:fx + 5].reshape(-1, 3)
        h_mean, s_mean, v_mean = patch.mean(axis=0)
        h_std, s_std, v_std = patch.std(axis=0)

        h_margin = max(8, h_std * 2.5)
        s_margin = max(50, s_std * 2.5)
        v_margin = max(50, v_std * 2.5)

        self.ball_lower = np.array([
            max(0, h_mean - h_margin),
            max(0, s_mean - s_margin),
            max(0, v_mean - v_margin)
        ])
        self.ball_upper = np.array([
            min(179, h_mean + h_margin),
            255,
            255
        ])
        self.ball_ema = None
        self.ball_lost_count = 0

        self.calibrating = False
        self.btn_calibrate.config(text="공 색상 보정 (영상 클릭)", bg=self.button_color)
        messagebox.showinfo(
            "색상 보정 완료",
            f"새 HSV 범위로 갱신되었습니다.\nLower {self.ball_lower.astype(int)}\nUpper {self.ball_upper.astype(int)}"
        )

    def check_status(self):
        hw_status = "✅ 정상" if (self.h1 and self.h2) else "❌ 실패"
        if hw_status == "✅ 정상":
            self.h1.buzzer(1000); wait(100); self.h1.buzzer(0)
            self.h2.buzzer(1000); wait(100); self.h2.buzzer(0)

        b_st = "✅" if self.detected_status['ball'] else "❌"
        r1_st = "✅" if self.detected_status['r1'] else f"❌ (ID {self.robot_marker_ids['r1']} 마커)"
        r2_st = "✅" if self.detected_status['r2'] else f"❌ (ID {self.robot_marker_ids['r2']} 마커)"

        msg = f"[ 하드웨어 통신 ]\n햄스터봇: {hw_status}\n\n[ 추적 상태 ]\n축구공(노랑): {b_st}\n로봇 1번: {r1_st}\n로봇 2번: {r2_st}"
        messagebox.showinfo("시스템 점검", msg)

    def reconnect_camera(self):
        try:
            self.cap.release()
        except Exception:
            pass
        self.cap = cv2.VideoCapture(self.camera_url, cv2.CAP_FFMPEG)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
        self.camera_fail_count = 0
        self.detected_status['camera'] = self.cap.isOpened()
        self.update_status_indicators()
        if self.detected_status['camera']:
            messagebox.showinfo("카메라", "카메라에 다시 연결되었습니다.")
        else:
            messagebox.showerror("카메라", "카메라 연결에 실패했습니다. 카메라 전원/네트워크 상태를 확인해 주세요.")

    def toggle_play(self):
        if self.remaining_seconds <= 0:
            messagebox.showwarning("안내", "시간을 먼저 설정해 주세요.")
            return

        self.is_playing = not self.is_playing
        if self.is_playing:
            self.btn_start.config(text="정지", bg="red")
            self.countdown()
        else:
            self.btn_start.config(text="시작", bg=self.button_color)
            if self.timer_id: self.root.after_cancel(self.timer_id)
            if self.h1: self.h1.stop()
            if self.h2: self.h2.stop()

    def countdown(self):
        if self.is_playing and self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            self.update_timer_display()
            self.timer_id = self.root.after(1000, self.countdown)
        elif self.remaining_seconds <= 0:
            self.is_playing = False
            self.btn_start.config(text="시작", bg=self.button_color)
            if self.h1: self.h1.stop()
            if self.h2: self.h2.stop()
            messagebox.showinfo("경기 종료", "경기 시간이 끝났습니다!")

    def move_robot_to_target(self, robot, rx, ry, rangle, tx, ty, is_attacker=True):
        dx = tx - rx
        dy = ty - ry

        target_angle = math.degrees(math.atan2(dy, dx))
        angle_diff = target_angle - rangle

        while angle_diff > 180: angle_diff -= 360
        while angle_diff < -180: angle_diff += 360

        speed = self.base_speed if is_attacker else int(self.base_speed * 0.7)

        if abs(angle_diff) > 30:
            turn_speed = int(angle_diff * 0.5)
            # 만약 로봇이 제자리에서 반대 방향으로 돈다면 아래의 turn_speed 와 -turn_speed 를 맞바꾸세요.
            left_wheel = max(-100, min(100, turn_speed))
            right_wheel = max(-100, min(100, -turn_speed))
            robot.wheels(left_wheel, right_wheel)
        else:
            fine_turn = int(angle_diff * 0.3)
            left_wheel = max(-100, min(100, speed + fine_turn))
            right_wheel = max(-100, min(100, speed - fine_turn))
            robot.wheels(left_wheel, right_wheel)

    def _attacker_target(self, rx, ry, ball_x, ball_y, goal_center):
        """공격 로봇이 실제로 향해야 할 좌표를 계산.

        공만 보고 바로 돌진하면 로봇이 어느 방향에서 접근했느냐에 따라 우연히
        자기 골대 쪽으로 공을 밀어버릴 수 있다. 이를 막기 위해 "공 - 상대 골대"
        연장선에서 공 뒤쪽 지점을 먼저 목표로 삼아 로봇이 골대 반대편으로
        돌아가게 하고, 이미 그 지점 근처(공을 사이에 두고 골대 반대편)에
        있을 때만 공을 직접 향해 밀어붙인다. 골대 위치를 모르면(색상/드래그
        지정이 모두 없는 경우) 예전처럼 공만 바로 쫓아간다.
        """
        if goal_center is None:
            return ball_x, ball_y

        gx, gy = goal_center
        dx, dy = ball_x - gx, ball_y - gy
        dist = math.hypot(dx, dy)
        if dist < 1e-3:
            return ball_x, ball_y

        behind_x = ball_x + dx / dist * self.attack_behind_offset
        behind_y = ball_y + dy / dist * self.attack_behind_offset

        if math.hypot(rx - behind_x, ry - behind_y) < self.attack_align_threshold:
            return ball_x, ball_y
        return behind_x, behind_y

    def detect_ball(self, frame):
        """노란 공을 찾아 (x, y)를 반환. 못 찾으면 (-1, -1).

        원본 대비 개선점:
        - CLAHE로 밝기(V)만 평준화해 조명 변화에 덜 민감하게 함
        - open(erode->dilate)으로 잡티 제거 후 close(dilate->erode)로 공 내부 구멍을 메움
          (원본은 dilate를 먼저 해서 잡티까지 같이 부풀렸음)
        - 면적 + 원형도(circularity) 기준으로 후보를 걸러 옷/바닥 반사 같은 오탐을 줄임
        - 지수이동평균(EMA)으로 좌표를 매끄럽게 하고, 잠깐 놓쳐도 몇 프레임은 직전 위치를 유지
        """
        blurred = cv2.GaussianBlur(frame, (5, 5), 0)
        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)
        v = self.clahe.apply(v)
        hsv = cv2.merge((h, s, v))
        self.current_hsv = hsv

        mask = cv2.inRange(hsv, self.ball_lower, self.ball_upper)
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        best_contour = None
        best_area = -1
        MIN_BALL_AREA = 40
        MIN_CIRCULARITY = 0.55
        for c in contours:
            area = cv2.contourArea(c)
            if area < MIN_BALL_AREA:
                continue
            perimeter = cv2.arcLength(c, True)
            if perimeter <= 0:
                continue
            circularity = 4 * math.pi * area / (perimeter ** 2)
            if circularity < MIN_CIRCULARITY:
                continue
            if area > best_area:
                best_area = area
                best_contour = c

        raw_detected = False
        raw_x, raw_y, radius = -1, -1, 0
        if best_contour is not None:
            ((bx, by), radius) = cv2.minEnclosingCircle(best_contour)
            if radius > 4:
                raw_x, raw_y = bx, by
                raw_detected = True

        self.detected_status['ball'] = raw_detected

        if raw_detected:
            if self.ball_ema is None:
                self.ball_ema = (raw_x, raw_y)
            else:
                ex, ey = self.ball_ema
                a = self.ball_ema_alpha
                self.ball_ema = (a * raw_x + (1 - a) * ex, a * raw_y + (1 - a) * ey)
            self.ball_lost_count = 0
            return int(self.ball_ema[0]), int(self.ball_ema[1]), int(radius), True
        else:
            self.ball_lost_count += 1
            if self.ball_ema is not None and self.ball_lost_count <= self.max_lost_frames:
                return int(self.ball_ema[0]), int(self.ball_ema[1]), 8, False
            self.ball_ema = None
            return -1, -1, 0, False

    def _largest_zone_rect(self, mask):
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        best, best_area = None, self.min_goal_area
        for c in contours:
            area = cv2.contourArea(c)
            if area > best_area:
                best_area = area
                best = c
        return cv2.boundingRect(best) if best is not None else None

    def detect_goal_zones(self, frame):
        """AI 골대(빨강)와 플레이어 골대(파랑)의 사각형 범위를 찾아 화면에 표시.

        영상에서 드래그로 직접 지정한 골대(self.manual_goal_rects)가 있으면 그 고정된
        위치를 그대로 쓰고, 지정하지 않은 골대만 색상(빨강/파랑) 자동 인식으로 찾는다.
        """
        ai_rect = self.manual_goal_rects['ai']
        player_rect = self.manual_goal_rects['player']

        if ai_rect is None or player_rect is None:
            hsv = self.current_hsv if self.current_hsv is not None else cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

            kernel = np.ones((7, 7), np.uint8)
            if ai_rect is None:
                red_mask = cv2.bitwise_or(
                    cv2.inRange(hsv, self.goal_ai_lower1, self.goal_ai_upper1),
                    cv2.inRange(hsv, self.goal_ai_lower2, self.goal_ai_upper2),
                )
                red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, kernel)
                ai_rect = self._largest_zone_rect(red_mask)
            if player_rect is None:
                blue_mask = cv2.inRange(hsv, self.goal_player_lower, self.goal_player_upper)
                blue_mask = cv2.morphologyEx(blue_mask, cv2.MORPH_OPEN, kernel)
                player_rect = self._largest_zone_rect(blue_mask)

        if ai_rect:
            x, y, w, h = ai_rect
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
            cv2.putText(frame, "AI GOAL", (x, max(20, y - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        if player_rect:
            x, y, w, h = player_rect
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 120, 0), 2)
            cv2.putText(frame, "PLAYER GOAL", (x, max(20, y - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 120, 0), 2)

        # 드래그로 영역을 지정하는 중이면 실시간 미리보기 사각형을 그림
        if self.goal_pick_side and self.goal_drag_start and self.goal_drag_current:
            x0, y0 = self.goal_drag_start
            x1, y1 = self.goal_drag_current
            preview_color = (0, 0, 255) if self.goal_pick_side == 'ai' else (255, 120, 0)
            cv2.rectangle(frame, (x0, y0), (x1, y1), preview_color, 2)

        return ai_rect, player_rect

    @staticmethod
    def _point_in_rect(x, y, rect):
        rx, ry, rw, rh = rect
        return rx <= x <= rx + rw and ry <= y <= ry + rh

    def check_goal(self, ball_x, ball_y, ai_rect, player_rect):
        """공이 골대 영역에 들어오면 점수를 올림.

        시간이 아니라 "골대 밖으로 나갔다가 다시 들어오는지"로 중복 득점을 막는다:
        한 번 득점하면 그 골대는 잠기고(goal_armed=False), 공이 그 골대 영역을
        완전히 벗어나야 다시 잠금이 풀려서 재득점이 가능해진다.
        """
        now = time.time()
        in_ai = bool(ai_rect and self._point_in_rect(ball_x, ball_y, ai_rect))
        in_player = bool(player_rect and self._point_in_rect(ball_x, ball_y, player_rect))

        if not in_ai:
            self.goal_armed['ai'] = True
        if not in_player:
            self.goal_armed['player'] = True

        scored_side = None
        if in_ai and self.goal_armed['ai']:
            # 공이 AI 골대 안으로 들어감 -> 상대인 Player 득점
            scored_side = 'player'
            self.goal_armed['ai'] = False
        elif in_player and self.goal_armed['player']:
            # 공이 플레이어 골대 안으로 들어감 -> AI 득점
            # 득점이 반대로 올라가는 것 같으면 위 두 분기의 'player'/'ai' 를 서로 바꾸세요.
            scored_side = 'ai'
            self.goal_armed['player'] = False

        if scored_side:
            self.score[scored_side] += 1
            self.update_score_display()
            self.goal_pause_until = now + 2.0
            self.goal_flash_until = now + 1.5
            self.goal_flash_text = "AI GOAL!" if scored_side == 'ai' else "PLAYER GOAL!"
            if self.h1: self.h1.wheels(0, 0)
            if self.h2: self.h2.wheels(0, 0)

    def _show_camera_error_frame(self):
        h, w = self.orig_frame_shape if self.orig_frame_shape[0] else (450, 800)
        blank = np.full((h, w, 3), 40, dtype=np.uint8)
        cv2.putText(blank, "카메라 연결 끊김", (w // 2 - 150, h // 2 - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)
        cv2.putText(blank, "'카메라 재연결' 버튼을 눌러주세요", (w // 2 - 220, h // 2 + 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        win_w = self.video_label.winfo_width()
        win_h = self.video_label.winfo_height()
        disp = (win_w, win_h) if (win_w > 50 and win_h > 50) else (800, 450)
        rgb_image = cv2.cvtColor(blank, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb_image).resize(disp, Image.LANCZOS)
        imgtk = ImageTk.PhotoImage(image=pil_image)
        self.video_label.imgtk = imgtk
        self.video_label.configure(image=imgtk)

    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            self.camera_fail_count += 1
            if self.camera_fail_count >= self.camera_fail_limit and self.detected_status['camera']:
                self.detected_status['camera'] = False
                self.update_status_indicators()
                if self.is_playing:
                    if self.h1: self.h1.wheels(0, 0)
                    if self.h2: self.h2.wheels(0, 0)
            self._show_camera_error_frame()
            self.root.after(15, self.update_frame)
            return

        self.camera_fail_count = 0
        if not self.detected_status['camera']:
            self.detected_status['camera'] = True
            self.update_status_indicators()

        if ret:
            # 1. 공 인식 (색상 보정 클릭을 위해 self.current_hsv 도 함께 갱신됨)
            ball_x, ball_y, ball_radius, ball_fresh = self.detect_ball(frame)
            if ball_x != -1:
                color = (0, 255, 255) if ball_fresh else (0, 165, 255)
                cv2.circle(frame, (ball_x, ball_y), max(ball_radius, 6), color, 2)

            # 2. 마커 인식
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if self.is_new_cv2:
                corners, ids, rejected = self.aruco_detector.detectMarkers(gray)
            else:
                corners, ids, rejected = aruco.detectMarkers(gray, self.aruco_dict, parameters=self.aruco_params)

            r1_data, r2_data = None, None
            self.detected_status['r1'] = False
            self.detected_status['r2'] = False

            debug_on = self.show_debug.get()

            if ids is not None:
                if debug_on:
                    # 디버그용: 이번 프레임에 실제로 잡힌 마커 ID 전체를 화면에 표시.
                    # "마커가 인식이 안 된다"는 문제를 (a) 아예 안 잡히는 경우와
                    # (b) 다른 ID로 잡히는 경우(마커 인쇄/딕셔너리 불일치)로 구분하는 데 사용.
                    detected_ids = sorted(int(v) for v in ids.flatten())
                    cv2.putText(frame, f"Detected marker IDs: {detected_ids}", (30, 80),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

                for i, marker_id in enumerate(ids.flatten()):
                    c = corners[i][0]
                    cx = int(np.mean(c[:, 0]))
                    cy = int(np.mean(c[:, 1]))

                    front_x = (c[0][0] + c[1][0]) / 2.0
                    front_y = (c[0][1] + c[1][1]) / 2.0

                    angle = math.degrees(math.atan2(front_y - cy, front_x - cx))

                    cv2.polylines(frame, [c.astype(np.int32)], True, (0, 255, 0), 2)
                    cv2.arrowedLine(frame, (cx, cy), (int(front_x), int(front_y)), (0, 0, 255), 3, tipLength=0.3)
                    if debug_on:
                        cv2.putText(frame, f"ID:{int(marker_id)}", (cx - 15, cy + 35),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 2)

                    if marker_id == self.robot_marker_ids['r1']:
                        r1_data = (cx, cy, angle)
                        self.detected_status['r1'] = True
                        cv2.putText(frame, f"R1 (ID{self.robot_marker_ids['r1']})", (cx-20, cy-20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,255), 2)
                    elif marker_id == self.robot_marker_ids['r2']:
                        r2_data = (cx, cy, angle)
                        self.detected_status['r2'] = True
                        cv2.putText(frame, f"R2 (ID{self.robot_marker_ids['r2']})", (cx-20, cy-20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)
            elif debug_on:
                cv2.putText(frame, "NO ARUCO MARKERS DETECTED", (30, 80),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            self.update_status_indicators()

            # 3. 골대 인식 + 자동 득점 (빨강=AI 골대, 파랑=플레이어 골대)
            ai_goal_rect, player_goal_rect = self.detect_goal_zones(frame)
            if self.is_playing and ball_x != -1:
                self.check_goal(ball_x, ball_y, ai_goal_rect, player_goal_rect)

            # 공격 목표(상대인 Player 골대 중심)와 수비 복귀 지점(자기 골대 중심)
            player_goal_center = None
            if player_goal_rect:
                gx, gy, gw, gh = player_goal_rect
                player_goal_center = (gx + gw / 2, gy + gh / 2)
            if ai_goal_rect:
                gx, gy, gw, gh = ai_goal_rect
                defend_point = (gx + gw / 2, gy + gh / 2)
            else:
                defend_point = (280, 360)

            in_goal_pause = time.time() < self.goal_pause_until

            # --- 자율 주행 실행부 ---
            if self.is_playing and in_goal_pause:
                if self.h1: self.h1.wheels(0, 0)
                if self.h2: self.h2.wheels(0, 0)
            elif self.is_playing:
                current_mode = self.active_mode.get()

                # 선택되지 않은 로봇은 강제 정지
                if current_mode == "r1" and self.h2: self.h2.wheels(0, 0)
                if current_mode == "r2" and self.h1: self.h1.wheels(0, 0)

                if ball_x != -1:
                    # 1번 로봇만 동작 모드
                    if current_mode == "r1" and r1_data:
                        atk_x, atk_y = self._attacker_target(r1_data[0], r1_data[1], ball_x, ball_y, player_goal_center)
                        self.move_robot_to_target(self.h1, r1_data[0], r1_data[1], r1_data[2], atk_x, atk_y, is_attacker=True)
                        cv2.line(frame, (int(r1_data[0]), int(r1_data[1])), (ball_x, ball_y), (255, 255, 0), 1, cv2.LINE_AA)

                    # 2번 로봇만 동작 모드
                    elif current_mode == "r2" and r2_data:
                        atk_x, atk_y = self._attacker_target(r2_data[0], r2_data[1], ball_x, ball_y, player_goal_center)
                        self.move_robot_to_target(self.h2, r2_data[0], r2_data[1], r2_data[2], atk_x, atk_y, is_attacker=True)
                        cv2.line(frame, (int(r2_data[0]), int(r2_data[1])), (ball_x, ball_y), (255, 255, 0), 1, cv2.LINE_AA)

                    # 두 대 모두 동작 모드
                    elif current_mode == "both":
                        if r1_data and r2_data:
                            dist1 = math.sqrt((r1_data[0] - ball_x)**2 + (r1_data[1] - ball_y)**2)
                            dist2 = math.sqrt((r2_data[0] - ball_x)**2 + (r2_data[1] - ball_y)**2)

                            if dist1 < dist2:
                                atk_x, atk_y = self._attacker_target(r1_data[0], r1_data[1], ball_x, ball_y, player_goal_center)
                                self.move_robot_to_target(self.h1, r1_data[0], r1_data[1], r1_data[2], atk_x, atk_y, is_attacker=True)
                                self.move_robot_to_target(self.h2, r2_data[0], r2_data[1], r2_data[2], defend_point[0], defend_point[1], is_attacker=False)
                                cv2.line(frame, (int(r1_data[0]), int(r1_data[1])), (ball_x, ball_y), (255, 255, 0), 1, cv2.LINE_AA)
                            else:
                                atk_x, atk_y = self._attacker_target(r2_data[0], r2_data[1], ball_x, ball_y, player_goal_center)
                                self.move_robot_to_target(self.h2, r2_data[0], r2_data[1], r2_data[2], atk_x, atk_y, is_attacker=True)
                                self.move_robot_to_target(self.h1, r1_data[0], r1_data[1], r1_data[2], defend_point[0], defend_point[1], is_attacker=False)
                                cv2.line(frame, (int(r2_data[0]), int(r2_data[1])), (ball_x, ball_y), (255, 255, 0), 1, cv2.LINE_AA)
                        elif r1_data:
                            atk_x, atk_y = self._attacker_target(r1_data[0], r1_data[1], ball_x, ball_y, player_goal_center)
                            self.move_robot_to_target(self.h1, r1_data[0], r1_data[1], r1_data[2], atk_x, atk_y, is_attacker=True)
                            cv2.line(frame, (int(r1_data[0]), int(r1_data[1])), (ball_x, ball_y), (255, 255, 0), 1, cv2.LINE_AA)
                            if self.h2: self.h2.wheels(0, 0)
                        elif r2_data:
                            atk_x, atk_y = self._attacker_target(r2_data[0], r2_data[1], ball_x, ball_y, player_goal_center)
                            self.move_robot_to_target(self.h2, r2_data[0], r2_data[1], r2_data[2], atk_x, atk_y, is_attacker=True)
                            cv2.line(frame, (int(r2_data[0]), int(r2_data[1])), (ball_x, ball_y), (255, 255, 0), 1, cv2.LINE_AA)
                            if self.h1: self.h1.wheels(0, 0)
                else:
                    cv2.putText(frame, "BALL NOT DETECTED - ROBOTS STOPPED", (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 3)
                    if self.h1: self.h1.wheels(0, 0)
                    if self.h2: self.h2.wheels(0, 0)

            elif not self.detected_status['ball']:
                cv2.putText(frame, "FINDING YELLOW BALL...", (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,255), 3)

            if time.time() < self.goal_flash_until and self.goal_flash_text:
                text_size = cv2.getTextSize(self.goal_flash_text, cv2.FONT_HERSHEY_SIMPLEX, 1.6, 4)[0]
                tx = max(10, (frame.shape[1] - text_size[0]) // 2)
                cv2.putText(frame, self.goal_flash_text, (tx, 130),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.6, (0, 255, 255), 4)

            win_w = self.video_label.winfo_width()
            win_h = self.video_label.winfo_height()

            self.orig_frame_shape = frame.shape[:2]
            self.disp_size = (win_w, win_h) if (win_w > 50 and win_h > 50) else (800, 450)

            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            if win_w > 50 and win_h > 50:
                pil_image = Image.fromarray(rgb_image).resize((win_w, win_h), Image.LANCZOS)
            else:
                pil_image = Image.fromarray(rgb_image).resize((800, 450), Image.LANCZOS)

            imgtk = ImageTk.PhotoImage(image=pil_image)
            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)

        self.root.after(15, self.update_frame)

    def on_closing(self):
        self.is_playing = False
        try:
            if self.h1: self.h1.stop()
            if self.h2: self.h2.stop()
            wait(100)
        except: pass
        self.cap.release()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = HamsterSoccerApp(root)
    root.mainloop()
