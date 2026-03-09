#!/usr/bin/env python3
"""Standalone Tkinter CoCo cartridge dumper."""

from __future__ import annotations

import re
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import serial
from serial.tools import list_ports

SERIAL_OPEN_SETTLE_S = 2.0
DEFAULT_BAUD = 115200
DEFAULT_START = "C000"
DEFAULT_SIZE = "auto"
MAX_DUMP_SIZE = 0x4000


def wait_for_begin(ser: serial.Serial, timeout_s: float = 5.0) -> int:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        line = ser.readline().decode("ascii", errors="ignore").strip()
        if not line:
            continue
        if line.startswith("BEGIN "):
            parts = line.split()
            if len(parts) == 2 and parts[1].isdigit():
                return int(parts[1])
    raise RuntimeError("Timed out waiting for BEGIN header")


def wait_for_end(ser: serial.Serial, timeout_s: float = 3.0) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        line = ser.readline().decode("ascii", errors="ignore").strip()
        if line == "END":
            return
    raise RuntimeError("Timed out waiting for END marker")


def read_exact(ser: serial.Serial, size: int, timeout_s: float = 20.0) -> bytes:
    deadline = time.time() + timeout_s
    out = bytearray()
    while len(out) < size:
        if time.time() > deadline:
            break
        remaining = size - len(out)
        chunk = ser.read(remaining)
        if chunk:
            out.extend(chunk)
    return bytes(out)


def capture_dump(
    ser: serial.Serial,
    start: int,
    size: int,
    begin_timeout: float = 5.0,
    read_timeout: float = 20.0,
    retries: int = 2,
) -> bytes:
    attempts = retries + 1
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            ser.reset_input_buffer()
            ser.write(f"D {start:04X} {size:04X}\n".encode("ascii"))
            ser.flush()

            expected = wait_for_begin(ser, timeout_s=begin_timeout)
            if expected != size:
                raise RuntimeError(f"Sketch reports size {expected}, expected {size}")

            data = read_exact(ser, size, timeout_s=read_timeout)
            if len(data) != size:
                raise RuntimeError(f"Short read: got {len(data)} bytes, expected {size}")

            wait_for_end(ser)
            return data
        except Exception as exc:
            last_error = exc
            if attempt == attempts:
                raise RuntimeError(
                    f"All {attempts} attempts failed; last error: {last_error}"
                ) from last_error
    raise RuntimeError("unreachable")


def looks_unconnected_probe(data: bytes) -> bool:
    if not data:
        return True
    unique = set(data)
    if len(unique) == 1 and data[0] in {0x00, 0xFF}:
        return True
    if len(unique) <= 2 and unique.issubset({0x00, 0xFF}):
        return True
    return False


def cart_presence_check(
    ser: serial.Serial,
    start: int,
    begin_timeout: float = 5.0,
    read_timeout: float = 20.0,
    retries: int = 2,
) -> None:
    probe_size = 0x0200
    probe_a1 = capture_dump(ser, start, probe_size, begin_timeout, read_timeout, retries)
    probe_a2 = capture_dump(ser, start, probe_size, begin_timeout, read_timeout, retries)
    probe_b_start = (start + 0x2000) & 0xFFFF
    probe_b1 = capture_dump(ser, probe_b_start, probe_size, begin_timeout, read_timeout, retries)
    probe_b2 = capture_dump(ser, probe_b_start, probe_size, begin_timeout, read_timeout, retries)

    a_repeatable = probe_a1 == probe_a2
    b_repeatable = probe_b1 == probe_b2
    if not (a_repeatable or b_repeatable):
        raise RuntimeError("No cartridge detected (probe reads are not repeatable)")

    if (
        looks_unconnected_probe(probe_a1)
        and looks_unconnected_probe(probe_b1)
        and a_repeatable
        and b_repeatable
    ):
        raise RuntimeError("No cartridge detected (probe reads look unconnected)")


def detect_cart_size_from_full_dump(data_16k: bytes) -> tuple[int, str]:
    if len(data_16k) != MAX_DUMP_SIZE:
        raise ValueError("internal error: auto-size requires a 16 KiB capture")

    lower = data_16k[:0x2000]
    upper = data_16k[0x2000:]
    lower_unconnected = looks_unconnected_probe(lower)
    upper_unconnected = looks_unconnected_probe(upper)

    if upper_unconnected and not lower_unconnected:
        return 0x2000, "upper 8 KiB looks unconnected"
    if upper == lower and not lower_unconnected:
        return 0x2000, "upper 8 KiB mirrors lower 8 KiB"
    return 0x4000, "upper 8 KiB appears populated"


def validate_captured_dump(data: bytes) -> None:
    if looks_unconnected_probe(data):
        raise RuntimeError("Captured dump looks unconnected; refusing to save output")


def sanitize_cart_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._ -]+", "_", name.strip())
    cleaned = cleaned.strip(" .")
    return cleaned


class DumperApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("CoCo Cartridge Dumper")
        self.root.resizable(False, False)

        self.port_var = tk.StringVar()
        self.folder_var = tk.StringVar(value=str(Path.cwd()))
        self.cart_name_var = tk.StringVar(value="cart_dump")
        self.start_var = tk.StringVar(value=DEFAULT_START)
        self.size_var = tk.StringVar(value=DEFAULT_SIZE)
        self.status_var = tk.StringVar(value="Select a serial port, folder, and cart name.")
        self.dump_button: ttk.Button | None = None
        self.is_dumping = False

        self.build_ui()
        self.refresh_ports()

    # Keep the list compact while still allowing manual entry if detection fails.
    def build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=12)
        frame.grid(row=0, column=0, sticky="nsew")

        ttk.Label(frame, text="Serial Port").grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.port_combo = ttk.Combobox(frame, textvariable=self.port_var, width=28)
        self.port_combo.grid(row=0, column=1, sticky="ew", pady=(0, 6))
        ttk.Button(frame, text="Refresh", command=self.refresh_ports).grid(row=0, column=2, padx=(8, 0), pady=(0, 6))

        ttk.Label(frame, text="Save Folder").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Entry(frame, textvariable=self.folder_var, width=28).grid(row=1, column=1, sticky="ew", pady=6)
        ttk.Button(frame, text="Browse", command=self.choose_folder).grid(row=1, column=2, padx=(8, 0), pady=6)

        ttk.Label(frame, text="Cart Name").grid(row=2, column=0, sticky="w", pady=6)
        ttk.Entry(frame, textvariable=self.cart_name_var, width=28).grid(row=2, column=1, columnspan=2, sticky="ew", pady=6)

        ttk.Label(frame, text="Start Address").grid(row=3, column=0, sticky="w", pady=6)
        ttk.Entry(frame, textvariable=self.start_var, width=12).grid(row=3, column=1, sticky="w", pady=6)

        ttk.Label(frame, text="Size").grid(row=4, column=0, sticky="w", pady=6)
        size_combo = ttk.Combobox(
            frame,
            textvariable=self.size_var,
            width=12,
            values=("auto", "2000", "4000"),
            state="readonly",
        )
        size_combo.grid(row=4, column=1, sticky="w", pady=6)

        self.dump_button = ttk.Button(frame, text="Dump Cartridge", command=self.start_dump)
        self.dump_button.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(12, 8))

        status = ttk.Label(frame, textvariable=self.status_var, wraplength=360, justify="left")
        status.grid(row=6, column=0, columnspan=3, sticky="w")

        frame.columnconfigure(1, weight=1)

    def refresh_ports(self) -> None:
        ports = [port.device for port in list_ports.comports()]
        self.port_combo["values"] = ports
        if ports and not self.port_var.get():
            self.port_var.set(ports[0])
        self.set_status("Ready." if ports else "No serial ports found. Connect the Mega and click Refresh.")

    def choose_folder(self) -> None:
        folder = filedialog.askdirectory(initialdir=self.folder_var.get() or str(Path.cwd()))
        if folder:
            self.folder_var.set(folder)

    def set_status(self, message: str) -> None:
        self.status_var.set(message)

    def set_dumping(self, dumping: bool) -> None:
        self.is_dumping = dumping
        if self.dump_button is not None:
            self.dump_button.state(["disabled"] if dumping else ["!disabled"])

    def start_dump(self) -> None:
        if self.is_dumping:
            return

        try:
            port = self.port_var.get().strip()
            if not port:
                raise ValueError("Select a serial port.")

            folder = Path(self.folder_var.get().strip()).expanduser()
            if not folder.is_dir():
                raise ValueError("Choose an existing save folder.")

            cart_name = sanitize_cart_name(self.cart_name_var.get())
            if not cart_name:
                raise ValueError("Enter a cart name.")

            start = int(self.start_var.get().strip(), 16)
            if start < 0 or start > 0xFFFF:
                raise ValueError

            size_text = self.size_var.get().strip().lower()
            if size_text == "auto":
                size: int | str = "auto"
            else:
                size = int(size_text, 16)
                if size <= 0 or size > MAX_DUMP_SIZE:
                    raise ValueError
        except ValueError as exc:
            message = str(exc) if str(exc) else "Check the start address and size."
            messagebox.showerror("Invalid Settings", message)
            return

        out_path = folder / f"{cart_name}.ccc"
        self.set_dumping(True)
        self.set_status(f"Dumping cartridge to {out_path}...")

        thread = threading.Thread(
            target=self.dump_worker,
            args=(port, start, size, out_path),
            daemon=True,
        )
        thread.start()

    def dump_worker(self, port: str, start: int, size: int | str, out_path: Path) -> None:
        try:
            result = self.perform_dump(port, start, size, out_path)
        except Exception as exc:
            self.root.after(0, self.on_dump_error, str(exc))
            return
        self.root.after(0, self.on_dump_success, result)

    def perform_dump(self, port: str, start: int, size: int | str, out_path: Path) -> str:
        with serial.Serial(port, DEFAULT_BAUD, timeout=0.25) as ser:
            time.sleep(SERIAL_OPEN_SETTLE_S)
            cart_presence_check(ser, start)

            if size == "auto":
                raw_16k = capture_dump(ser, start, 0x4000)
                detected_size, reason = detect_cart_size_from_full_dump(raw_16k)
                data = raw_16k[:detected_size]
                detail = f"Auto size selected {detected_size} bytes because {reason}."
            else:
                data = capture_dump(ser, start, size)
                detail = f"Captured {len(data)} bytes."

            validate_captured_dump(data)
            out_path.write_bytes(data)

        return f"{detail} Saved to {out_path}"

    def on_dump_success(self, message: str) -> None:
        self.set_dumping(False)
        self.set_status(message)
        messagebox.showinfo("Dump Complete", message)

    def on_dump_error(self, message: str) -> None:
        self.set_dumping(False)
        self.set_status(message)
        messagebox.showerror("Dump Failed", message)


def main() -> int:
    root = tk.Tk()
    DumperApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
