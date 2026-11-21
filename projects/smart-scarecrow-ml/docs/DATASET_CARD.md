# Dataset card

## Local recordings

The original project contains 2 raw recordings, 6 WAV derivatives, 2 annotated intervals, a 768-row ADC frame CSV, and a 20-row serial connectivity CSV. The source recordings are `XC1002645` and `SELF_VOICE_001`. The two verified flags are inherited from the original `labels.csv`; the agent did not independently listen to and relabel the recordings.

The annotated Bird and Non-bird WAVs are mono PCM16 at 9,600 Hz and 1.4 seconds each. DC-centered RMS is 0.019526 and 0.034292 respectively, so the Non-bird example is louder. Neither has samples reaching the clipping threshold. No claim of calibrated sound pressure level or SNR is made.

The XC MP3 ID3 tags identify W. Agster and link to XC1002645. The source page denied automated access, so its exact license remains unverified. The self-voice label is a provenance claim from existing metadata; participant consent and ownership remain for the owner to confirm. No local private audio was uploaded.

Full WAV derivatives are not counted as new independent recordings. Only the existing annotated intervals enter the local experiment. Original ADC frames remain unlabeled and are excluded from supervised training.

## ESC-50 research subset

Source: [Karol J. Piczak's ESC-50 repository](https://github.com/karolpiczak/ESC-50), pinned commit `33c8ce9eb2cf0b1c2f8bcf322eb349b6be34dbb6`. Repository-level metadata and per-clip source attribution were checked before downloading. See `third_party/esc50/` for exact snapshots and SHA-256 records.

- Downloaded 160 genuine WAV files, 70,567,040 bytes, 800 seconds total.
- Positive class: all 40 `chirping_birds` and all 40 `crow` clips.
- Negative class: 2 clips per category per official fold, from rain, wind, crickets, engine, vacuum cleaner, footsteps, clapping and helicopter (80 clips).
- Selection seed: 42. Obvious mentions of bird/crow/rooster in negative source descriptions were excluded before sampling.
- No generated audio, synthetic samples or augmentation were added to the real dataset. Synthetic unit-test tones are temporary software fixtures only.

Quality checks run before training using the same fixed thresholds. Two clips (`1-46744-A-36`, `3-130330-A-22`) have more than 1% near-full-scale or overloaded samples after preprocessing and are excluded. Resampling may introduce overshoot, so this flag is a conservative preprocessing-quality screen, not proof of original ADC clipping. Retained: 158 clips, 790 seconds, 80 Bird and 78 Non-bird clips, 132 recording groups, 3,160 windows.

These labels describe the dominant five-second sound event; they do **not** certify that every 250 ms window contains a bird, or that background birds are absent from negative clips. Listen/reannotate intervals before event-level field evaluation. The selected negative classes do not include speech, which helps explain the poor transfer to the owner's voice clip. Public-data label verification means agreement with the upstream annotation, not independent listening.

## Splits and leakage controls

`source_recording = source_group = FREESOUND_<src_file>` preserves the upstream original recording ID across different ESC takes. Official fold 5 is the fixed test set; folds 1–4 train the default model. The threshold experiment uses folds 1–3 for fitting, fold 4 for selecting a threshold, and fold 5 for testing, without refitting. Exact copied originals and decoded clips are additionally merged by hashes; conflicting labels on identical decoded clips fail validation.

The parser retains original groups in every child window and refuses source overlap across official partitions. Source metadata is still essential: exact hashing cannot discover all cropped, transcoded or acoustically related files. Shared recordists, sites and sessions can create residual correlations even when Freesound IDs differ. A future field test must group by recording session/day/location as appropriate.

There are only 28 original source groups in the test set. The 640 windows are correlated, so neither 640 independent trials nor a narrow independent-binomial confidence interval is claimed. Report both window and clip metrics with their denominators. These custom binary results are not comparable to published ESC-50 50-class scores.

## License and redistribution

The official dataset is offered under CC BY-NC 3.0, with individual source credits and license tags in its LICENSE. The download manifest retains original creator links; transformations consist of mono mixing, polyphase resampling and feature extraction. The source audio is ignored by Git. No public upload or GitHub publication occurred. Commercial use and future redistribution must be reviewed against the dataset and per-source terms; a code license does not license the audio.

## Next collection priorities

Collect independently recorded, reviewed clips from the actual Waveshare front end: multiple bird species and distances, human speech, crickets, wind, rain, motor/servo/buzzer noise, footsteps, farm machinery and quiet scenes. Record device, gain, location, date/session, rate, source permissions and exact annotation intervals. Keep entire sessions on one side of a split. Reserve a new site/day for the final untouched test; report false alarms per hour and missed bird events as well as F1. More windows cut from one recording do not replace more recording sources.
