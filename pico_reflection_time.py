"picoのmainとAD9833を動かすプログラム"
"""
初めて触る人へ。
実行後、Shellになにか文字を打ってエンターを押してください
文字が入れば始まります。
"""
# pico側 (MicroPython)
import _thread
import rp2
from machine import Pin
import time
import sys
from math import pi, radians
from module import AD9833
import select

# --- PIO: 入力立ち上がり検出用 (元のアセンブリをほぼ維持) ---
@rp2.asm_pio(set_init=rp2.PIO.IN_LOW)
def edge_capture():
    pull(block)                 # OSR から y に初期値を入れる
    mov(y, osr)
    label("start")
    mov(x, y)
    set(pindirs, 0b000)
    wait(0, pin, 0)
    wait(1, pin, 0)
    label("wait_for_fall")
    nop() [31]
    jmp(pin, "dec_and_fall")
    jmp("wait_for_rise")
    label("dec_and_fall")
    jmp(x_dec, "wait_for_fall")
#     jmp("start")
    label("wait_for_rise")
    jmp(pin, "got_rise")
    jmp(x_dec, "wait_for_rise")
#     jmp("start")
    label("got_rise")
    mov(isr, x)
    push()
#     jmp("start")
#     label("done")
#     jmp("start")

# --- ユーティリティ関数 ---
def filter_large_values(data):
    """(最大値 + 最小値) / 2 より小さい値を除外"""
    if not data:
        return []
    max_val = max(data)
    min_val = min(data)
    threshold = (max_val + min_val) / 2
    return [x for x in data if x >= threshold]

def median(data):
    data = sorted(data)
    n = len(data)
    mid = n // 2
    
    if n % 2 == 1:
        return data[mid]
    else:
        return (data[mid-1] + data[mid])/2

def calculate_statistics(data):
    """平均・標準偏差を計算（データ長0/1に対応）"""
    n = len(data)
    if n == 0:
        return 0.0, 0.0, []
    #mean = sum(data) / n
    mean = median(data)
    if n == 1:
        stdev = 0.0
    else:
        # 標本分散（n-1 で割る）
        var = sum((x - mean) ** 2 for x in data) / (n - 1)
        stdev = var ** 0.5
    return mean, stdev, data

# ======= Core1 ======
def core1_pio():
    from machine import Pin
    # --- GPIO設定 ---
    trigger_pin = Pin(11, Pin.IN, pull=Pin.PULL_DOWN)  # トリガー用（in_baseに使う）
    pins_capture = [12,13,14,15]     # キャプチャ対象ピンリストこのリストに使う予定のピンを全て入れてピンの準備をする
   # キャプチャ対象ピンリスト

    # --- ステートマシン準備 ---
    sms = []
    for i, pin_num in enumerate(pins_capture):
        cap_pin = Pin(pin_num, Pin.IN, pull=Pin.PULL_DOWN)
        # freq と in_base/jmp_pin は環境に合わせて調整してください
        sm = rp2.StateMachine(i, edge_capture, freq=20_000_000, in_base=trigger_pin, jmp_pin=cap_pin)
        sms.append(sm)
        

#     print("PICO ready. ")

    # --- メインループ: シリアルからコマンドを受け取る ---
    while True:
        for sm in sms:
            try:
                # rx_fifo() may not exist on all builds; try to drain safely
                while sm.rx_fifo():
                    _ = sm.get()
            except Exception:
                # もし rx_fifo() が無ければ、try-get を軽く回す
                try:
                    while True:
                        _ = sm.get()
                except Exception:
                    pass

#         print("Starting trigger SM...")
        for sm in sms:
            sm.active(1)

        # キャプチャデータ収集（最大20回試行）
        results = {pin: [] for pin in pins_capture}
        attempts = 10
        for _ in range(attempts):
            # sm.put によってカウントを与えて PIO を動作させる
            for sm in sms:
                try:
                    sm.put(20000)
                except Exception:
                    pass
            
            # 少し待ってから結果を取りに行く（PIO のタイミングに合わせる）
            time.sleep(0.001)
                
            for pin, sm in zip(pins_capture, sms):

                try:
                    cycle_get = sm.get()  # 取得。失敗したら例外処理へ
#                     print(cycle_get)
                except Exception:
                    # 取得できなければスキップ
                    continue

                # 元のコードのロジックに合わせ、閾値で無視する
                if cycle_get > 19000:
                    # 無効値（タイムアウト等）
                    pass
                else:
                    clock = 20000 - cycle_get
                    clockCycles = clock * 2
                    # 20 MHz => 50 ns per cycle, 50ns * clockCycles -> ns
                    time_ns = clockCycles * 50  # ns
                    time_us = time_ns / 1000.0  # μs
                    results[pin].append(time_us)
#                     print(time_us)
#         print('1')
        # 表示（取得できた分だけ）
        max_len = max((len(v) for v in results.values()), default=0)
        for i in range(max_len):
            line_parts = []
            for pin in pins_capture:
                vals = results[pin]
                if i < len(vals):
                    line_parts.append(f"GPIO{pin} = {vals[i]:.1f} μs")
                else:
                    line_parts.append(f"GPIO{pin} = -")
#             print(f"{i+1} 回目: " + ", ".join(line_parts))
#         print("Capture finished.")
#         print('2')
        # --- 統計処理 ---
        
        for pin, data in results.items():
            normal_stats = calculate_statistics(data)
            filtered_data = filter_large_values(data)
            filtered_stats = calculate_statistics(filtered_data)
        median_buffers = {pin:[] for pin in pins_capture}
            
            # 元データ統計
#             print(f"GPIO{pin} (元データ): 平均 = {normal_stats[0]:.1f} μs, 標準偏差 = {normal_stats[1]:.3f} μs, count = {len(data)}")
            # フィルタ後統計
#             print(f"GPIO{pin} (フィルタ後): 平均 = {filtered_stats[0]:.1f} μs, 標準偏差 = {filtered_stats[1]:.3f} μs, データ = {filtered_stats[2]}")
            
                    # --- フィルタ後平均の4ピンぶんをラズパイに送信 ---
        avg_list = []
        avg_list = []

        for pin in pins_capture:   # ← 絶対にこの順番
            data = results[pin]

            filtered_data = filter_large_values(data)

            if not filtered_data:
                avg_list.append(None)   # 取れてない
                continue

            filtered_stats = calculate_statistics(filtered_data)
            current_median = filtered_stats[0]

            buf = median_buffers[pin]
            buf.append(current_median)
            if len(buf) > 20:
                buf.pop(0)

            if len(buf) >= 20:
                median_median = median(buf)
            else:
                median_median = buf[-1]

            avg_list.append(median_median)
            # カンマ区切りで送信 (例: "450.2,462.1,455.9,470.3")
        out_str = ",".join(f"{(v if v is not None else 0.0):.3f}"
                           for v in avg_list)
        print(out_str)

# Core1起動
_thread.start_new_thread(core1_pio, ())

if __name__ == "__main__":
    # AD9833の初期化（ピン番号は環境に合わせて変更）
#     以下初期化のために追加
# AD9833の初期化 MOSI   SCLK   FSYNC 波形発生器の周波数
    SDO_PIN = 3 # MOSI 共通
    CLK_PIN = 2 # SCLK 共通
    FREQ = 40000  # 40 kHz
    # FSYNC 8ch
    CS_PINS = [4,5,6,7,21,20,19,18]

    # --- 位相リスト（度単位） ---
#     PHASES = [0, 45, 90, 135, 180, 225, 270, 315]

    # --- AD9833初期化 ---
    ad1 = AD9833(sdo=SDO_PIN, clk=CLK_PIN, cs=CS_PINS[0], fmclk=25)
    ad2 = AD9833(sdo=SDO_PIN, clk=CLK_PIN, cs=CS_PINS[1], fmclk=25)
    ad3 = AD9833(sdo=SDO_PIN, clk=CLK_PIN, cs=CS_PINS[2], fmclk=25)
    ad4 = AD9833(sdo=SDO_PIN, clk=CLK_PIN, cs=CS_PINS[3], fmclk=25)
    ad5 = AD9833(sdo=SDO_PIN, clk=CLK_PIN, cs=CS_PINS[4], fmclk=25)
    ad6 = AD9833(sdo=SDO_PIN, clk=CLK_PIN, cs=CS_PINS[5], fmclk=25)
    ad7 = AD9833(sdo=SDO_PIN, clk=CLK_PIN, cs=CS_PINS[6], fmclk=25)
    ad8 = AD9833(sdo=SDO_PIN, clk=CLK_PIN, cs=CS_PINS[7], fmclk=25)
    
    ad1.set_mode('RESET')
    ad2.set_mode('RESET')
    ad3.set_mode('RESET')
    ad4.set_mode('RESET')
    ad5.set_mode('RESET')
    ad6.set_mode('RESET')
    ad7.set_mode('RESET')
    ad8.set_mode('RESET')
    time.sleep_us(10)
#     # 正弦波モードで出力開始
#     ad1.set_mode('SIN')

    # 4周期分だけ出力する（40kHz → 100μs）
#     time.sleep_us(int(1_000_000 * 4 / freq))  # ≈100μs
    ad1.set_frequency(FREQ,0)  # 例：40kHz, 41kHz, …, 47kHz
    ad1.set_phase(0, 0, rads=False)
    # 出力停止（RESETモード）
    ad1.set_mode('OFF')
    
#     print("start")

    cmd = sys.stdin.readline().strip()

    try:
        while(1):
            if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
#                 print("a")
                cmd = sys.stdin.readline().strip()
                if cmd == "stop":
                    machine.reset()
                    ad1.set_mode('OFF')
                    while(1):
                        pass
            
    #         print("sin")
            ad1.set_mode('SIN')
            time.sleep_us(400)
#             time.sleep(5)
            ad1.set_mode('OFF')
    #         print("reset")k
    
            time.sleep(0.3)
            
#             if cmd == "stop":
#                 while(1):
#                     ad1.set_mode('OFF')
                

    except KeyboardInterrupt:
#         print("Program stopped by user.")
        ad1.set_mode('OFF')
        


