import sys
import threading
import argparse
import tkinter as tk
from tkinter import messagebox
from tkinter import scrolledtext
from pythonosc import osc_server
from pythonosc import udp_client

# グローバル変数で状態・通信情報を管理
cached_root = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0]
cached_hips = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0]

server_thread = None
osc_server_instance = None
is_running = False
client = None

def multiply_quaternions(q1, q2):
    x1, y1, z1, w1 = q1
    x2, y2, z2, w2 = q2
    return [
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2,
        w1*w2 - x1*x2 - y1*y2 - z1*z2
    ]

class App(tk.Tk):
    def __init__(self, default_ip="127.0.0.1", default_port=39539, listen_port=39539):
        super().__init__()
        self.title("VMCプロキシ") # 日本語タイトル
        
        # コンパクトなUIサイズ (初期: 横240px × 縦210px)
        self.geometry("240x210")
        self.resizable(False, False)

        self.listen_port = listen_port
        self.log_visible = False 

        # 滲みや潰れが発生しない、最も安全なシステムフォントの組み合わせに修正
        font_main = ("Meiryo", 9)
        font_button = ("Meiryo", 10)
        font_log = ("Consolas", 9)

        # UI要素の配置（以前の日本語に戻しました）
        tk.Label(self, text=f"受信ポート: {self.listen_port}", font=font_main, fg="#2196F3").pack(pady=(10, 2))

        tk.Label(self, text="送信先 IPアドレス:", font=font_main).pack(pady=(4, 1))
        self.entry_ip = tk.Entry(self, width=18, justify="center", font=font_main)
        self.entry_ip.insert(0, default_ip)
        self.entry_ip.pack()

        tk.Label(self, text="送信先 ポート番号:", font=font_main).pack(pady=(6, 1))
        self.entry_port = tk.Entry(self, width=18, justify="center", font=font_main)
        self.entry_port.insert(0, str(default_port))
        self.entry_port.pack()

        self.btn_toggle = tk.Button(self, text="通信開始", bg="#4CAF50", fg="white", 
                                    font=font_button, width=12, height=1, bd=1, relief="raised", command=self.toggle_proxy)
        self.btn_toggle.pack(pady=10)

        # 折りたたみ式エラーログ（ラベルは日本語）
        self.lbl_log_toggle = tk.Label(self, text="▶ エラーログを表示", fg="#2196F3", cursor="hand2", font=font_main)
        self.lbl_log_toggle.pack(pady=(2, 5))
        self.lbl_log_toggle.bind("<Button-1>", lambda e: self.toggle_log_window())

        # ログコンソール本体（初期テキストは英文）
        self.log_area = scrolledtext.ScrolledText(self, width=28, height=6, font=font_log)
        self.log_area.insert(tk.END, "No errors reported.\n")
        self.log_area.configure(state="disabled")

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def toggle_log_window(self):
        if not self.log_visible:
            self.lbl_log_toggle.config(text="▼ エラーログを隠す")
            self.geometry("240x330") 
            self.log_area.pack(padx=15, pady=(0, 8))
            self.log_visible = True
        else:
            self.lbl_log_toggle.config(text="▶ エラーログを表示")
            self.log_area.pack_forget() 
            self.geometry("240x210") 
            self.log_visible = False

    def log_error(self, message):
        """エラーログ専用の出力関数（ログ中身は英文）"""
        def append():
            self.log_area.configure(state="normal")
            if "No errors reported." in self.log_area.get("1.0", tk.END):
                self.log_area.delete("1.0", tk.END)
            self.log_area.insert(tk.END, f"[ERROR] {message}\n")
            self.log_area.see(tk.END)
            self.log_area.configure(state="disabled")
            
            # エラー発生時は自動的にログウィンドウを開いて警告
            if not self.log_visible:
                self.toggle_log_window()
        self.after(0, append)

    def filter_and_forward(self, address, *osc_args):
        global cached_root, cached_hips, client, is_running
        if not is_running or client is None:
            return

        try:
            if address == "/VMC/Ext/Root/Pos":
                if len(osc_args) >= 8:
                    cached_root = [osc_args[1], osc_args[2], osc_args[3], osc_args[4], osc_args[5], osc_args[6], osc_args[7]]
                    new_args = list(osc_args)
                    new_args[1], new_args[2], new_args[3] = 0.0, 0.0, 0.0
                    new_args[4], new_args[5], new_args[6] = 0.0, 0.0, 0.0
                    new_args[7] = 1.0
                    client.send_message(address, new_args)
                    return

            elif address == "/VMC/Ext/Bone/Pos":
                if len(osc_args) >= 8:
                    bone_name = osc_args[0]
                    if bone_name.lower() == "hips":
                        cached_hips = [osc_args[1], osc_args[2], osc_args[3], osc_args[4], osc_args[5], osc_args[6], osc_args[7]]
                        integrated_x = cached_hips[0] + cached_root[0]
                        integrated_y = cached_hips[1] + cached_root[1]
                        integrated_z = cached_hips[2] + cached_root[2]
                        q_root = cached_root[3:7]
                        q_hips = cached_hips[3:7]
                        integrated_q = multiply_quaternions(q_root, q_hips)

                        new_args = list(osc_args)
                        new_args[1] = integrated_x
                        new_args[2] = integrated_y
                        new_args[3] = integrated_z
                        new_args[4:8] = integrated_q
                        client.send_message(address, new_args)
                        return

            client.send_message(address, list(osc_args))
        except Exception as e:
            self.log_error(f"Forwarding failed: {e}")

    def toggle_proxy(self):
        global is_running, server_thread, osc_server_instance, client
        
        if not is_running:
            ip = self.entry_ip.get().strip()
            port_str = self.entry_port.get().strip()

            if not ip:
                messagebox.showerror("エラー", "IPアドレスを入力してください。")
                return
            
            port = 39539 if not port_str else int(port_str)

            try:
                client = udp_client.SimpleUDPClient(ip, port)
                dispatcher = osc_server.Dispatcher()
                dispatcher.map("*", self.filter_and_forward)
                
                osc_server.ThreadingOSCUDPServer.allow_reuse_address = True
                osc_server_instance = osc_server.ThreadingOSCUDPServer(("0.0.0.0", self.listen_port), dispatcher)
                
                is_running = True
                server_thread = threading.Thread(target=osc_server_instance.serve_forever, daemon=True)
                server_thread.start()

                self.btn_toggle.config(text="通信停止", bg="#F44336")
                self.entry_ip.config(state="disabled")
                self.entry_port.config(state="disabled")
            except Exception as e:
                self.log_error(f"Server startup failed: {e}")
                messagebox.showerror("エラー", f"サーバーの起動に失敗しました:\n{e}")
        else:
            is_running = False
            if osc_server_instance:
                osc_server_instance.shutdown()
                osc_server_instance.server_close()
            
            self.btn_toggle.config(text="通信開始", bg="#4CAF50")
            self.entry_ip.config(state="normal")
            self.entry_port.config(state="normal")

    def on_closing(self):
        global is_running, osc_server_instance
        if is_running:
            is_running = False
            if osc_server_instance:
                osc_server_instance.shutdown()
        self.destroy()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--listen-port", type=int, default=39539)
    parser.add_argument("--target-ip", type=str, default="127.0.0.1")
    parser.add_argument("--target-port", type=int, default=39539)
    args = parser.parse_args()

    app = App(default_ip=args.target_ip, default_port=args.target_port, listen_port=args.listen_port)
    app.mainloop()
