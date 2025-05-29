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
    print(f"Starting snapshot extraction for video: {video_path}")
    print(f"Snapshots will be saved to: {output_dir}")

    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")

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
        print("Detecting scenes...")
        scene_manager.detect_scenes(frame_source=video_manager, show_progress=True)

        # scene_list will be a list of tuples (start_timecode, end_timecode)
        scene_list = scene_manager.get_scene_list()
        print(f"Detected {len(scene_list)} scenes.")

        if not scene_list:
            print("No scenes detected in the video.")
            return

        # Create a new VideoCapture object to extract frames by number,
        # as PySceneDetect's VideoManager might be optimized for sequential access.
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"Error: Could not open video file {video_path} with OpenCV for frame extraction.")
            return
            
        fps = cap.get(cv2.CAP_PROP_FPS)
        print(f"Video FPS: {fps}")

        snapshot_count = 0
        for i, (start_time, end_time) in enumerate(scene_list):
            # start_time and end_time are FrameTimecode objects.
            # We want to get the frame at the beginning of the scene.
            start_frame_num = start_time.get_frames()
            
            # To get a frame slightly after the cut, you can add a small offset
            # For PPTs, the first frame of the scene is usually what we want.
            # frame_to_extract = start_frame_num + int(fps * 0.1) # e.g., 0.1s after cut

            print(f"Scene {i+1:03d}: Starts at frame {start_frame_num} ({start_time.get_timecode()})")

            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame_num)
            ret, frame = cap.read()

            if ret:
                snapshot_filename = f"snapshot_scene_{i+1:03d}_frame_{start_frame_num}.jpg"
                snapshot_path = os.path.join(output_dir, snapshot_filename)
                cv2.imwrite(snapshot_path, frame)
                print(f"  Saved: {snapshot_path}")
                snapshot_count += 1
            else:
                print(f"  Error: Could not read frame {start_frame_num} for scene {i+1:03d}.")
        
        cap.release()
        print(f"\nExtraction complete. Saved {snapshot_count} snapshots.")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # For PySceneDetect v0.6.x and later, simply call release.
        # The is_started() method check is not needed / available.
        if 'video_manager' in locals():
            video_manager.release()

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

def get_theme_from_snapshot_coarse(filepath, group_size=10):
    """
    从截图文件路径中提取粗粒度的主题ID。
    例如，将 scene_001 到 scene_009 映射到同一个主题组。
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
    latest_screenshots_by_theme = {}

    for screenshot_item in screenshot_list:
        theme_id = func_get_theme(screenshot_item)
        order_key = func_get_order_key(screenshot_item)

        if theme_id is None:
            print(f"警告：无法确定 {screenshot_item} 的主题，已跳过。")
            continue
            
        current_best_data = latest_screenshots_by_theme.get(theme_id)

        if current_best_data is None or order_key >= current_best_data['order_key']:
            latest_screenshots_by_theme[theme_id] = {
                'item': screenshot_item,
                'order_key': order_key,
                'theme': theme_id
            }

    deduplicated_list = [data['item'] for data in latest_screenshots_by_theme.values()]
    deduplicated_list.sort(key=lambda x: func_get_theme(x)) 
    return deduplicated_list

if __name__ == "__main__":
    # --- 用户可配置的主要参数 ---
    # 1. 输入视频文件的完整路径
    # 示例: video_file_path = "C:/videos/my_presentation.mp4"
    # video_file_path = "/path/to/your/video.mp4"
    # 自动构建测试视频路径 (如果脚本按预期目录结构放置)
    script_dir_for_paths = os.path.dirname(os.path.abspath(__file__))
    base_test_data_dir_for_paths = os.path.join(script_dir_for_paths, "test", "test_data")
    video_file_path = os.path.join(base_test_data_dir_for_paths, "test-video-2.mp4")

    # 2. PySceneDetect 场景检测阈值 (ContentDetector threshold)
    # 较低的值 (如 5.0, 10.0) 更敏感，检测更多场景；较高的值 (如 25.0-35.0) 检测较明显切换。
    scene_detection_thresh = 5.0

    # 3. 去重时的主题分组大小 (group_size for deduplication)
    # 定义多少个连续的 PySceneDetect 细分场景被视为一个"逻辑幻灯片主题"组。
    # 根据视频内容和 scene_detection_thresh 的设置进行调整。
    # 如果去重不够，尝试增大此值；如果去重过度，尝试减小此值。
    deduplication_group_size = 5

    # --- 派生路径定义 (基于脚本位置自动生成) ---
    # (确保 script_dir, base_test_data_dir 等变量名不与上面的新变量名冲突，如果需要则调整)
    # 当前脚本的父目录，用于构建测试数据路径
    # script_dir = os.path.dirname(os.path.abspath(__file__))
    # base_test_data_dir = os.path.join(script_dir, "test", "test_data") 
    # 使用上面已经为 video_file_path 定义的 base_test_data_dir_for_paths
    
    # 初始截图的输出目录
    snapshot_output_dir_path = os.path.join(base_test_data_dir_for_paths, "video-snapshot")
    # 去重后截图的输出目录
    deduplicated_output_dir_path = os.path.join(base_test_data_dir_for_paths, "video-snapshot-duplicate")

    # --- 参数校验与执行 --- 
    if not os.path.exists(video_file_path):
        print(f"错误: 视频文件未找到于 {video_file_path}")
        print("请确保 video_file_path 参数已正确设置，并且文件存在。")
    else:
        # 步骤 1: 提取初始快照
        print("--- 步骤 1: 开始提取初始视频快照 ---")
        extract_snapshots(video_file_path, snapshot_output_dir_path, scene_detector_threshold=scene_detection_thresh)

        # 步骤 2: 对提取的快照进行去重
        print("--- 步骤 2: 开始对提取的快照进行去重处理 ---")
        
        # 确保目标去重目录存在
        if not os.path.exists(deduplicated_output_dir_path):
            os.makedirs(deduplicated_output_dir_path)
            print(f"已创建去重后截图的目标目录: {deduplicated_output_dir_path}")
        # else:
            # 如果需要，这里可以添加清空已存在目标目录的逻辑
            # print(f"目标目录 {deduplicated_output_dir_path} 已存在，内容将被覆盖或追加。")

        # 获取源截图文件列表 (来自步骤1的输出)
        all_generated_screenshots = []
        source_for_dedup_dir = snapshot_output_dir_path # 去重的源是步骤1的输出
        
        if os.path.exists(source_for_dedup_dir) and os.path.isdir(source_for_dedup_dir):
            print(f"从以下目录读取截图进行去重: {source_for_dedup_dir}")
            for filename in os.listdir(source_for_dedup_dir):
                if filename.startswith("snapshot_scene_") and filename.endswith(".jpg"):
                    full_path = os.path.join(source_for_dedup_dir, filename)
                    all_generated_screenshots.append(full_path)
        else:
            print(f"错误：找不到用于去重的源截图目录 {source_for_dedup_dir}。请检查步骤1是否成功执行。")
            exit() # 如果没有源文件，则无法继续

        all_generated_screenshots.sort() # 确保一致的顺序

        if all_generated_screenshots:
            final_screenshots = deduplicate_slide_screenshots(
                all_generated_screenshots,
                lambda x: get_theme_from_snapshot_coarse(x, group_size=deduplication_group_size), 
                get_order_key_from_snapshot
            )

            print(f"原始截图数量 (来自 {os.path.basename(source_for_dedup_dir)}): {len(all_generated_screenshots)}")
            print(f"去重后选定截图数量: {len(final_screenshots)}")

            copied_count = 0
            if final_screenshots:
                print(f"开始复制去重后的截图到: {deduplicated_output_dir_path}")
                for src_file_path in final_screenshots:
                    try:
                        filename = os.path.basename(src_file_path)
                        dst_file_path = os.path.join(deduplicated_output_dir_path, filename)
                        shutil.copy2(src_file_path, dst_file_path)
                        copied_count += 1
                    except Exception as e:
                        print(f"复制文件 {src_file_path} 到 {dst_file_path} 时发生错误: {e}")
                print(f"成功复制 {copied_count} 张去重后的截图。")
            else:
                print("没有符合去重条件的截图可供复制。")
        else:
            print(f"在源目录 {source_for_dedup_dir} 中没有找到截图文件进行处理。")

    print("--- 脚本执行完毕 ---") 