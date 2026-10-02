from pathlib import Path

LABEL_DIR = Path("data/yolo/raw/train/labels")

ROAD_DAMAGE_IDS = {0, 1, 3, 4, 5}
POTHOLE_ID = 6

pothole_images = set()
road_damage_images = set()
both_images = set()

for label_file in LABEL_DIR.glob("*.txt"):

    ids = set()

    with open(label_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            class_id = int(line.split()[0])
            ids.add(class_id)

    has_pothole = POTHOLE_ID in ids
    has_road_damage = bool(ids & ROAD_DAMAGE_IDS)

    if has_pothole:
        pothole_images.add(label_file.stem)

    if has_road_damage:
        road_damage_images.add(label_file.stem)

    if has_pothole and has_road_damage:
        both_images.add(label_file.stem)


combined_images = pothole_images | road_damage_images

print("=" * 50)
print("CIVICBRAIN RDD2022 OVERLAP ANALYSIS")
print("=" * 50)

print(f"Pothole images       : {len(pothole_images)}")
print(f"Road Damage images   : {len(road_damage_images)}")
print(f"Both                 : {len(both_images)}")
print(f"Combined unique      : {len(combined_images)}")

print("\nAnalysis completed.")
print("No images or labels were modified.")