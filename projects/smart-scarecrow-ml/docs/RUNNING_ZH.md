# 本地运行指南

所有命令在项目根目录执行，使用现有 Python 3.12 `.venv`。所有新结果采用独立目录；同名输出存在时程序报错，避免覆盖。原来的根目录脚本作为实验历史保留，建议使用下面的统一入口。

```bash
cd ~/Documents/Smart-Scarecrow-ML
source .venv/bin/activate
python -m scarecrow --help
python -m pytest -q
```

## 1. 原有数据实验

```bash
python -m scarecrow run --demo-model
```

读取 `data/manifest.csv` 中两段已经裁剪好的 1.4 秒 WAV。`start_sec/end_sec` 用于记录父音频坐标，不会再次裁剪。原始 `data/labels.csv` 保持原样。每段得到 5 个完整 0.25 秒窗口，尾部 0.15 秒不填充、不用于训练。

仅每类一个录音来源，独立评估不成立。因此默认不训练模型；`--demo-model` 明确允许生成演示模型，其 Accuracy、Precision、Recall、F1 和混淆矩阵仍为 N/A。

## 2. 公开音频实验

本机已经下载完成，不需要再次下载。新克隆的代码需先执行下载脚本；它仅从固定版本的 ESC-50 官方仓库获取真实文件，保存许可、原作者、原录音 ID 和哈希。

```bash
python scripts/download_esc50_subset.py
python -m scarecrow run --manifest data/manifest_esc50.csv
python -m scarecrow run --manifest data/manifest_esc50.csv --calibrate
```

如果清单和音频已存在，下载脚本核对内容及哈希，不覆盖文件；源码包没有音频时，它补下载固定版本的文件，并核对附带的哈希。发现不一致会报错，不替换已有数据。

已有完整运行：

- `results/runs/20261121_local_sources/`：私有的原有两条来源，演示模型。
- `results/runs/20261121_esc50_fold5/`：1–4 折训练，5 折独立测试。
- `results/runs/20261121_esc50_low_fpr/`：1–3 折训练，4 折选阈值，5 折独立测试。

每次运行保存 `features.csv`、`dataset_audit.json`、`evaluation.json`、`run_config.json`、模型卡及图表。有独立划分时还保存 `split_assignment.csv` 和每个测试窗口、测试片段的预测，便于核查泄漏和复算指标。

## 3. 单文件推理

```bash
python -m scarecrow predict \
  --audio data/processed/bird/bird_001_segment.wav \
  --model results/runs/20261121_esc50_fold5/model_holdout.joblib \
  --output results/predictions/my_bird_check.json
```

输出包含每个窗口的 Bird 分数、判定、FFT 判定及 RMS。`bird_score` 是未经概率校准的树投票分数，不是准确率。`known_training_file` 仅检查文件哈希；换编码或裁剪仍可能来自训练录音。仅加载可信本地 joblib，反序列化不可信文件可能执行代码。

演示模型必须显式添加 `--allow-demo`，并且程序禁止它驱动执行器。

## 4. 新音频裁剪及标注

```bash
python -m scarecrow segment --audio path/to/source.wav \
  --start 1.9 --end 3.3 --output data/processed/new_unique_clip.wav
```

支持 soundfile 能解码的 WAV、FLAC、MP3 等；M4A 可在 Mac 上先用系统 `afconvert` 转为新 WAV，保留原始文件：

```bash
afconvert -f WAVE -d LEI16 data/raw/your_recording.m4a data/processed/your_recording_new.wav
```

手动听审后，以 `data/manifest_template.csv` 的字段建立新的清单。相同原始录音的片段、重采样、增益变换和增强样本必须共用 `source_recording` / `source_group`。同一采集地点、同一天或同一播放会话相关性很强时，用更保守的同一 `source_group`。标签只允许 `bird` / `non_bird`；不确定的样本标 `label_verified=no`，不会进入训练。未知许可写 `unverified`，不要凭空填许可。

`original_path` 是本机可用的父音频，`start_sec/end_sec` 是相对该父文件的坐标。对 ESC-50，这个父文件本身是五秒裁剪片段，其更早的 Freesound 原录音偏移未知，来源 ID 仍保持一致分组。

## 5. 现有 CSV 审计

```bash
python -m scarecrow audit-legacy --output results/legacy_check_new.json
python scripts/check_originals.py
```

旧 CSV 的三帧均含 256 个 10-bit ADC 值，但没有时间戳和真实采样率。后来找到的旧采集源码指定 104 微秒名义间隔，ADC 使用 /32 加速。源码参数不是实测采样率；新审计不把不连续帧拼接成连续 WAV。

## 6. 声音传感器串口录音

当前板子使用 115200 baud 的旧文本协议，可关闭 IDE 串口监视器后执行：

```bash
python -m scarecrow capture-legacy --port /dev/cu.usbmodem1101 --frames 30 --output data/captures/new_unique_legacy_session
```

它保存独立帧，不拼接为 WAV。若要连续采集，使用 A1 的独立 `uno_audio_capture.ino`；它与旧协议不同，Timer1 不能和 Servo 同时使用。

```bash
python -m serial.tools.list_ports -v
python -m scarecrow capture --port /dev/cu.YOUR_ACTUAL_PORT \
  --seconds 5 --timeout 30 --output data/captures/session_unique_001
```

程序保存未标注的 8 kHz WAV、包序号和采集元数据；CRC 错误、丢包或采样溢出会中止并记录错误，不会伪造连续采样。`--output` 必须是新目录。采集完成后需要听审、标注来源，再加入训练；不要把传感器测试噪声自动标为 Non-bird。

## 7. Mac 麦克风实时推理

```bash
python -m scarecrow live \
  --model results/runs/20261121_esc50_fold5/model_holdout.joblib \
  --seconds 20 --sample-rate 48000 --output results/predictions/live_unique.json
```

首次可能需要 macOS 麦克风权限；本次没有自动录制私人环境声音。默认只打印和记录结果。需要其他设备时先用 `python -m sounddevice` 查看设备，`--device` 传设备名称。

`--serial-port ... --enable-actuator` 才允许发送 `HEARTBEAT` / `ARM` / `TRIGGER` / `STOP`。先使用 `uno_controller` 验证 D7 绿灯，再考虑完整 `scarecrow_host_ml`；其默认不驱动舵机，ARM 后才启用。该开关只允许技术上已做来源留出测试的模型，不代表已证明适合实地驱鸟。现阶段建议持续使用不连接执行器的观察模式。

实时策略固定为：分数至少达到 `max(0.8, model_threshold)`、RMS ≥ 0.005、连续三次阳性，动作后冷却 10 秒。这个组合策略没有在实地事件级数据上评估，不可将表中的单窗口指标视为真实动作效果。

## 8. 验证和固件编译

```bash
python scripts/validate_project.py --output work/validation_unique
```

脚本运行软件测试、依赖检查、原始文件校验，并在找到 Arduino CLI 时编译四份新增或修正版 UNO 固件；它不会上传固件。安装 Arduino IDE 的这台 Mac 已具备 `arduino:avr:uno` 编译环境。首次上传前务必保留板上既有固件或源代码，核对执行器引脚及驱动电路。
