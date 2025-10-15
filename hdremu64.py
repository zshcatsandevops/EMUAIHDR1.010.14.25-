#!/usr/bin/env python3
"""
ProjectEMU64 v1.0 [C] FlamesCo & Samsoft
N64 MIPS R4300i Emulator - Project64 Legacy Style (Tkinter Edition)
Prebuilt Python 3.13 Standalone Release
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import struct, time, threading, random
from pathlib import Path

# ============================================================================
# Constants
# ============================================================================
PROJECTEMU64_VERSION = "1.0"
PROJECTEMU64_BUILD = "Tkinter 600x400 60 fps Edition"
PROJECTEMU64_COPYRIGHT = "© 2025 FlamesCo / Samsoft"
WINDOW_TITLE = "ProjectEMU64 Tkinter 600x400 60 fps"

# Controller constants
CONTROLLER_A = 0x0001
CONTROLLER_B = 0x0002
CONTROLLER_START = 0x0004
CONTROLLER_DPAD_UP = 0x0010
CONTROLLER_DPAD_DOWN = 0x0020
CONTROLLER_DPAD_LEFT = 0x0040
CONTROLLER_DPAD_RIGHT = 0x0080

# ============================================================================
# CPU Core (simplified interpreter)
# ============================================================================
class ProjectEMU64CPU:
    def __init__(self):
        self.regs = [0]*32
        self.pc = 0x80000000
        self.next_pc = self.pc + 4
        self.hi = self.lo = 0
        self.cp0 = [0]*32
        self.running = False
        self.cycles = 0

    def reset(self):
        self.regs = [0]*32
        self.pc = 0x80000000
        self.next_pc = self.pc + 4
        self.cycles = 0

    def fetch(self, memory, addr):
        return memory.read_word(addr)

    def execute(self, memory, log_callback=None):
        if not self.running:
            return
        instr = self.fetch(memory, self.pc)
        if log_callback:
            log_callback(f"[PC: {self.pc:08X}] 0x{instr:08X}")
        self.pc += 4
        self.cycles += 1

# ============================================================================
# Memory Controller
# ============================================================================
class ProjectEMU64Memory:
    def __init__(self):
        self.rdram = bytearray(8 * 1024 * 1024)
        self.rom = None
        self.rom_size = 0

    def load_rom(self, data):
        self.rom = bytearray(data)
        self.rom_size = len(data)
        copy = min(self.rom_size, len(self.rdram))
        self.rdram[:copy] = self.rom[:copy]

    def read_word(self, addr):
        if addr < len(self.rdram)-3:
            return struct.unpack(">I", self.rdram[addr:addr+4])[0]
        return 0

# ============================================================================
# Simple GPU/PPU (placeholder render)
# ============================================================================
class ProjectEMU64PPU:
    def __init__(self):
        self.width, self.height = 320, 240
        self.framebuffer = ["#000000"] * (self.width * self.height)

    def reset(self):
        color = "#0011FF"
        self.framebuffer = [color]*(self.width*self.height)

    def draw_random_square(self):
        color = "#FFFFFF"
        x = random.randint(0, self.width-21)
        y = random.randint(0, self.height-21)
        for j in range(20):
            for i in range(20):
                idx = (y+j)*self.width + (x+i)
                self.framebuffer[idx] = color

    def update_display(self, image):
        for y in range(self.height):
            for x in range(self.width):
                color = self.framebuffer[y*self.width+x]
                image.put(color, (x, y))
        return image

# ============================================================================
# Controller
# ============================================================================
class SimpleController:
    def __init__(self):
        self.buttons = 0

    def update(self, keys):
        self.buttons = 0
        if "space" in keys: self.buttons |= CONTROLLER_A
        if "Return" in keys: self.buttons |= CONTROLLER_B
        if "Up" in keys: self.buttons |= CONTROLLER_DPAD_UP
        if "Down" in keys: self.buttons |= CONTROLLER_DPAD_DOWN
        if "Left" in keys: self.buttons |= CONTROLLER_DPAD_LEFT
        if "Right" in keys: self.buttons |= CONTROLLER_DPAD_RIGHT

# ============================================================================
# Main Launcher GUI
# ============================================================================
class ProjectEMU64Launcher:
    def __init__(self, root):
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.geometry("600x400")

        # Cores
        self.cpu = ProjectEMU64CPU()
        self.memory = ProjectEMU64Memory()
        self.ppu = ProjectEMU64PPU()
        self.controller = SimpleController()
        self.keys = set()
        self.running = False
        self.fps = 0
        self.frame_count = 0
        self.start_time = time.time()

        # GUI setup
        self.photo = tk.PhotoImage(width=320, height=240)
        self.canvas = tk.Canvas(root, width=320, height=240, bg="black")
        self.canvas.pack(pady=10)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)

        self.status = tk.Label(root, text="Ready.", anchor=tk.W)
        self.status.pack(fill=tk.X, side=tk.BOTTOM)
        self.fps_label = tk.Label(root, text="FPS: 0", font=("Courier", 10))
        self.fps_label.pack()

        # Menu
        self.make_menu()
        self.root.bind("<KeyPress>", self.key_down)
        self.root.bind("<KeyRelease>", self.key_up)

    # ---------------- GUI Setup ----------------
    def make_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open ROM...", command=self.open_rom)
        file_menu.add_command(label="Start", command=self.start)
        file_menu.add_command(label="Stop", command=self.stop)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        plugin_menu = tk.Menu(menubar, tearoff=0)
        plugin_menu.add_command(label="Configure Graphics", command=self.config_graphics)
        plugin_menu.add_command(label="Configure Audio", command=self.config_audio)
        plugin_menu.add_command(label="Configure Controller", command=self.config_controller)
        plugin_menu.add_command(label="Configure RSP", command=self.config_rsp)
        menubar.add_cascade(label="Plugins", menu=plugin_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

    # ---------------- Key Input ----------------
    def key_down(self, e):
        self.keys.add(e.keysym)
        self.controller.update(self.keys)

    def key_up(self, e):
        if e.keysym in self.keys:
            self.keys.remove(e.keysym)
        self.controller.update(self.keys)

    # ---------------- Emulator ----------------
    def open_rom(self):
        path = filedialog.askopenfilename(title="Select ROM", filetypes=[("N64 ROM", "*.z64 *.n64 *.v64")])
        if not path: return
        try:
            with open(path, "rb") as f:
                data = f.read()
            self.memory.load_rom(data)
            self.status.config(text=f"Loaded {Path(path).name}")
        except Exception as e:
            messagebox.showerror("Load Error", str(e))

    def start(self):
        if self.running:
            return
        self.cpu.reset()
        self.ppu.reset()
        self.running = True
        self.status.config(text="Running...")
        threading.Thread(target=self.loop, daemon=True).start()

    def stop(self):
        self.running = False
        self.status.config(text="Stopped")

    def loop(self):
        while self.running:
            self.cpu.execute(self.memory)
            if random.randint(0, 10) == 0:
                self.ppu.draw_random_square()
            self.ppu.update_display(self.photo)
            self.update_fps()
            time.sleep(1/60)

    def update_fps(self):
        self.frame_count += 1
        now = time.time()
        if now - self.start_time >= 1.0:
            self.fps = self.frame_count
            self.frame_count = 0
            self.start_time = now
            self.root.after(0, lambda: self.fps_label.config(text=f"FPS: {self.fps}"))

    # ---------------- Config Windows ----------------
    def config_graphics(self):
        self.show_plugin_config("Graphics Plugin")

    def config_audio(self):
        self.show_plugin_config("Audio Plugin")

    def config_controller(self):
        self.show_plugin_config("Controller Plugin")

    def config_rsp(self):
        self.show_plugin_config("RSP Plugin")

    def show_plugin_config(self, name):
        win = tk.Toplevel(self.root)
        win.title(name)
        win.geometry("300x150")
        tk.Label(win, text=name, font=("Arial", 12, "bold")).pack(pady=10)
        tk.Label(win, text="Basic config window (placeholder)").pack(pady=10)
        tk.Button(win, text="OK", command=win.destroy).pack(pady=10)

    # ---------------- About ----------------
    def show_about(self):
        messagebox.showinfo(
            "About ProjectEMU64",
            f"{WINDOW_TITLE}\n{PROJECTEMU64_BUILD}\n{PROJECTEMU64_COPYRIGHT}\n\n"
            "Playable demo with fake GPU/CPU loop.\nArrows = move, Space = A button."
        )

# ============================================================================
# Main
# ============================================================================
def main():
    root = tk.Tk()
    app = ProjectEMU64Launcher(root)
    root.mainloop()

if __name__ == "__main__":
    main()
