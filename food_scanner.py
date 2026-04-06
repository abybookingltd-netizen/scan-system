"""
Live 3D Food Scanner
Scans a food dish using your webcam, tracks captured angles,
reconstructs a 3D point cloud, exports GLB, and uploads to backend.

Requirements:
    pip install opencv-python numpy open3d trimesh requests python-dotenv
"""

import os
import cv2
import json
import shutil
import requests
import numpy as np
import open3d as o3d
import trimesh
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ─── Config ────────────────────────────────────────────────────────────────────

API_URL      = os.getenv("API_URL", "http://localhost:3000").rstrip("/")
SCAN_DIR     = Path("food_scans")
TARGET_SHOTS = 24          # number of frames to capture (8 per ring × 3 rings)
BLUR_THRESH  = 120         # frames below this Laplacian variance are too blurry
MIN_MOVE_PX  = 30          # minimum pixel movement before a new frame is accepted

# Angle zones: (label, horizontal_deg_start, horizontal_deg_end, vertical_level)
# We divide 360° into 8 columns × 3 rows (low / mid / high) = 24 zones
RINGS = ["low", "mid", "high"]
COLS  = 8
ZONES = [(f"{ring}_{col * (360 // COLS)}deg", ring, col * (360 // COLS))
         for ring in RINGS for col in range(COLS)]


# ─── Helpers ───────────────────────────────────────────────────────────────────

def is_blurry(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var() < BLUR_THRESH


def draw_object_overlay(canvas, orb, prev_gray, prev_kps, coverage_mask):
    """
    Draw live feature points and tracked mesh on the object — like a face scanner.
    - Green dots  : ORB feature points detected right now
    - Cyan lines  : matches between current frame and last captured frame
    - Blue tint   : areas already covered (accumulated coverage mask)
    """
    h, w = canvas.shape[:2]
    gray = cv2.cvtColor(canvas, cv2.COLOR_BGR2GRAY)
    kps, des = orb.detectAndCompute(gray, None)

    # Blue coverage tint over already-scanned area
    if coverage_mask is not None and coverage_mask.any():
        tint = canvas.copy()
        tint[coverage_mask > 0] = (180, 80, 0)   # blue-ish tint
        cv2.addWeighted(tint, 0.25, canvas, 0.75, 0, canvas)

    # Draw detected feature points as green dots
    for kp in kps:
        x, y = int(kp.pt[0]), int(kp.pt[1])
        cv2.circle(canvas, (x, y), 2, (0, 255, 80), -1)

    # Draw match lines between current frame and last captured frame
    if prev_gray is not None and prev_kps is not None and des is not None:
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        prev_kp_list, prev_des = prev_kps
        if prev_des is not None and len(prev_des) > 0 and len(des) > 0:
            matches = bf.match(prev_des, des)
            matches = sorted(matches, key=lambda m: m.distance)[:40]
            for m in matches:
                pt1 = tuple(map(int, prev_kp_list[m.queryIdx].pt))
                pt2 = tuple(map(int, kps[m.trainIdx].pt))
                cv2.line(canvas, pt1, pt2, (255, 200, 0), 1)

    # Scanning border pulse (green when enough features, orange when too few)
    border_color = (0, 220, 80) if len(kps) > 80 else (0, 140, 255)
    cv2.rectangle(canvas, (4, 4), (w - 4, h - 4), border_color, 2)

    return canvas, kps, gray


def update_coverage_mask(mask, frame, kps):
    """Paint a small circle around each keypoint into the coverage mask."""
    if mask is None:
        h, w = frame.shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)
    for kp in kps:
        x, y = int(kp.pt[0]), int(kp.pt[1])
        cv2.circle(mask, (x, y), 18, 255, -1)
    return mask


def draw_hud(canvas, captured, total, last_zone, status_msg, zones_done):
    """Draw angle tracker HUD onto the live webcam frame."""
    h, w = canvas.shape[:2]

    # Semi-transparent dark overlay at bottom
    overlay = canvas.copy()
    cv2.rectangle(overlay, (0, h - 160), (w, h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.55, canvas, 0.45, 0, canvas)

    # Progress bar
    bar_w = int((captured / total) * (w - 40))
    cv2.rectangle(canvas, (20, h - 150), (w - 20, h - 125), (60, 60, 60), -1)
    cv2.rectangle(canvas, (20, h - 150), (20 + bar_w, h - 125), (0, 200, 80), -1)
    cv2.putText(canvas, f"Captured: {captured}/{total}", (20, h - 130),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

    # Zone grid (3 rows × 8 cols)
    cell_w, cell_h = 36, 20
    grid_x, grid_y = 20, h - 115
    for i, (zone_id, ring, deg) in enumerate(ZONES):
        row = RINGS.index(ring)
        col = i % COLS
        x1 = grid_x + col * cell_w
        y1 = grid_y + row * cell_h
        color = (0, 200, 80) if zone_id in zones_done else (80, 80, 80)
        cv2.rectangle(canvas, (x1, y1), (x1 + cell_w - 2, y1 + cell_h - 2), color, -1)
        cv2.putText(canvas, str(deg), (x1 + 2, y1 + 13),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.28, (255, 255, 255), 1)

    # Row labels
    for i, ring in enumerate(RINGS):
        cv2.putText(canvas, ring, (grid_x + COLS * cell_w + 5, grid_y + i * cell_h + 13),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180, 180, 180), 1)

    # Status
    cv2.putText(canvas, status_msg, (20, h - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 220, 255), 1)
    if last_zone:
        cv2.putText(canvas, f"Last zone: {last_zone}", (20, h - 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)

    # Controls hint
    cv2.putText(canvas, "SPACE=capture  Q=quit & process  R=reset",
                (w - 370, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)

    return canvas


def estimate_zone(frame_idx, total):
    """
    Map frame index to an angle zone based on capture order.
    User is expected to rotate the dish slowly; we assign zones in order.
    """
    zone_idx = int((frame_idx / total) * len(ZONES)) % len(ZONES)
    return ZONES[zone_idx][0]


def point_cloud_from_frames(frames_dir):
    """
    Build a rough point cloud from captured frames using ORB feature matching
    and triangulation. Returns an Open3D PointCloud.
    """
    print("\n[3D] Loading frames for reconstruction...")
    image_paths = sorted(frames_dir.glob("*.jpg"))

    if len(image_paths) < 6:
        raise ValueError(f"Need at least 6 frames, got {len(image_paths)}")

    orb = cv2.ORB_create(2000)
    bf  = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)

    all_points_3d = []
    all_colors    = []

    # Approximate camera intrinsics (works for most webcams)
    h, w = cv2.imread(str(image_paths[0])).shape[:2]
    focal = 0.9 * w
    cx, cy = w / 2, h / 2
    K = np.array([[focal, 0, cx],
                  [0, focal, cy],
                  [0,     0,  1]], dtype=np.float64)

    prev_img  = cv2.imread(str(image_paths[0]), cv2.IMREAD_GRAYSCALE)
    prev_kp, prev_des = orb.detectAndCompute(prev_img, None)
    prev_color_img = cv2.imread(str(image_paths[0]))

    R_total = np.eye(3)
    t_total = np.zeros((3, 1))

    for i in range(1, len(image_paths)):
        curr_color_img = cv2.imread(str(image_paths[i]))
        curr_img = cv2.cvtColor(curr_color_img, cv2.COLOR_BGR2GRAY)
        curr_kp, curr_des = orb.detectAndCompute(curr_img, None)

        if prev_des is None or curr_des is None or len(prev_des) < 8 or len(curr_des) < 8:
            prev_img, prev_color_img = curr_img, curr_color_img
            continue

        matches = bf.match(prev_des, curr_des)
        matches = sorted(matches, key=lambda m: m.distance)[:200]

        if len(matches) < 8:
            prev_img, prev_kp, prev_des, prev_color_img = curr_img, curr_kp, curr_des, curr_color_img
            continue

        pts1 = np.float32([prev_kp[m.queryIdx].pt for m in matches])
        pts2 = np.float32([curr_kp[m.trainIdx].pt  for m in matches])

        E, mask = cv2.findEssentialMat(pts1, pts2, K, method=cv2.RANSAC, prob=0.999, threshold=1.0)
        if E is None:
            continue

        _, R, t, mask_pose = cv2.recoverPose(E, pts1, pts2, K, mask=mask)

        # Triangulate
        P1 = K @ np.hstack([np.eye(3), np.zeros((3, 1))])
        P2 = K @ np.hstack([R, t])

        pts1_h = pts1[mask_pose.ravel() == 255].T
        pts2_h = pts2[mask_pose.ravel() == 255].T

        if pts1_h.shape[1] < 4:
            continue

        pts4d = cv2.triangulatePoints(P1, P2, pts1_h, pts2_h)
        pts3d = (pts4d[:3] / pts4d[3]).T

        # Filter points in front of both cameras and within reasonable distance
        valid = (pts3d[:, 2] > 0) & (np.linalg.norm(pts3d, axis=1) < 10)
        pts3d = pts3d[valid]

        # Sample colors from previous frame at matched keypoints
        for pt2d in pts1_h.T[valid]:
            px, py = int(pt2d[0]), int(pt2d[1])
            px = np.clip(px, 0, w - 1)
            py = np.clip(py, 0, h - 1)
            bgr = prev_color_img[py, px]
            all_colors.append([bgr[2] / 255, bgr[1] / 255, bgr[0] / 255])

        all_points_3d.extend(pts3d.tolist())

        R_total = R @ R_total
        t_total = R @ t_total + t

        prev_img        = curr_img
        prev_kp         = curr_kp
        prev_des        = curr_des
        prev_color_img  = curr_color_img


        print(f"  Frame {i}/{len(image_paths)-1} — points so far: {len(all_points_3d)}")

    if len(all_points_3d) < 100:
        raise ValueError("Not enough 3D points reconstructed. Try capturing more distinct angles.")

    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(np.array(all_points_3d))
    if all_colors:
        colors_arr = np.array(all_colors[:len(all_points_3d)])
        pcd.colors = o3d.utility.Vector3dVector(colors_arr)

    # Denoise
    pcd, _ = pcd.remove_statistical_outlier(nb_neighbors=20, std_ratio=2.0)
    print(f"[3D] Point cloud: {len(pcd.points)} points after denoising")
    return pcd


def point_cloud_to_glb(pcd, output_path):
    """Convert Open3D point cloud → mesh (Poisson) → GLB."""
    print("[3D] Estimating normals...")
    pcd.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.1, max_nn=30))
    pcd.orient_normals_consistent_tangent_plane(30)

    print("[3D] Running Poisson surface reconstruction...")
    mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(pcd, depth=8)

    # Remove low-density vertices (noise on the surface boundary)
    density_threshold = np.quantile(np.asarray(densities), 0.1)
    vertices_to_remove = np.asarray(densities) < density_threshold
    mesh.remove_vertices_by_mask(vertices_to_remove)
    mesh.compute_vertex_normals()

    print("[3D] Exporting to GLB...")
    vertices  = np.asarray(mesh.vertices)
    triangles = np.asarray(mesh.triangles)
    colors    = np.asarray(mesh.vertex_colors) if mesh.has_vertex_colors() else None

    tm = trimesh.Trimesh(
        vertices  = vertices,
        faces     = triangles,
        vertex_colors = (colors * 255).astype(np.uint8) if colors is not None else None,
    )
    tm.export(str(output_path))
    print(f"[3D] GLB saved: {output_path}  ({output_path.stat().st_size // 1024} KB)")
    return output_path


def upload_to_backend(glb_path, thumbnail_path, dish_name, category, description, price, allergens):
    """POST the GLB and metadata to the Express backend."""
    files = {
        "model": (glb_path.name, open(glb_path, "rb"), "model/gltf-binary"),
    }
    if thumbnail_path and thumbnail_path.exists():
        files["thumbnail"] = (thumbnail_path.name, open(thumbnail_path, "rb"), "image/jpeg")

    data = {
        "name":        dish_name,
        "category":    category,
        "description": description,
        "price":       str(price),
        "allergens":   json.dumps(allergens or []),
    }

    print(f"\n[Upload] Sending to {API_URL}/api/menu ...")
    try:
        r = requests.post(f"{API_URL}/api/menu", files=files, data=data, timeout=60)
        r.raise_for_status()
        item = r.json().get("data", {})
        print(f"[Upload] Done! ID={item.get('id')}  URL={API_URL}{item.get('modelPath')}")
        return item
    except requests.exceptions.ConnectionError:
        print(f"[Upload] ERROR: Cannot reach backend at {API_URL}. Is node server.js running?")
    except requests.exceptions.HTTPError as e:
        print(f"[Upload] HTTP error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        print(f"[Upload] Failed: {e}")
    return None


# ─── Main Scanner ──────────────────────────────────────────────────────────────

def live_scan(dish_name, category="Uncategorized", description="", price=0.0, allergens=None):
    """
    Open webcam, guide user through angle capture with HUD,
    reconstruct 3D point cloud, export GLB, upload to backend.
    """
    # Project folders
    project_dir  = SCAN_DIR / dish_name.replace(" ", "_")
    frames_dir   = project_dir / "frames"
    models_dir   = project_dir / "models"
    output_dir   = project_dir / "output"
    for d in (frames_dir, models_dir, output_dir):
        d.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: Cannot open webcam.")
        return

    captured      = 0
    zones_done    = set()
    last_zone     = ""
    last_frame    = None
    status_msg    = "Place dish in frame. Press SPACE to capture each angle."
    coverage_mask = None
    orb           = cv2.ORB_create(500)
    prev_gray     = None
    prev_kps      = None   # (keypoints, descriptors) of last saved frame

    print(f"\n{'='*60}")
    print(f"  LIVE 3D SCANNER — {dish_name}")
    print(f"  Rotate dish slowly. Capture {TARGET_SHOTS} angles.")
    print(f"  SPACE=capture  Q=finish & process  R=reset")
    print(f"{'='*60}\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        display = frame.copy()

        # ── Real-time object overlay (feature dots, match lines, coverage tint) ──
        display, live_kps, live_gray = draw_object_overlay(
            display, orb, prev_gray, prev_kps, coverage_mask
        )

        # ── Bottom HUD (zone grid, progress bar, status) ──
        display = draw_hud(display, captured, TARGET_SHOTS, last_zone, status_msg, zones_done)
        cv2.imshow("3D Food Scanner", display)

        key = cv2.waitKey(1) & 0xFF

        if key == ord(" "):
            # Check blur
            if is_blurry(frame):
                status_msg = "Too blurry — hold steady and try again."
                continue

            # Check movement (avoid duplicate frames)
            if last_frame is not None:
                diff = cv2.absdiff(
                    cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY),
                    cv2.cvtColor(last_frame, cv2.COLOR_BGR2GRAY)
                )
                if diff.mean() < MIN_MOVE_PX / 10:
                    status_msg = "Too similar to last frame — rotate the dish more."
                    continue

            # Save frame
            fname = frames_dir / f"frame_{captured:04d}.jpg"
            cv2.imwrite(str(fname), frame)

            zone_id  = estimate_zone(captured, TARGET_SHOTS)
            zones_done.add(zone_id)
            last_zone  = zone_id
            last_frame = frame.copy()

            # Update coverage mask & prev keypoints for overlay
            coverage_mask = update_coverage_mask(coverage_mask, frame, live_kps)
            _, desc = orb.detectAndCompute(live_gray, None)
            prev_kps  = (live_kps, desc)
            prev_gray = live_gray

            captured  += 1

            remaining  = TARGET_SHOTS - captured
            status_msg = f"Captured! {remaining} more to go. Keep rotating." if remaining > 0 else "All angles captured! Press Q to process."
            print(f"  Frame {captured}/{TARGET_SHOTS} saved — zone: {zone_id}")

            # Save first frame as thumbnail
            if captured == 1:
                thumb_path = output_dir / "thumbnail.jpg"
                cv2.imwrite(str(thumb_path), frame)

        elif key == ord("r"):
            # Reset
            shutil.rmtree(frames_dir)
            frames_dir.mkdir()
            captured      = 0
            zones_done    = set()
            last_frame    = None
            coverage_mask = None
            prev_gray     = None
            prev_kps      = None
            status_msg = "Reset. Start again — press SPACE to capture."
            print("  Reset. Starting over.")

        elif key == ord("q"):
            if captured < 6:
                print(f"  Need at least 6 frames (have {captured}). Keep scanning.")
                status_msg = f"Need at least 6 frames. Have {captured}."
                continue
            break

    cap.release()
    cv2.destroyAllWindows()

    if captured < 6:
        print("Not enough frames captured. Exiting.")
        return

    # ── 3D Reconstruction ──────────────────────────────────────────────────────
    print(f"\n[3D] Reconstructing from {captured} frames...")
    try:
        pcd      = point_cloud_from_frames(frames_dir)
        glb_path = models_dir / f"{dish_name.replace(' ', '_')}.glb"
        point_cloud_to_glb(pcd, glb_path)
    except Exception as e:
        print(f"[3D] Reconstruction failed: {e}")
        return

    # ── Upload ─────────────────────────────────────────────────────────────────
    thumb_path = output_dir / "thumbnail.jpg"
    upload_to_backend(glb_path, thumb_path, dish_name, category, description, price, allergens)


# ─── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    dish     = input("Dish name: ").strip() or "My Dish"
    category = input("Category (e.g. Main Course): ").strip() or "Uncategorized"
    desc     = input("Description: ").strip()
    price    = float(input("Price (e.g. 12.99): ").strip() or "0")
    raw_all  = input("Allergens comma-separated (e.g. gluten,dairy): ").strip()
    allergens = [a.strip() for a in raw_all.split(",")] if raw_all else []

    live_scan(dish, category, desc, price, allergens)
