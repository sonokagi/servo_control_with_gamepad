#Raspberry Pi Picoを利用した余興用アームロボットのサーボ制御
from machine import Pin, PWM, Timer
import time

#サーボ制御(リミット付きPWM出力)
class Servo:
    PWM_FREQ = 50  #PWM周期20ms(=50Hz)
    
    def __init__(self, pin, initial_duty_us, min_duty_us, max_duty_us, speed_us):
        self.pwm_ = PWM(pin)
        self.min_us_ = min_duty_us
        self.max_us_ = max_duty_us
        self._cmd_us = initial_duty_us #指令
        self._out_us = initial_duty_us #出力
        self._speed_us = speed_us # 単位時間(20ms)あたりの変化量
        #PWM周波数とDutyの初期設定
        self.pwm_.freq(Servo.PWM_FREQ)
        self.set_duty(initial_duty_us)
        self.update()

    def set_duty(self, duty_us):
        """
        指示値をリミットして、格納
        """
        if duty_us < self.min_us_:
            self._cmd_us = self.min_us_
        elif duty_us > self.max_us_:
            self._cmd_us = self.max_us_
        else:
            self._cmd_us = duty_us
    
    def duty(self):
        """
        現在の指令値を取得
        """
        return self._cmd_us
    
    def update(self):
        """
        指令値に基づいて、最終的なPWM出力値決定し、出力に反映
        """
        # 現在値が指令値より大きいなら、speed分だけ減算して指令値に近づける
        if self._out_us > self._cmd_us + self._speed_us:
          self._out_us -= self._speed_us
          
        # 現在値が指令値より小さいなら、speed分だけ加算して指令値に近づける
        elif self._out_us < self._cmd_us - self._speed_us:
          self._out_us += self._speed_us
        
        # 現在値が指令値に十分近いなら、指令値に一致させる
        else:
          self._out_us = self._cmd_us
        
        # 現在値でPWM出力を更新
        self.pwm_.duty_ns(self._out_us*1000)       


# 一定間隔ごとにLEDをトグルする
class ToggleLed:
    def __init__(self, pin_no, priod):
        self._out = Pin(pin_no, Pin.OUT)
        self._priod = priod
        self._count = 0

    def update(self):
        self._count += 1
        if self._count == self._priod:
            self._out.toggle()
            self._count = 0


#文字列が整数に変換可能か
def is_int(s):
    try:
        int(s)
    except ValueError:
        return False
    else:
        return True


#タイマ割り込みで呼び出される関数
def timer_callback(timer):
    #global led
    #led.update()
    global servos
    for i in range(len(servos)):
        servos[i].update()

#サーボ制御用のピン定義と初期設定
servos = []
#自作ボード           pin      ini   min  max   speed
servos.append( Servo(Pin(14), 1520, 620, 2400, 12) ) #旋回
servos.append( Servo(Pin(15), 1540, 920, 2020,  9) ) #肩
servos.append( Servo(Pin(17), 1490, 820, 2020,  9) ) #肘
servos.append( Servo(Pin(16), 1600, 750, 2450, 36) ) #手首

#LEDピンの定義と初期設定
led = ToggleLed(18, 5)

#タイマーオブジェクトの作成(周期処理的に実行)
timer = Timer()
period_ms = 20
timer.init(period=period_ms, mode=Timer.PERIODIC, callback=timer_callback)

#メインループ
while True:
    #各サーボ分のPWM指示値をカンマ区切りで入力
    #例) 2000,1000,1500,2000
    line = input()

    #カンマ区切りの各要素を、(可能なら)整数に変換してリスト化する
    elms = line.split(',')
    vals = [int(e) for e in elms if is_int(e)]
    
    #各サーボ分の指示値を受信出来たら、PWM出力を変更する
    if len(vals) >= len(servos):
        dutys = []
        #各サーボが受付可能な範囲に指示値をリミットして、PWM出力を変更
        for i in range(len(servos)):
            servos[i].set_duty(vals[i])
            #動作を滑らかにするため、タイマ割り込みとは別に、指令を受けた時点でPWM値に反映してみる
            #-> あまり効果がわからないが、何となく良くなった気がするので、この処理は残す
            servos[i].update()
            dutys.append(servos[i].duty())
        #出力値を表示
        print(dutys)

    #LEDをトグル
    led.update()
