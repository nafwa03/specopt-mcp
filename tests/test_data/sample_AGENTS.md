# Gardin

YOLO-based object tracker for YouTube live streams and local video. Single-file Python app (`main.py`).

## Setup

```bash
python -m venv venv && venv\Scripts\activate  # Windows
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu  # AMD/unsupported GPU workaround
pip install -r requirements.txt
```

ffmpeg required for `cap-from-youtube` stream reliability.

## Run

```bash
python main.py                                    # Default stream, class 0 (person)
python main.py --class-id 14                      # Track birds
python main.py --class-id 21,23                    # Track bears AND giraffes
python main.py --model guinea-pig-detector.pt --url guinea_pig.mp4  # Local video + custom model
python main.py --list-classes                      # Print all COCO classes
```

## Key facts for editing

- **`main.py` is the live code.** `main2.py` is a frozen older version (penguin-only, no argparse, hardcoded `best.pt`). Don't edit `main2.py`.
- **`--class-id` default is `"0"`** (person) — this overrides `PenguinTracker.__init__` which sets `active_classes = {14}`. The argparse value wins at `main.py:771-772`.
- **Architecture is single-file:** `PenguinTracker` (YOLO inference, tracking, zone state), `PenguinTrackerUI` (OpenCV window, mouse/keyboard, rendering), `TrackingZone`/`TrackedObject` (dataclasses).
- **No tests, no linter, no CI, no git repo.** Verify changes by running the app.
- **Custom `.pt` models in repo root:** `best.pt`, `guinea-pig-detector.pt`, `guinea-pig-improved.pt`, `yolov8n.pt`. These are large binary files — don't try to read or diff them.
- **Visual tracker fallback chain:** CSRT → legacy CSRT → MIL (`init_visual_tracker` at `main.py:346-357`). Only activates for user-selected objects when YOLO loses them.
- **Segmentation support:** `--highlight` enables mask overlay; requires a seg model (e.g. `yolov8n-seg.pt`) for instance masks, falls back to bbox highlighting.
- **Dataset dirs** (`guinneapigs/`, `Guinea Pig Detection.v1i.yolov8/`, `Guinea Pig Breeds.v14-orig.yolov8/`, `datasets/`) are darknet/YOLOv8 training data, not Python packages.

## Training custom models

```bash
python train_fish.py --dataset deepfish --epochs 100 --imgsz 608
# Output: runs/train/fish-detector/weights/best.pt
# Then: python main.py --model runs/train/fish-detector/weights/best.pt
```

`train_fish.py` handles two dataset layouts: nested-by-location (DeepFish) and flat darknet (`obj_train_data/` + `train.txt`/`test.txt`).

## Design reference

`docs/plans/2026-04-04-iot-yolo-platform-design.md` — future IoT platform expansion plans.
