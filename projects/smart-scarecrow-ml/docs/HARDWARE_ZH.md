# Kona328 与现有智能稻草人的集成

## 已确认的真实接线

下表来自用户提供的完整主控程序，并与本机 `Documents/Arduino/5CCE2EMP_Control_SG90_HC-SR04` 源码一致。四份现有 Arduino 草图已完整复制到 `firmware/originals/`，记录 SHA-256，原目录未修改。

| 部件 | 引脚 |
|---|---|
| HC-SR04 1 | TRIG D2，ECHO D3 |
| HC-SR04 2 | TRIG D12，ECHO D13 |
| PIR 1 / PIR 2 | D4 / A0 |
| Waveshare Sound V2 | DOUT D5，AOUT A1 |
| 共阴 RGB | R D6，G D7，B D8 |
| 右臂 / 左臂舵机 | D9 / D10 |
| 蜂鸣器 | D11 |

**A0 不是本项目的音频输入；D13 不能当测试 LED 输出。** 新增采集固件使用 A1；简单控制固件使用 RGB 的 D7 绿灯。电源及地线仍需对照实体模块检查。Waveshare 的 AOUT 是模拟波形，DOUT 是比较器阈值事件，DOUT 不能提供 MFCC/FFT 所需波形。[厂家说明](https://www.waveshare.com/wiki/Sound_Sensor)

## 四种固件，不能同时刷入

| 草图 | 实际用途 | Flash | 静态 SRAM |
|---|---|---:|---:|
| `originals/5CCE2EMP_Control_SG90_HC-SR04` | 原主控，完整保留 | 12,322 B | 1,767 B |
| `legacy_master_fixed` | 原主控的独立修正版 | 12,370 B | 939 B |
| `uno_audio_capture` | A1 连续录音；关闭动作输出 | 2,422 B | 1,222 B |
| `uno_controller` | 主机事件驱动 D7 LED 测试 | 2,392 B | 247 B |
| `scarecrow_host_ml` | 完整引脚下的主机 ML 控制版本 | 7,634 B | 356 B |

数字来自本机 `arduino:avr:uno` 编译器；未测量运行时栈峰值、电流、采样抖动或真实机械动作。原主控只剩 281 B 给局部变量和中断栈，编译器发出低内存警告。修正版把串口常量字符串放入 Flash 的 `F()`，减少 828 B 静态 SRAM，并将 FFT 使用的名义采样率与 104 μs 采样周期统一。它仍然保留原来的舵机动作行为，上传后可能自动触发，不能把它当作纯采集程序。

## 当前已连接板子的状态

2026-11-21 已枚举到 `/dev/cu.usbmodem1101`，USB VID:PID 为 2341:0043。用户在 Arduino IDE 中将 9600 改为 115200 后，确认出现 `FRAME_START / Audio / FRAME_END`，表明当前运行的是分帧采样协议。这个观察由用户通过 IDE 确认；自动终端访问串口被系统拒绝，界面控制服务也不可用。因此不能把“识别端口”和“编译成功”写成“已自动完成实机测试”。本次未通过代理上传新固件。随后用户在自己的终端运行项目的 capture-legacy，成功采集 30 帧、7,680 点，代理已读取并分析落盘文件；这是真实硬件采集，但不是新固件或动作测试。

现有 `Sound_Frame_Test_03` 在 A1 上按名义 104 μs 周期取 256 点，然后传输文本并 `delay(300)`。它每帧约 26.6 ms，但帧之间有大间隙；不能拼成连续录音，也不足以直接匹配当前 250 ms 分类窗口。`capture-legacy` 专门记录这些帧及质量，不输出伪连续 WAV。

## 路径 A：先验证软件与控制链

主机麦克风 / USB 音频输入 → Mac 上的 37 特征 + RF → 串口命令 → Kona328。

第一阶段选择 `uno_controller`，只验证 D7 绿灯、心跳、800 ms 脉冲和 10 s 冷却。确认后使用 `scarecrow_host_ml`，它保持原有超声波、PIR、RGB、舵机和蜂鸣器引脚，采用非阻塞状态机和分步舵机动作。超声波仍有每次最多 15 ms 的 `pulseIn` 等待，不能称为完全非阻塞硬实时系统。

完整主控默认 **DISARMED**：舵机不 attach，蜂鸣器关闭；只有最近收到 `HEARTBEAT` 才接受 `ARM`。`TRIGGER` 替代声学 FFT 的报警入口；超声波与 PIR 仍可独立触发，日志记录来源。20 秒报警、3 秒冷却保留。心跳超过 1.5 秒消失，或收到 `STOP` / `DISARM`，关闭蜂鸣器并 detach 舵机。停止 PWM 不保证机械结构保持原位，实际机械限位和支撑必须验证。

Python `live` 默认只观察。只有显式给出 `--serial-port` 和 `--enable-actuator` 才发送 `HEARTBEAT/ARM`，随后按判定发送 `TRIGGER`，退出时发送 `STOP`。本次没有执行这个动作模式。串口仅是控制事件，不传 MFCC 或整个模型。

这个版本的 **ML 音频来自主机麦克风**；A1/D5 仅作现有声音传感器遥测。不要把它描述成已用 Waveshare 实时运行分类器。

## 路径 B：用 Waveshare 采集真正的目标域数据

独立的 `uno_audio_capture`：A1 → AVcc 参考 ADC → Timer1 Compare B 触发 → 512 点 uint16 环形缓冲 → 250000 baud 二进制串口 → Mac WAV。

- 时钟 16 MHz，Timer1 /8，TOP 249，名义采样率 8,000 Hz。
- ADC /128 为 125 kHz；预热首次转换后使用定时触发，避免首次转换较长的影响。
- 每个包为 14 字节头 + 256×2 字节采样 + 2 字节 CRC，共 528 字节。约 31.25 包/s，总计 16,500 B/s；250000 baud、8N1 的理论上限为 25,000 B/s。
- 头包含 `SCM1`、uint32 序号、uint16 采样率、点数、累计丢样数，全部小端；CRC 为 CCITT，poly 0x1021，初值 0xffff，覆盖头和采样负载。
- 接收端拒绝丢包、CRC 错误及 ADC 溢出；每次采集使用全新目录。定时器只给出名义采样率，晶振误差及中断行为仍需实测。

**Timer1 与 AVR Servo 库冲突**。采集固件不包含 Servo，D9/D10 不产生舵机脉冲，D11 蜂鸣器保持低电平；不要直接并入完整 Servo 主控。8 kHz 的 Nyquist 为 4 kHz，无法保留 4–4.8 kHz 及更高鸟声。将音频重采样到 9.6 kHz 只能匹配输入格式，不能恢复这些信息。后续应在同样的 8 kHz 前端上重新训练、验证，或升级采集链。

## ATmega328P 的现实限制

UNO 级 ATmega328P 有 2 KB SRAM、32 KB Flash、16 MHz 时钟。[Arduino 官方规格](https://store.arduino.cc/products/arduino-uno-rev3)

当前默认 RF 文件为约 2.40 MB，包含 28,476 个树节点；不是适合 UNO 的模型。仅一个 0.25 秒、9.6 kHz、16-bit 缓冲就需 4,800 B，已经超过全部 SRAM。256 点实部和虚部 float 数组需 2,048 B；再加 Servo、串口缓冲和栈，无法容纳。26×129 的 float Mel 滤波器矩阵还需 13,416 B。Python joblib 也不是 MCU 可执行格式。

可行路线按工作量递增：

1. 当前推荐：Mac 或其他主机做音频分类，Kona328 保留传感器和执行器控制。
2. 若必须使用同一 Waveshare 音频且同时控制舵机：使用独立采集处理单元，或重新设计不占用 Servo Timer1 的采集时序，并实测中断开销。
3. 若必须完全单片机独立：用整数 RMS、少量 Goertzel 频带或小型定点 FFT，重新训练极浅决策树；量化后逐样本验证与主机一致性，再测内存和时延。深度 3 的满二叉树最多 15 个节点，其存储可控制在数百字节，但这只是容量估算，目前没有已验证的嵌入式分类模型。

模拟前端还需检查增益、静态偏置和过载，并设置与采样率相适应的抗混叠低通。原固件 ADC /32 为 500 kHz，超过最高 10-bit 分辨率常用的 50–200 kHz 范围；读值仍是 10-bit 编码，不等于获得完整 10-bit 有效精度。[ATmega328/P 数据手册](https://docs.arduino.cc/resources/datasheets/Atmel-42735-8-bit-AVR-Microcontroller-ATmega328-328P_Datasheet.pdf)

平滑舵机动作不能保证消除供电跌落。应根据两只舵机的峰值电流配置电源、共地及去耦，避免把所有负载直接归因于算法误报；串口掉线、重启和供电干扰应单独记录。
