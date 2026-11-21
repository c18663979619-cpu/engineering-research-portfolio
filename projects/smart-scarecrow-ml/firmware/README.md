# Arduino firmware — original system and ML extensions

**Start here to review the completed school project:** [the original five-sensor master](originals/5CCE2EMP_Control_SG90_HC-SR04/5CCE2EMP_Control_SG90_HC-SR04.ino). It controls the ultrasonic, PIR and FFT sound channels together with two servos, RGB and buzzer. Its source is preserved unchanged.

Each folder is a separate Arduino sketch. Open the `.ino` inside the matching folder in Arduino IDE and select **Arduino UNO** for the Kona328. Only one sketch runs on the board at a time. A sketch name in the IDE does not prove that it is the sketch currently flashed on the board.

## Which sketch serves which purpose?

| Goal | Sketch | Serial baud | Important behavior |
|---|---|---:|---|
| Inspect / restore the school controller | [Original master](originals/5CCE2EMP_Control_SG90_HC-SR04/5CCE2EMP_Control_SG90_HC-SR04.ino) | 9600 | Standalone five-sensor alarm; may move arms and sound the buzzer when triggered |
| Use the separate memory repair | [legacy_master_fixed](legacy_master_fixed/legacy_master_fixed.ino) | 9600 | Same standalone application; lower static SRAM; new revision needs hardware verification |
| Read existing `FRAME_START / Audio / FRAME_END` output | [Sound_Frame_Test_03](originals/Sound_Frame_Test_03/Sound_Frame_Test_03.ino) | 115200 | A1, 256-sample frames with gaps; the current board was observed using this protocol |
| Collect continuous Waveshare audio | [uno_audio_capture](uno_audio_capture/uno_audio_capture.ino) | 250000 | Binary `SCM1` packets; use the Python capture command, not text display; Timer1 reserved for sampling |
| Check the host-to-board event link | [uno_controller](uno_controller/uno_controller.ino) | 115200 | D7 green LED only; heartbeat and cooldown; no servo actuation |
| Integrate host ML events with the full system | [scarecrow_host_ml](scarecrow_host_ml/scarecrow_host_ml.ino) | 115200 | Starts disarmed; `HEARTBEAT` then `ARM`; host-microphone ML, not simultaneous Waveshare PCM inference |

The master sketches using FFT require **Servo** and the compatible **arduinoFFT 2.x** API (`ArduinoFFT<float>`). Consult the includes in each sketch for its actual dependencies. Full wiring is documented in the [hardware case study](../docs/HARDWARE_CASE_STUDY.md).

## 中文：我在 Arduino IDE 里应该用哪份？

- **展示你已经完成的学校作品**：打开 `originals/5CCE2EMP_Control_SG90_HC-SR04/5CCE2EMP_Control_SG90_HC-SR04.ino`。这是你的原始完整主控，不是新 ML 固件。
- **继续当前已连通的声音分帧检查**：保持板子现有程序，串口监视器使用 **115200 baud**。观察到 `FRAME_START / Audio / FRAME_END` 时，无需为了查看数据再刷一次完整主控。
- **以后录制 Waveshare 连续训练数据**：选择 `uno_audio_capture`，配合 Python 二进制采集工具。它会替换板上现有程序，而且不能同时运行 Servo。
- **以后测试 ML 控制整机**：先完成 D7 灯的事件链检查，再使用 `scarecrow_host_ml` 做整机验证。当前模型由 Mac 麦克风取音、Mac 分类，UNO 控制动作。

The original waveform and sensor diagnostic sketches are also retained in [originals](originals/). No new firmware was flashed during the software verification reported here. Uploading a standalone master can restore automatic physical actions; inspect the assembled hardware before choosing that stage.
