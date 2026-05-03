// ゲームパッドからサーボ操作する
import processing.serial.*;
import controlP5.*;
import org.gamecontrolplus.*;

Serial serial;
ControlP5 cp5;
ControlIO control;
ControlDevice device;

final int N_AXIS = 4;
Slider[] slider = new Slider[N_AXIS];
String[] label = {"Rotate","Sholder","Elbow","Hand"};
int Rotate, Sholder, Elbow, Hand;
final int[][] SERVO_DUTY_SPEC = {
  //min, max, initial 
  {620, 2400, 1500},
  {920, 2020, 2000},
  {820, 2020, 1950},
  {750, 2450, 1600}
};

ControlSlider slider_rx, slider_ry, slider_lx, slider_ly;
ControlButton button_a, button_b, button_l, button_r;

// 1フレームあたりのDuty変化量(速度みたいなもの)
final int[] DUTY_CHANGE_PAR_FRAME = {10, 6, 7, 30};

void setup() 
{
  // ウィンドウ幅をこれ以上小さくすると
  // ウィンドウをつかめず、移動できなくなる
  size(200,260);
  frameRate(60);
  
  // シリアル初期化
  printArray(Serial.list());
  serial = new Serial(this, Serial.list()[0], 115200);
  
  // ControlP5関係
  cp5 = new ControlP5(this);
  ControlFont font1 = new ControlFont(createFont("Arial",14));

  // Gamepad関係
  control = ControlIO.getInstance(this);
  device = control.getDevice("Wireless Gamepad");

  // スティック・ボタンを取得
  slider_ry = device.getSlider(0);  //右スティックの上下
  slider_rx = device.getSlider(1);  //右スティックの左右
  slider_ly = device.getSlider(2);  //左スティックの上下
  slider_lx = device.getSlider(3);  //左スティックの左右
  button_b = device.getButton(0);
  button_a = device.getButton(1);
  button_l = device.getButton(4);
  button_r = device.getButton(5);
  
  // Duty設定用スライダ
  for ( int i = 0, y_pos = 25; i < N_AXIS; i++, y_pos += 55 ) {
    slider[i] = cp5.addSlider(label[i])
      .setPosition(10, y_pos)
      .setSize(120,30)
      .setRange(SERVO_DUTY_SPEC[i][0],SERVO_DUTY_SPEC[i][1])
      .setValue(SERVO_DUTY_SPEC[i][2]);
    slider[i].getValueLabel()
      .setFont(font1);
    slider[i].getCaptionLabel()
      .setFont(font1)
      .align(ControlP5.LEFT, ControlP5.TOP_OUTSIDE);
  }
  
  // 現在の指令値シリアル出力
  serialSend();
}

void draw() {
  background(0);
  
  // 姿勢制御
  updateServoFromGamepad();

  // 現在のサーボ指令値をシリアル出力し、ロボットに反映
  serialSend();
  
  // フレームレート表示
  textSize(16);
  text("Frame rate: " + nf(frameRate,1,1), 12, 245);
}

void updateServoFromGamepad()
{
  manualOperation();
  buttonOperation();
}

// ボタン操作による姿勢変更
void buttonOperation()
{
  // bボタンで初期位置に戻す
  if ( button_b.pressed() ) {
    initServo();
  }
}

// 初期位置に戻す
void initServo()
{
  for ( int i = 0; i < N_AXIS; i++ ) {
      slider[i].setValue(SERVO_DUTY_SPEC[i][2]);
  }
}

// 各関節をマニュアル操作
void manualOperation()
{
  // Gamepadの指令値を取得
  float[] command = new float[N_AXIS];
  // Rotate, Sholder, Elbow: スティック操作量
  final float SCALE = 1.0/0.8;               // スティック操作量は概ね 0.8 が最大なので、これを 1.0 にスケーリング
  command[0] = -slider_lx.getValue()*SCALE;  // Rotate(ここだけ、操作量を反転)
  command[1] = +slider_ry.getValue()*SCALE;  // Sholder
  command[2] = +slider_ly.getValue()*SCALE;  // Elbow
  // Hand：ボタン操作  
  if ( button_l.pressed() ) {
    command[3] = -1.0;
  }
  else if ( button_r.pressed() ) {
    command[3] = +1.0;
  }
  else {
    command[3] = 0.0;
  }
  
  // 各軸のDutyを変更
  for ( int i = 0; i < N_AXIS; i++ ) {
    int current_duty = int(slider[i].getValue());
    int speed = DUTY_CHANGE_PAR_FRAME[i];

    // Gamepadの指令値に応じて、Dutyを変更する
    // ある程度のスティック操作があったら、操作量に応じてDuty変更(スライダの設定値に設定)
    final float CMD_THRESH = 0.375;  // float で正確な数値が表現できる 1/4 + 1/8 = 0.375 を設定 
    if ( command[i] < -CMD_THRESH ) {
      int delta = int( speed * (command[i] + CMD_THRESH) / (1.0 - CMD_THRESH) );
      slider[i].setValue(current_duty + delta);
    }
    else if ( CMD_THRESH < command[i] ) {
      int delta = int( speed * (command[i] - CMD_THRESH) / (1.0 - CMD_THRESH) );
      slider[i].setValue(current_duty + delta);
    }
    // 微小なスティック操作には反応しない
    else {
      // 何もしない
    }
  }
}

void serialSend()
{
  // スライダUIの現在値を取得し、カンマ区切りの文字列に変換
  String send = "";
  for ( int i = 0; i < N_AXIS; i++ ){
    if ( i != 0 ) send += ",";
    send += str(int(slider[i].getValue()));
  }
  // micropythonのinput関数にデータを渡すには、最後に CR が必要(LFではダメだった) 
  send += "\r";

  serial.write(send);
  //デバッグ
  //println(send);
}

/*
// micropythonからの応答データを表示(この表示は無くてもよい)
// 送信データのエコーバックがあるため、PCから送信したデータも表示される
void serialEvent(Serial p) {
  if (p.available() > 0 ) {
    print(p.readString());
  }
}
*/
