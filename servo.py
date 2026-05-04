from machine import Pin, PWM


class Servo:
    """リミット・速度制限付き PWM サーボ制御クラス。

    update() を 20ms 周期で呼び出すことで、set_duty() で指定した目標値に
    speed_us ずつ近づける（滑らか追従）。
    """

    PWM_FREQ = 50  # 50Hz = 20ms 周期

    def __init__(self, pin, initial_duty_us, min_duty_us, max_duty_us, speed_us):
        self._pwm        = PWM(pin)
        self._min_us     = min_duty_us
        self._max_us     = max_duty_us
        self._speed_us   = speed_us  # 1 周期 (20ms) あたりの最大変化量
        self._cmd_us     = initial_duty_us
        self._out_us     = initial_duty_us
        self.initial_us  = initial_duty_us  # reset() の参照用
        self._pwm.freq(Servo.PWM_FREQ)
        self.update()

    def set_duty(self, duty_us):
        """目標 Duty 値をリミットして格納する（PWM 出力は update() で反映）。"""
        self._cmd_us = max(self._min_us, min(self._max_us, duty_us))

    def duty(self):
        """現在の目標 Duty 値を返す。"""
        return self._cmd_us

    def reset(self):
        """目標・出力の両方を initial_us に即時戻す。"""
        self._cmd_us = self.initial_us
        self._out_us = self.initial_us
        self._pwm.duty_ns(self._out_us * 1000)

    def update(self):
        """目標値に speed_us ずつ近づけて PWM 出力を更新する。20ms 周期で呼ぶ。"""
        if self._out_us > self._cmd_us + self._speed_us:
            self._out_us -= self._speed_us
        elif self._out_us < self._cmd_us - self._speed_us:
            self._out_us += self._speed_us
        else:
            self._out_us = self._cmd_us
        self._pwm.duty_ns(self._out_us * 1000)


class ToggleLed:
    """一定周期でトグルする LED クラス。

    period: update() 何回ごとにトグルするか（20ms 周期なら period=25 で 0.5 秒点滅）
    """

    def __init__(self, pin_no, period):
        self._pin    = Pin(pin_no, Pin.OUT)
        self._period = period
        self._count  = 0

    def update(self):
        self._count += 1
        if self._count >= self._period:
            self._pin.toggle()
            self._count = 0

    def on(self):
        self._pin.value(1)

    def off(self):
        self._pin.value(0)
