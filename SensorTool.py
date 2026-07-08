import sys
import serial
import serial.tools.list_ports
import csv
import time
from datetime import datetime
import socket


def findport():
    """
    Scan serial ports and return the device path for the PDC2_422 interface.

    Identifies the PDC2 by USB vendor:product ID 0403:6010 (FTDI dual-channel).
    On Linux the ftdi_sio driver strips the A/B suffix from serial numbers, so
    the RS-422 channel (B/interface 1) is matched via port.location ending in
    ':1.1'. On other platforms port.serial_number[-1] == 'B' is used instead.

    Returns:
        str | None: Device path (e.g. '/dev/ttyUSB1', 'COM4') or None if not found.
    """
    print("Looking for USB with serial number 0403:6010 and setting loc 1.1 as comport")
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if "0403:6010" in port.hwid:
            if sys.platform.startswith("linux"):
                loc = port.location or ""
                if loc.endswith(":1.1"):
                    return port.device
            else:
                if port.serial_number and port.serial_number[-1] == "B":
                    return port.device
    print("No fitting device found")
    return None

class SensorTool():
    """
    Reads data from an FTS sensor over serial and outputs it to a selected sink.

    Output modes:
        fts_print()         -- print parsed fields to the terminal
        fts_to_csv()        -- write fields to a CSV file
        fts_to_udp()        -- stream comma-separated fields over UDP
        fts_gui()           -- live plot in a PySide6/pyqtgraph window

    Args:
        port (str):             Serial port the sensor is connected to. Default: auto (detect PDC2_422 automatically via script)
        timestamps (bool):      Request timestamps from the sensor. Default: True
        auto_calibrate (bool):  Send a calibration command on startup. Default: True
    
    Hardware documentation:
        https://kb.seedrobotics.com/doku.php?id=fts:fts3_pressuresensor

    Usage examples:
        python3 SensorTool.py              # no args -> GUI (double-click friendly)
        python3 SensorTool.py print
        python3 SensorTool.py csv --port /dev/ttyUSB0
        python3 SensorTool.py udp --udp-ip 192.168.1.10 --udp-port 6000
        python3 SensorTool.py csv --no-timestamps --no-calibrate
        python3 SensorTool.py gui 
        
    Run with -h to see all options:
        python3 SensorTool.py -h
    
    """

    def __init__(self, port = "auto", timestamps = True, auto_calibrate = True):
        """
        Args:
            port (str): Serial port to use, or "auto" to detect the PDC2_422 automatically.
            timestamps (bool): If True, requests hardware timestamps from the sensor.
            auto_calibrate (bool): If True, sends a calibration command on startup.
        """
        if port == "auto":
            self.com_port = findport()
            print(f"Auto detected: {self.com_port}")
        else:
            self.com_port = port  # Windows: "COM3"
        self.timestamps = timestamps
        self.auto_calibrate = auto_calibrate
        self.baud = 1000000

    def fts_print(self):
        """Read sensor data from serial and print each parsed sample to stdout."""
        #Open the serial port
        with serial.Serial(self.com_port, self.baud, timeout=1) as ser:
            if self.timestamps:
                ser.write("enabletime".encode("utf-8"))
                time.sleep(0.3)
                #align timestamp with unix time
                ser.write(f"setepoch,{time.time()},0".encode("utf-8"))
            else:
                ser.write("disabletime".encode("utf-8"))
            time.sleep(0.3)

            if self.auto_calibrate:
                ser.write("calibrate".encode("utf-8"))
            time.sleep(0.3)


            #Flush the input buffer so no stale data is read
            ser.reset_input_buffer()
            #Loop for ever
            while True:
                line = ser.readline()
                #If new data is there
                if line:
                    #print it, strip leading @ and \n
                    print(line.decode("utf-8", errors="replace").rstrip().split(",")[1:-1])

    def fts_to_csv(self, filename=None):
        """
        Read sensor data from serial and write it to a CSV file.

        Args:
            filename (str | None): Output file path. Defaults to a timestamped name
                                   like ``sensor_data_YYYY-MM-DD_HH-MM-SS.csv``.
        """
        if filename is None:
            filename = datetime.now().strftime("sensor_data_%Y-%m-%d_%H-%M-%S") + ".csv"
        with serial.Serial(self.com_port, self.baud, timeout=1) as ser, open(filename, "w", newline="") as csvfile:
            if self.timestamps:
                ser.write("enabletime".encode("utf-8"))
                time.sleep(0.3)
                #align timestamp with unix time
                ser.write(f"setepoch,{time.time()},0".encode("utf-8"))
            else:
                ser.write("disabletime".encode("utf-8"))
            time.sleep(0.3)
            
            if self.auto_calibrate:
                ser.write("calibrate".encode("utf-8"))
            time.sleep(0.3)

            writer = csv.writer(csvfile)
            #Create the title row
            if self.timestamps:
                writer.writerow(["Time: s", "Time: ms"] + [f"{a}{i}" for i in range(1, 6) for a in "xyz"])
            else:
                writer.writerow([f"{a}{i}" for i in range(1, 6) for a in "xyz"])

            #Flush the input buffer so no stale data is read
            ser.reset_input_buffer()
            print(f"Writing to CSV")

            while True:
                line = ser.readline()
                if line:
                    #Split the message into parts and strip the leading "@"
                    fields = line.decode("utf-8", errors="replace").rstrip().split(",")
                    writer.writerow(fields[1:-1])


    def fts_to_udp(self, udp_ip = "127.0.0.1", udp_port = 5005):
        """
        Read sensor data from serial and stream each sample as a comma-separated UDP datagram.

        Args:
            udp_ip (str): Destination IP address. Default: ``"127.0.0.1"``.
            udp_port (int): Destination UDP port. Default: ``5005``.
        """
        with serial.Serial(self.com_port, self.baud, timeout=1) as ser, socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            if self.timestamps:
                ser.write("enabletime".encode("utf-8"))
                time.sleep(0.3)
                #align timestamp with unix time
                ser.write(f"setepoch,{time.time()},0".encode("utf-8"))
            else:
                ser.write("disabletime".encode("utf-8"))
            time.sleep(0.3)
            
            if self.auto_calibrate:
                ser.write("calibrate".encode("utf-8"))
            time.sleep(0.3)

            print(f"Streaming to UDP {udp_ip}:{udp_port}...")
            #Flush the input buffer so no stale data is read
            ser.reset_input_buffer()

            while True:
                line = ser.readline()
                if line:
                    fields = line.decode("utf-8", errors="replace").rstrip().split(",")
                    if fields != []:
                        payload = ",".join(fields[1:-1])
                        sock.sendto(payload.encode("utf-8"), (udp_ip, udp_port))


    def fts_gui(self):
        """
        Open a live PySide6/pyqtgraph window that plots all sensor axes in real time.

        The window opens even with no sensor attached: a reader thread keeps
        scanning for the device, auto-reconnects (with full re-init) if the
        connection drops, and reports its state in the control panel. A port
        dropdown allows manual selection if auto-detection fails, and a Record
        button writes incoming samples to a CSV file (same format as csv mode).
        """
        import sys
        import queue
        import threading
        from collections import deque
        from pathlib import Path
        from PySide6 import QtWidgets, QtCore
        import pyqtgraph as pg

        BUFFER_SIZE = 500
        NUM_SENSORS = 5
        AXES = ['x', 'y', 'z']
        MIN_Y_RANGE = 40.0  # auto-scale never shrinks the Y axis below this span
        SENSOR_COLORS = ['#e74c3c', '#2ecc71', '#3498db', '#f39c12', '#9b59b6']
        AXIS_STYLES = [
            QtCore.Qt.PenStyle.SolidLine,
            QtCore.Qt.PenStyle.DashLine,
            QtCore.Qt.PenStyle.DotLine,
        ]

        # With timestamps the first two fields are T1/T2, so sensor data starts at index 2
        offset = 2 if self.timestamps else 0

        data_queue = queue.Queue(maxsize=2000)
        status_queue = queue.Queue()
        record_queue = queue.Queue()
        stop_event = threading.Event()
        calibrate_event = threading.Event()
        reconnect_event = threading.Event()
        period_queue = queue.Queue(maxsize=1)
        # Shared with the reader thread; single-key dicts to allow closure writes
        port_selection = {'value': self.com_port or "auto"}
        current_period = {'value': 20}
        rec_state = {'rows': 0, 'error': None}

        def serial_reader():
            csvfile = None
            writer = None
            last_flush = 0.0

            def stop_recording():
                nonlocal csvfile, writer
                if csvfile:
                    csvfile.close()
                csvfile = None
                writer = None

            def start_recording(filename):
                nonlocal csvfile, writer
                stop_recording()
                try:
                    csvfile = open(filename, "w", newline="")
                except OSError as e:
                    rec_state['error'] = str(e)
                    return
                writer = csv.writer(csvfile)
                if self.timestamps:
                    writer.writerow(["Time: s", "Time: ms"] + [f"{a}{i}" for i in range(1, 6) for a in "xyz"])
                else:
                    writer.writerow([f"{a}{i}" for i in range(1, 6) for a in "xyz"])
                csvfile.flush()
                rec_state['rows'] = 0

            def handle_record_commands():
                while True:
                    try:
                        cmd = record_queue.get_nowait()
                    except queue.Empty:
                        return
                    if cmd[0] == "start":
                        start_recording(cmd[1])
                    else:
                        stop_recording()

            try:
                while not stop_event.is_set():
                    handle_record_commands()
                    reconnect_event.clear()
                    port = port_selection['value']
                    if port == "auto":
                        port = findport()
                    if port is None:
                        status_queue.put(("searching", None))
                        if stop_event.wait(1.0):
                            break
                        continue
                    try:
                        with serial.Serial(port, self.baud, timeout=1) as ser:
                            # Full init on every (re)connect: the sensor may have
                            # power-cycled and lost its epoch/period state.
                            if self.timestamps:
                                ser.write(b"enabletime")
                                time.sleep(0.3)
                                ser.write(f"setepoch,{time.time()},0".encode())
                            else:
                                ser.write(b"disabletime")
                            time.sleep(0.3)
                            if self.auto_calibrate:
                                ser.write(b"calibrate")
                            time.sleep(0.3)
                            ser.write(f"setperiod,{current_period['value']}".encode())
                            time.sleep(0.3)
                            ser.reset_input_buffer()
                            status_queue.put(("connected", port))
                            last_data = time.monotonic()
                            while not stop_event.is_set():
                                handle_record_commands()
                                if reconnect_event.is_set():
                                    raise serial.SerialException("port changed by user")
                                if calibrate_event.is_set():
                                    ser.write(b"calibrate")
                                    calibrate_event.clear()
                                try:
                                    period_val = period_queue.get_nowait()
                                    ser.write(f"setperiod,{period_val}".encode())
                                except queue.Empty:
                                    pass
                                line = ser.readline()
                                now = time.monotonic()
                                if line:
                                    last_data = now
                                    fields = line.decode("utf-8", errors="replace").rstrip().split(",")[1:-1]
                                    if writer:
                                        writer.writerow(fields)
                                        rec_state['rows'] += 1
                                        if now - last_flush > 1.0:
                                            csvfile.flush()
                                            last_flush = now
                                    try:
                                        data_queue.put_nowait([float(v) for v in fields])
                                    except (ValueError, queue.Full):
                                        pass
                                elif now - last_data > 3.0:
                                    # Unplugging doesn't always raise on Windows; a port
                                    # silent past the max sample period means the link died.
                                    raise serial.SerialException("no data for 3 s")
                    except (serial.SerialException, OSError):
                        status_queue.put(("lost", None))
                        if stop_event.wait(1.0):
                            break
            finally:
                stop_recording()

        buffers = [
            [deque([0.0] * BUFFER_SIZE, maxlen=BUFFER_SIZE) for _ in AXES]
            for _ in range(NUM_SENSORS)
        ]

        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

        win = QtWidgets.QWidget()
        win.setWindowTitle("FTS Sensor Monitor")
        win.resize(1200, 650)

        main_layout = QtWidgets.QHBoxLayout(win)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # Left control panel
        ctrl_panel = QtWidgets.QFrame()
        ctrl_panel.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        ctrl_panel.setFixedWidth(155)
        ctrl_layout = QtWidgets.QVBoxLayout(ctrl_panel)
        ctrl_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        ctrl_layout.setSpacing(6)

        ctrl_layout.addWidget(QtWidgets.QLabel("Port"))

        def refresh_ports():
            desired = port_selection['value']
            port_combo.blockSignals(True)
            port_combo.clear()
            port_combo.addItem("Auto", "auto")
            for p in serial.tools.list_ports.comports():
                port_combo.addItem(p.device, p.device)
            if desired != "auto" and port_combo.findData(desired) < 0:
                port_combo.addItem(desired, desired)
            port_combo.setCurrentIndex(max(port_combo.findData(desired), 0))
            port_combo.blockSignals(False)

        class _PortCombo(QtWidgets.QComboBox):
            def showPopup(self):
                refresh_ports()
                super().showPopup()

        port_combo = _PortCombo()
        refresh_ports()

        def on_port_changed(index):
            port_selection['value'] = port_combo.itemData(index)
            reconnect_event.set()

        port_combo.currentIndexChanged.connect(on_port_changed)
        ctrl_layout.addWidget(port_combo)

        status_label = QtWidgets.QLabel("Searching for sensor…")
        status_label.setWordWrap(True)
        status_label.setStyleSheet("color: #f39c12; font-weight: bold;")
        ctrl_layout.addWidget(status_label)

        fps_label = QtWidgets.QLabel("FPS: --")
        fps_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        #ctrl_layout.addWidget(fps_label)

        calibrate_btn = QtWidgets.QPushButton("Calibrate")
        calibrate_btn.setStyleSheet("QPushButton { padding: 4px; }")
        calibrate_btn.clicked.connect(calibrate_event.set)
        ctrl_layout.addWidget(calibrate_btn)

        record_btn = QtWidgets.QPushButton("⏺ Record CSV")
        record_btn.setCheckable(True)
        record_btn.setStyleSheet("QPushButton { padding: 4px; }")
        rec_ui = {'started': None}

        def on_record_toggled(checked):
            if checked:
                docs = Path.home() / "Documents"
                base = docs if docs.is_dir() else Path.home()
                default = str(base / datetime.now().strftime("sensor_data_%Y-%m-%d_%H-%M-%S.csv"))
                filename, _ = QtWidgets.QFileDialog.getSaveFileName(
                    win, "Save sensor recording", default, "CSV files (*.csv)")
                if not filename:
                    record_btn.setChecked(False)
                    return
                record_queue.put(("start", filename))
                rec_ui['started'] = time.monotonic()
            else:
                record_queue.put(("stop",))
                rec_ui['started'] = None
                record_btn.setText("⏺ Record CSV")

        record_btn.toggled.connect(on_record_toggled)
        ctrl_layout.addWidget(record_btn)

        ctrl_layout.addWidget(QtWidgets.QLabel("Period (ms)"))
        period_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        period_slider.setRange(20, 1000)
        period_slider.setValue(20)
        #ctrl_layout.addWidget(period_slider)
        period_label = QtWidgets.QLabel("20")
        period_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        #ctrl_layout.addWidget(period_label)

        def on_period_changed(val):
            period_label.setText(str(val))
            current_period['value'] = val  # re-sent by the reader on reconnect
            try:
                period_queue.get_nowait()
            except queue.Empty:
                pass
            period_queue.put_nowait(val)

        period_slider.valueChanged.connect(on_period_changed)

        ctrl_layout.addSpacing(6)
        ctrl_layout.addWidget(QtWidgets.QLabel("<b>Sensors</b>"))

        sensor_axis_checks = []
        sensor_master_checks = []
        for s in range(NUM_SENSORS):
            row_widget = QtWidgets.QWidget()
            row_layout = QtWidgets.QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(4)

            master_cb = QtWidgets.QCheckBox()
            master_cb.setChecked(True)
            master_cb.setToolTip(f"Enable / disable all axes for Sensor {s + 1}")
            row_layout.addWidget(master_cb)
            sensor_master_checks.append(master_cb)

            btn = QtWidgets.QPushButton(f"▶  Sensor {s + 1}")
            btn.setCheckable(True)
            btn.setStyleSheet(
                f"QPushButton {{ color: {SENSOR_COLORS[s]}; font-weight: bold; "
                f"text-align: left; border: none; padding: 2px 0px; }}"
            )
            row_layout.addWidget(btn, stretch=1)
            ctrl_layout.addWidget(row_widget)

            axis_widget = QtWidgets.QWidget()
            axis_layout = QtWidgets.QVBoxLayout(axis_widget)
            axis_layout.setContentsMargins(14, 0, 0, 0)
            axis_layout.setSpacing(1)
            axis_widget.setVisible(False)
            ctrl_layout.addWidget(axis_widget)

            axis_cbs = []
            for axis_name in AXES:
                cb = QtWidgets.QCheckBox(axis_name)
                cb.setChecked(True)
                axis_layout.addWidget(cb)
                axis_cbs.append(cb)

            sensor_axis_checks.append(axis_cbs)

            def _make_toggle(b, aw, idx):
                def _toggle(checked):
                    aw.setVisible(checked)
                    b.setText(f"{'▼' if checked else '▶'}  Sensor {idx + 1}")
                return _toggle

            btn.toggled.connect(_make_toggle(btn, axis_widget, s))

        ctrl_layout.addSpacing(12)
        ctrl_layout.addWidget(QtWidgets.QLabel("<b>Axes</b>"))
        ctrl_layout.addWidget(QtWidgets.QLabel("— x\n‒‒ y\n··· z"))
        ctrl_layout.addStretch()

        main_layout.addWidget(ctrl_panel)

        # Right plot
        pg.setConfigOptions(antialias=True)
        plot_widget = pg.PlotWidget()
        plot_widget.setBackground('w')
        plot_widget.setMouseEnabled(x=False, y=False)
        vb = plot_widget.getPlotItem().getViewBox()
        vb.setMenuEnabled(False)
        plot_widget.getPlotItem().hideButtons()
        vb.disableAutoRange(axis=vb.YAxis)
        vb.setYRange(-MIN_Y_RANGE / 2, MIN_Y_RANGE / 2, padding=0)
        plot_widget.showGrid(x=True, y=True, alpha=0.25)
        plot_widget.setLabel('left', 'Value')
        plot_widget.setLabel('bottom', 'Samples')
        main_layout.addWidget(plot_widget, stretch=1)

        curves = [
            [
                plot_widget.plot(
                    pen=pg.mkPen(color=SENSOR_COLORS[s], style=AXIS_STYLES[a], width=1.5),
                    clipToView=True,
                )
                for a in range(len(AXES))
            ]
            for s in range(NUM_SENSORS)
        ]
        import math
        import numpy as np
        import time as _time

        _frame_times = deque(maxlen=30)

        # Discrete Y scaling: only rescale at multiples of SCALE_STEP.
        # Expansion is immediate; shrinking waits SHRINK_FRAMES consecutive
        # frames where a smaller level would suffice (avoids flip-flopping).
        SCALE_STEP = MIN_Y_RANGE
        MIN_DISPLAY_SPAN = MIN_Y_RANGE  # hard floor — raise this to reduce lag at tight scales
        SHRINK_FRAMES = 20
        y_state = {'lo': -MIN_Y_RANGE / 2, 'hi': MIN_Y_RANGE / 2, 'shrink_count': 0}

        def _maybe_rescale(dmin, dmax):
            center = (dmin + dmax) / 2
            steps = math.ceil(max(dmax - dmin, SCALE_STEP) / SCALE_STEP)
            half = max(steps * SCALE_STEP / 2, MIN_DISPLAY_SPAN / 2)
            new_lo, new_hi = center - half, center + half
            cur_span = y_state['hi'] - y_state['lo']

            if dmin < y_state['lo'] or dmax > y_state['hi']:
                # data exceeded view — expand immediately
                y_state.update(lo=new_lo, hi=new_hi, shrink_count=0)
                vb.setYRange(new_lo, new_hi, padding=0)
            elif half * 2 < cur_span:
                # data fits a smaller level — wait for hysteresis before shrinking
                y_state['shrink_count'] += 1
                if y_state['shrink_count'] >= SHRINK_FRAMES:
                    y_state.update(lo=new_lo, hi=new_hi, shrink_count=0)
                    vb.setYRange(new_lo, new_hi, padding=0)
            else:
                y_state['shrink_count'] = 0

        def update():
            try:
                while True:
                    state, info = status_queue.get_nowait()
                    if state == "connected":
                        status_label.setText(f"Connected: {info}")
                        status_label.setStyleSheet("color: #2ecc71; font-weight: bold;")
                    elif state == "searching":
                        status_label.setText("Searching for sensor…")
                        status_label.setStyleSheet("color: #f39c12; font-weight: bold;")
                    else:
                        status_label.setText("Connection lost — reconnecting…")
                        status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
            except queue.Empty:
                pass

            if rec_state['error']:
                record_btn.setChecked(False)
                error_msg, rec_state['error'] = rec_state['error'], None
                QtWidgets.QMessageBox.warning(win, "Recording failed", error_msg)
            elif rec_ui['started'] is not None:
                elapsed = int(_time.monotonic() - rec_ui['started'])
                record_btn.setText(f"⏹ Stop ({elapsed // 60}:{elapsed % 60:02d})")
                #record_btn.setText(f"⏹ ({elapsed // 60}:{elapsed % 60:02d} · {rec_state['rows']} rows)")

            changed = False
            while True:
                try:
                    data = data_queue.get_nowait()
                    for s in range(NUM_SENSORS):
                        for a in range(len(AXES)):
                            idx = offset + s * 3 + a
                            if idx < len(data):
                                buffers[s][a].append(data[idx])
                    changed = True
                except queue.Empty:
                    break

            glb_min = float('inf')
            glb_max = float('-inf')
            for s in range(NUM_SENSORS):
                for a in range(len(AXES)):
                    visible = sensor_master_checks[s].isChecked() and sensor_axis_checks[s][a].isChecked()
                    curves[s][a].setVisible(visible)
                    if visible and changed:
                        arr = np.array(buffers[s][a])
                        curves[s][a].setData(arr)
                        a_min = float(arr.min())
                        a_max = float(arr.max())
                        if a_min < glb_min: glb_min = a_min
                        if a_max > glb_max: glb_max = a_max

            _frame_times.append(_time.monotonic())
            if len(_frame_times) >= 2:
                fps = (len(_frame_times) - 1) / (_frame_times[-1] - _frame_times[0])
                fps_label.setText(f"FPS: {fps:.1f}")

            if changed and glb_min != float('inf'):
                _maybe_rescale(glb_min, glb_max)

        timer = QtCore.QTimer()
        timer.timeout.connect(update)
        timer.start(50)  # 20 Hz refresh

        reader_thread = threading.Thread(target=serial_reader, daemon=True)
        reader_thread.start()

        win.show()
        try:
            app.exec()
        finally:
            stop_event.set()
            # let the reader finish its cycle and close any open recording
            reader_thread.join(timeout=3.0)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Seed robotics sensor data writer")
    parser.add_argument("mode", nargs="?", choices=["print", "csv", "udp", "gui"], default="gui",
                        help="Output mode (default: gui, so a double-clicked exe opens the GUI)")
    parser.add_argument("--port", default="auto", help="Serial port (default: auto)")
    parser.add_argument("--no-timestamps", action="store_true", help="Disable timestamps")
    parser.add_argument("--no-calibrate", action="store_true", help="Skip auto-calibration")
    parser.add_argument("--filename", default=None, help="CSV output filename (default: timestamped)")
    parser.add_argument("--udp-ip", default="127.0.0.1", help="UDP target IP (default: 127.0.0.1)")
    parser.add_argument("--udp-port", type=int, default=5005, help="UDP target port (default: 5005)")
    args = parser.parse_args()

    writer = SensorTool(
        port=args.port,
        timestamps=not args.no_timestamps,
        auto_calibrate=not args.no_calibrate,
    )

    # GUI keeps scanning on its own; the one-shot CLI modes need a port up front
    if args.mode != "gui" and writer.com_port is None:
        sys.exit("Error: no sensor found. Specify the serial port with --port.")

    if args.mode == "print":
        writer.fts_print()
    elif args.mode == "csv":
        writer.fts_to_csv(filename=args.filename)
    elif args.mode == "udp":
        writer.fts_to_udp(udp_ip=args.udp_ip, udp_port=args.udp_port)
    elif args.mode == "gui":
        writer.fts_gui()