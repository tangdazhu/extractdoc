# -*- coding: utf-8 -*-
"""
本脚本用于从视频文件中提取关键帧快照，并对生成的快照进行去重处理。

主要功能包括：
1. 视频场景检测与快照提取 (extract_snapshots 函数):
   - 使用 PySceneDetect库 (ContentDetector) 来检测视频中的场景切换。
   - 为每个检测到的场景的起始帧保存一张图片快照。
   - 关键参数：`scene_detector_threshold` (场景检测器阈值)
     - 作用：控制场景检测的灵敏度。此值为内容检测器 (ContentDetector) 的阈值。
     - 较低的值 (例如 5.0, 10.0) 会使检测器更敏感，从而检测到更多的场景变化，
       可能会将一个缓慢变化的逻辑幻灯片或场景分割成多个小片段。
     - 较高的值 (例如 25.0, 30.0, 35.0) 会使检测器不那么敏感，通常用于检测较明显的场景切换。
     - 调整建议：根据视频内容的特性进行调整。对于PPT演示或变化较慢的视频，
       如果希望捕捉到每个微小变化后的最完整状态，可以先尝试较低的阈值以生成更多原始截图，
       然后依赖后续的去重步骤来筛选。

2. 快照去重 (deduplicate_slide_screenshots 函数结合 get_theme_from_snapshot_coarse):
   - 背景：当 `scene_detector_threshold` 设置较低时，可能会产生大量内容相似的连续截图，
     这些截图可能对应同一个逻辑幻灯片或内容主题的不同演进阶段。
   - 目的：从这些密集的截图中，为每个"逻辑幻灯片主题"筛选出最具代表性的一张 (通常是内容演进的最后一张)。
   - 实现方式：通过 `get_theme_from_snapshot_coarse` 函数对原始截图进行粗粒度的主题分组。
     它将 PySceneDetect 生成的连续多个细分场景（由文件名中的 `scene_XXX` 编号体现）
     合并为一个逻辑主题组。
   - 关键参数：`group_size` (在 `if __name__ == "__main__":` 部分调用时配置)
     - 作用：定义了多少个连续的 PySceneDetect 细分场景应被视为一个"逻辑幻灯片主题"组。
       例如，如果 `group_size=5`，则 `scene_001` 到 `scene_005` (基于它们的文件名提取的场景号)
       将被视为第一个逻辑主题组，`scene_006` 到 `scene_010` 为第二个，以此类推。
     - 调整建议：
       - 如果去重后保留的截图仍然过多，感觉很多相似内容没有被合并，可以尝试【增大】`group_size` 的值
         (例如从 5 改为 8, 10, 或 15)。
       - 如果去重后发现一些本应独立的逻辑幻灯片被错误地合并了，导致部分内容丢失，
         可以尝试【减小】`group_size` 的值 (例如从 5 改为 3 或 2)。
       - 此参数的效果高度依赖于视频内容以及 `scene_detector_threshold` 的设置，
         通常需要根据实际输出的去重结果进行多次试验性调整。
   - 去重规则：在每个通过 `group_size` 定义的"逻辑幻灯片主题"组内，脚本会选取该组中
     原始帧号 (文件名中的 `frame_YYYYY`) 最大的那张截图作为该逻辑主题的代表。
     这符合"同一主题下肯定是最后一个截图的内容最多和最好"的假设。

使用流程：
1. 配置 `video_file` 指定输入视频路径。
2. （可选）调整 `detection_threshold` (场景检测阈值) 以控制初始截图的生成密度。
3. （可选）在脚本末尾的 `if __name__ == "__main__":` 部分，调整调用 `deduplicate_slide_screenshots` 时
   传递给 `get_theme_from_snapshot_coarse` 的 `group_size` 参数，以优化去重效果。
4. 运行脚本。初始截图会保存在 `video-snapshot` 子目录中。
5. 去重后的精华截图会保存在 `video-snapshot-duplicate` 子目录中。
"""
import cv2
import os
from scenedetect import VideoManager, SceneManager
# Detectors:
from scenedetect.detectors import ContentDetector # For finding fast cuts using changes in content.
# from scenedetect.detectors import ThresholdDetector # For finding fast cuts based on a threshold.
import re
import shutil # 用于文件复制
import argparse # 新增 argparse
import sys # Added for sys.exit
import numpy as np
from PIL import Image
import imagehash

# tqdm is a great library for progress bars if you process many/long videos
# from tqdm import tqdm

def extract_snapshots(video_path, output_dir, scene_detector_threshold=27.0):
    """
    Analyzes a video, detects scene changes, and saves a snapshot
    from the beginning of each detected scene.

    Args:
        video_path (str): Path to the input video file.
        output_dir (str): Directory to save the snapshots.
        scene_detector_threshold (float): Threshold for the ContentDetector.
                                          Lower values detect more scenes. Tune as needed.
    """
    print(f"INFO: Starting snapshot extraction for video: {video_path}", flush=True)
    print(f"INFO: Snapshots will be saved to: {output_dir}", flush=True)

    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"INFO: Created output directory: {output_dir}", flush=True)

    try:
        video_manager = VideoManager([video_path])
        scene_manager = SceneManager()

        # Add ContentDetector to detect scene changes.
        # You can also try ThresholdDetector for different results/performance.
        # scene_manager.add_detector(ThresholdDetector(threshold=12, min_scene_len=15))
        scene_manager.add_detector(ContentDetector(threshold=scene_detector_threshold))

        # Get an 8-bit BGR OpenCV VideoCapture object.
        # video_manager.set_downscale_factor(1) # Default is 1 (no downscaling)
        video_manager.start()

        # Perform scene detection on video_manager.
        print("INFO: Detecting scenes...", flush=True)
        scene_manager.detect_scenes(frame_source=video_manager, show_progress=False)

        # scene_list will be a list of tuples (start_timecode, end_timecode)
        scene_list = scene_manager.get_scene_list()
        print(f"INFO: Detected {len(scene_list)} scenes.", flush=True)

        if not scene_list:
            print("INFO: No scenes detected in the video.", flush=True)
            return

        # Create a new VideoCapture object to extract frames by number,
        # as PySceneDetect's VideoManager might be optimized for sequential access.
        print("INFO: Opening video with OpenCV for frame extraction...", flush=True)
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"ERROR: Could not open video file {video_path} with OpenCV for frame extraction.", flush=True)
            return
            
        fps = cap.get(cv2.CAP_PROP_FPS)
        print(f"INFO: Video FPS: {fps}", flush=True)

        snapshot_count = 0
        total_scenes = len(scene_list)
        print(f"INFO: Starting to save snapshots for {total_scenes} scenes...", flush=True)
        for i, (start_time, end_time) in enumerate(scene_list):
            # start_time and end_time are FrameTimecode objects.
            # We want to get the frame at the beginning of the scene.
            start_frame_num = start_time.get_frames()
            
            # To get a frame slightly after the cut, you can add a small offset
            # For PPTs, the first frame of the scene is usually what we want.
            # frame_to_extract = start_frame_num + int(fps * 0.1) # e.g., 0.1s after cut

            # print(f"Scene {i+1:03d}: Starts at frame {start_frame_num} ({start_time.get_timecode()})") # COMMENTED OUT - too verbose for many scenes
            if (i + 1) % 10 == 0 or (i + 1) == total_scenes: # ADDED: Log progress every 10 scenes or for the last scene
                print(f"INFO: Processing scene {i+1}/{total_scenes}, Start frame: {start_frame_num}", flush=True) # ADDED

            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame_num)
            ret, frame = cap.read()

            if ret:
                snapshot_filename = f"snapshot_scene_{i+1:03d}_frame_{start_frame_num}.jpg"
                snapshot_path = os.path.join(output_dir, snapshot_filename)
                try: # ADDED: try-except for imwrite
                    cv2.imwrite(snapshot_path, frame)
                    # print(f"  Saved: {snapshot_path}") # COMMENTED OUT - too verbose
                    snapshot_count += 1
                except Exception as e_imwrite: # ADDED
                    print(f"ERROR: Could not write snapshot {snapshot_path}. Error: {e_imwrite}", flush=True) # ADDED
            else:
                print(f"ERROR: Could not read frame {start_frame_num} for scene {i+1:03d}.", flush=True) # MODIFIED
        
        print(f"INFO: Snapshot saving loop finished. Attempting to release OpenCV VideoCapture.", flush=True) # ADDED
        cap.release()
        print(f"INFO: OpenCV VideoCapture released.", flush=True) # ADDED
        print(f"INFO: Extraction complete. Saved {snapshot_count} snapshots.", flush=True) # MODIFIED

    except Exception as e:
        print(f"ERROR: An error occurred during extract_snapshots: {e}", flush=True) # MODIFIED
    finally:
        # For PySceneDetect v0.6.x and later, simply call release.
        # The is_started() method check is not needed / available.
        print("INFO: In finally block of extract_snapshots. Attempting to release VideoManager.", flush=True) # ADDED
        if 'video_manager' in locals() and hasattr(video_manager, '_started') and video_manager._started: # MODIFIED
            video_manager.release()
            print("INFO: VideoManager released.", flush=True) # ADDED
        else: # ADDED
            print("INFO: VideoManager was not found, not started, or does not have _started attribute; no release needed or possible.", flush=True) # MODIFIED

def get_theme_from_snapshot(filepath):
    """
    从截图文件路径中提取主题ID (e.g., 'scene_004').
    """
    filename = os.path.basename(filepath)
    match = re.search(r"(scene_\d+)_frame_\d+\.jpg", filename)
    if match:
        return match.group(1) # 返回 'scene_XXX'
    return None

def get_order_key_from_snapshot(filepath):
    """
    从截图文件路径中提取排序键 (帧号).
    """
    filename = os.path.basename(filepath)
    match = re.search(r"scene_\d+_frame_(\d+)\.jpg", filename)
    if match:
        return int(match.group(1)) # 返回帧号的整数形式
    return 0 # 如果匹配失败，返回一个默认值

def calculate_image_sharpness(image_path):
    """
    计算图像清晰度（使用Laplacian方差）。
    值越大表示图像越清晰。
    """
    try:
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return 0.0
        # 使用Laplacian算子计算图像清晰度
        laplacian_var = cv2.Laplacian(img, cv2.CV_64F).var()
        return laplacian_var
    except Exception as e:
        print(f"WARNING: Failed to calculate sharpness for {image_path}: {e}", flush=True)
        return 0.0

def calculate_content_density(image_path, threshold=30):
    """
    计算图像的内容密度（非背景像素的比例）。
    用于判断渐进式PPT中哪一帧内容最多。
    
    Args:
        image_path: 图像文件路径
        threshold: 二值化阈值，低于此值视为背景
    
    Returns:
        内容密度（0-1之间的浮点数），值越大表示内容越多
    """
    try:
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return 0.0
        
        # 二值化：将接近白色的像素视为背景
        _, binary = cv2.threshold(img, 240, 255, cv2.THRESH_BINARY_INV)
        
        # 计算非背景像素的比例
        content_pixels = np.count_nonzero(binary)
        total_pixels = binary.size
        density = content_pixels / total_pixels if total_pixels > 0 else 0.0
        
        return density
    except Exception as e:
        print(f"WARNING: Failed to calculate content density for {image_path}: {e}", flush=True)
        return 0.0

def calculate_perceptual_hash(image_path, hash_size=16):
    """
    计算图像的感知哈希（pHash）。
    
    Args:
        image_path: 图像文件路径
        hash_size: 哈希大小，越大越精确但计算越慢
    
    Returns:
        imagehash.ImageHash对象，如果失败返回None
    """
    try:
        img = Image.open(image_path)
        # 使用感知哈希（对旋转、缩放、亮度变化更鲁棒）
        phash = imagehash.phash(img, hash_size=hash_size)
        return phash
    except Exception as e:
        print(f"WARNING: Failed to calculate hash for {image_path}: {e}", flush=True)
        return None

def deduplicate_by_similarity(screenshot_list, similarity_threshold=5, min_group_interval=3):
    """
    基于图像相似度的智能去重。
    
    策略：
    1. 使用感知哈希计算图像相似度
    2. 相似的图像（哈希距离 < threshold）归为一组
    3. 每组保留清晰度最高的图像
    4. 确保相邻保留的图像之间至少间隔min_group_interval个场景
    
    Args:
        screenshot_list: 截图文件路径列表（已按场景顺序排序）
        similarity_threshold: 哈希距离阈值，越小越严格（推荐3-8）
        min_group_interval: 同一组内最小场景间隔，避免过度去重
    
    Returns:
        去重后的截图列表
    """
    print(f"INFO: Starting similarity-based deduplication for {len(screenshot_list)} screenshots.", flush=True)
    print(f"INFO: Similarity threshold: {similarity_threshold}, Min group interval: {min_group_interval}", flush=True)
    
    if not screenshot_list:
        return []
    
    # 计算所有图像的哈希值、清晰度和内容密度
    image_data = []
    for i, img_path in enumerate(screenshot_list):
        phash = calculate_perceptual_hash(img_path)
        sharpness = calculate_image_sharpness(img_path)
        content_density = calculate_content_density(img_path)
        scene_num = get_scene_number_from_path(img_path)
        
        if phash is not None:
            image_data.append({
                'path': img_path,
                'hash': phash,
                'sharpness': sharpness,
                'content_density': content_density,
                'scene_num': scene_num,
                'index': i
            })
        else:
            print(f"WARNING: Skipping {img_path} due to hash calculation failure.", flush=True)
    
    if not image_data:
        print("WARNING: No valid images to deduplicate.", flush=True)
        return []
    
    print(f"INFO: Successfully processed {len(image_data)} images for deduplication.", flush=True)
    
    # 动态分组：相似的图像归为一组
    groups = []
    used = set()
    
    for i, img_data in enumerate(image_data):
        if i in used:
            continue
        
        # 创建新组
        current_group = [img_data]
        used.add(i)
        
        # 查找相似的图像
        for j in range(i + 1, len(image_data)):
            if j in used:
                continue
            
            # 计算哈希距离
            hash_distance = img_data['hash'] - image_data[j]['hash']
            
            # 如果相似度足够高，加入当前组
            if hash_distance <= similarity_threshold:
                current_group.append(image_data[j])
                used.add(j)
        
        groups.append(current_group)
        
        # 每处理20个图像输出一次进度
        if (i + 1) % 20 == 0 or (i + 1) == len(image_data):
            print(f"INFO: Processed {i+1}/{len(image_data)} images, found {len(groups)} groups so far.", flush=True)
    
    print(f"INFO: Grouped {len(image_data)} images into {len(groups)} similarity groups.", flush=True)
    
    # 从每组中选择最佳图像
    # 策略：优先选择内容最多的（处理渐进式PPT），其次选择场景编号最大的（最后出现的）
    selected_images = []
    for group_idx, group in enumerate(groups):
        # 首先按内容密度排序（降序），然后按场景编号排序（降序）
        # 这样可以选择内容最完整的那一帧
        group_sorted = sorted(group, key=lambda x: (x['content_density'], x['scene_num']), reverse=True)
        best_image = group_sorted[0]
        
        selected_images.append(best_image)
        
        if len(group) > 1:
            # 显示组内所有图像的信息，帮助调试
            group_info = ", ".join([f"scene_{img['scene_num']:03d}(d:{img['content_density']:.2f})" for img in group])
            print(f"INFO: Group {group_idx+1}: {len(group)} similar images [{group_info}], selected scene_{best_image['scene_num']:03d} (density: {best_image['content_density']:.3f})", flush=True)
    
    # 按原始顺序排序
    selected_images.sort(key=lambda x: x['index'])
    
    # 应用最小间隔过滤，避免保留过于密集的截图
    final_images = []
    last_scene_num = -999
    
    for img_data in selected_images:
        scene_num = img_data['scene_num']
        
        # 如果与上一个保留的场景间隔足够大，则保留
        if scene_num - last_scene_num >= min_group_interval:
            final_images.append(img_data['path'])
            last_scene_num = scene_num
        else:
            print(f"INFO: Skipping scene_{scene_num:03d} due to min_group_interval constraint (last: {last_scene_num}).", flush=True)
    
    print(f"INFO: Similarity-based deduplication finished. Original: {len(screenshot_list)}, After grouping: {len(selected_images)}, Final: {len(final_images)}.", flush=True)
    
    return final_images

def get_scene_number_from_path(filepath):
    """
    从文件路径中提取场景编号。
    """
    filename = os.path.basename(filepath)
    match = re.search(r"scene_(\d+)_frame_\d+\.jpg", filename)
    if match:
        return int(match.group(1))
    return 0

def get_theme_from_snapshot_coarse(filepath, group_size=10):
    """
    从截图文件路径中提取粗粒度的主题ID。
    例如，将 scene_001 到 scene_009 映射到同一个主题组。
    
    注意：此函数已被 deduplicate_by_similarity 替代，保留用于向后兼容。
    """
    filename = os.path.basename(filepath)
    match_scene = re.search(r"scene_(\d+)_frame_\d+\.jpg", filename)
    if match_scene:
        scene_number = int(match_scene.group(1))
        # scene_number 是从1开始的 (因为来自于 enumerate(scene_list) 的 i+1)
        # 为了使分组从0开始，或者更直观，可以 (scene_number - 1) // group_size
        coarse_theme_group = (scene_number - 1) // group_size 
        return f"logical_slide_group_{coarse_theme_group}"
    # 如果文件名不匹配预期的 "scene_XXX_frame_YYY.jpg" 格式，
    # 或者无法提取场景编号，则返回一个基于文件名的独特主题，以避免错误合并。
    # 或者直接返回 None，让 deduplicate_slide_screenshots 函数中的逻辑跳过它。
    # 这里选择返回 None，如果无法分组，则该文件不会参与此种方式的去重。
    return None

def deduplicate_slide_screenshots(screenshot_list, func_get_theme, func_get_order_key):
    """
    根据"幻灯片主题"对截图进行去重，并保留每个主题的"最后一张"。
    """
    print(f"INFO: Starting deduplication for {len(screenshot_list)} screenshots.", flush=True)
    latest_screenshots_by_theme = {}

    for i, screenshot_item in enumerate(screenshot_list):
        theme_id = func_get_theme(screenshot_item)
        order_key = func_get_order_key(screenshot_item)

        if theme_id is None:
            print(f"WARNING: Could not determine theme for {screenshot_item}, skipping.", flush=True)
            continue

        if (i + 1) % 20 == 0 or (i + 1) == len(screenshot_list):
            print(
                f"INFO: Deduplicating screenshot {i+1}/{len(screenshot_list)}: {os.path.basename(screenshot_item)} -> Theme: {theme_id}, OrderKey: {order_key}",
                flush=True,
            )

        current_latest_order_key = latest_screenshots_by_theme.get(theme_id, (None, -1))[1]

        if order_key > current_latest_order_key:
            latest_screenshots_by_theme[theme_id] = (screenshot_item, order_key)

    deduplicated_list = [item for item, key in latest_screenshots_by_theme.values()]
    print(
        f"INFO: Deduplication finished. Original: {len(screenshot_list)}, Deduplicated: {len(deduplicated_list)}.",
        flush=True,
    )
    return deduplicated_list

def main(args):
    # Setup output directories
    base_output_dir = args.output_base_dir
    raw_snapshot_dir = os.path.join(base_output_dir, "video-snapshot")
    deduplicated_snapshot_dir = os.path.join(base_output_dir, "video-snapshot-duplicate")

    print(f"INFO: Main function started. Video: {args.video_file}", flush=True) # ADDED
    print(f"INFO: Raw snapshot dir: {raw_snapshot_dir}", flush=True) # ADDED
    print(f"INFO: Deduplicated snapshot dir: {deduplicated_snapshot_dir}", flush=True) # ADDED
    print(f"INFO: Scene detection threshold: {args.threshold}", flush=True) # ADDED
    print(f"INFO: Deduplication group size: {args.group_size}", flush=True) # ADDED

    if not os.path.exists(args.video_file):
        print(f"ERROR: Video file not found: {args.video_file}", flush=True) # MODIFIED
        sys.exit(1) # ADDED exit

    # 1. Extract snapshots
    print("INFO: === Step 1: Extracting Snapshots ===", flush=True) # ADDED
    extract_snapshots(args.video_file, raw_snapshot_dir, scene_detector_threshold=args.threshold)
    print("INFO: === Step 1: Finished Extracting Snapshots ===", flush=True) # ADDED

    # 2. Deduplicate snapshots
    print("INFO: === Step 2: Deduplicating Snapshots ===", flush=True) # ADDED
    if not os.path.exists(raw_snapshot_dir) or not os.listdir(raw_snapshot_dir):
        print(f"WARNING: Raw snapshot directory {raw_snapshot_dir} is empty or does not exist. Skipping deduplication.", flush=True) # MODIFIED
    else:
        all_raw_snapshots = [os.path.join(raw_snapshot_dir, f) for f in os.listdir(raw_snapshot_dir) if f.lower().endswith('.jpg')]
        # 按文件名排序，确保按场景顺序处理
        all_raw_snapshots.sort(key=lambda x: get_scene_number_from_path(x))
        print(f"INFO: Found {len(all_raw_snapshots)} raw snapshots for deduplication.", flush=True) # ADDED
        
        # 使用新的基于相似度的去重方法
        # similarity_threshold: 哈希距离阈值（3-8推荐，越小越严格）
        # min_group_interval: 保留的截图之间最小场景间隔（避免过度去重）
        similarity_threshold = getattr(args, 'similarity_threshold', 5)
        min_group_interval = getattr(args, 'min_group_interval', 3)
        
        deduplicated_files = deduplicate_by_similarity(
            all_raw_snapshots,
            similarity_threshold=similarity_threshold,
            min_group_interval=min_group_interval
        )
        print(f"INFO: Found {len(deduplicated_files)} deduplicated files.", flush=True) # ADDED

        if deduplicated_files:
            if not os.path.exists(deduplicated_snapshot_dir):
                os.makedirs(deduplicated_snapshot_dir)
                print(f"INFO: Created deduplicated snapshot directory: {deduplicated_snapshot_dir}", flush=True) # MODIFIED
            else: # Clean the directory before copying new files
                print(f"INFO: Cleaning existing deduplicated snapshot directory: {deduplicated_snapshot_dir}", flush=True) # ADDED
                for item in os.listdir(deduplicated_snapshot_dir):
                    item_path = os.path.join(deduplicated_snapshot_dir, item)
                    try:
                        if os.path.isfile(item_path) or os.path.islink(item_path):
                            os.unlink(item_path)
                        elif os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                    except Exception as e_clean:
                        print(f"ERROR: Failed to delete {item_path}. Reason: {e_clean}", flush=True)

            print(f"INFO: Copying {len(deduplicated_files)} deduplicated files to {deduplicated_snapshot_dir}...", flush=True) # ADDED
            copied_count = 0 # ADDED
            for i, f_path in enumerate(deduplicated_files):
                try:
                    shutil.copy(f_path, deduplicated_snapshot_dir)
                    copied_count += 1 # ADDED
                    if (i + 1) % 20 == 0 or (i+1) == len(deduplicated_files): # ADDED progress
                        print(f"INFO: Copied {i+1}/{len(deduplicated_files)} deduplicated files.", flush=True)
                except Exception as e_copy:
                    print(f"ERROR: Failed to copy {f_path} to {deduplicated_snapshot_dir}. Error: {e_copy}", flush=True) # MODIFIED
            print(f"INFO: Successfully copied {copied_count} deduplicated files.", flush=True) # ADDED
        else:
            print("INFO: No files left after deduplication or no raw snapshots to process.", flush=True) # MODIFIED
    print("INFO: === Step 2: Finished Deduplicating Snapshots ===", flush=True) # ADDED
    
    # Output counts for views.py to parse
    raw_snapshot_count = len(os.listdir(raw_snapshot_dir)) if os.path.exists(raw_snapshot_dir) else 0
    deduplicated_snapshot_count = len(os.listdir(deduplicated_snapshot_dir)) if os.path.exists(deduplicated_snapshot_dir) else 0
    print(f"Raw snapshots count: {raw_snapshot_count}", flush=True)
    print(f"Deduplicated snapshots count: {deduplicated_snapshot_count}", flush=True)

    print("INFO: Video snapshot script finished successfully.", flush=True) # ADDED
    sys.exit(0) # ADDED explicit exit for success

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Extracts and deduplicates video snapshots.')
    parser.add_argument('--video_file', type=str, required=True, help='Path to the video file.')
    # MODIFIED: Changed from --output_dir to --output_base_dir for clarity
    parser.add_argument('--output_base_dir', type=str, required=True, help='Base directory to save snapshot subdirectories (raw and deduplicated).') 
    # MODIFIED: Changed from --scene_detection_thresh to --threshold
    parser.add_argument('--threshold', type=float, default=27.0, help='Scene detection threshold for ContentDetector.')
    # MODIFIED: Changed from --deduplication_group_size to --group_size
    parser.add_argument('--group_size', type=int, default=10, help='[DEPRECATED] Number of consecutive scenes to group for deduplication. Use similarity_threshold instead.')
    # NEW: 相似度阈值（哈希距离）
    parser.add_argument('--similarity_threshold', type=int, default=5, help='Perceptual hash distance threshold for similarity (3-8 recommended, lower=stricter).')
    # NEW: 最小场景间隔
    parser.add_argument('--min_group_interval', type=int, default=3, help='Minimum scene interval between retained screenshots.')

    cli_args = parser.parse_args()
    
    # Add a print statement right at the beginning of script execution
    print("INFO: extract_video_snapshots.py script started.", flush=True) # ADDED
    
    # Before calling main, ensure sys.stdout and sys.stderr are utf-8 encoded if possible
    # This is a general good practice for scripts run as subprocesses
    # However, views.py already handles encoding with errors='replace'
    # So, this might be redundant here but doesn't harm.
    # import sys
    # if sys.stdout.encoding != 'utf-8':
    #     sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
    # if sys.stderr.encoding != 'utf-8':
    #     sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', buffering=1)

    main(cli_args)
    # No code should be here, main now calls sys.exit()