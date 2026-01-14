import cv2
import webvtt
import os
import shutil
from datetime import timedelta

def time_str_to_seconds(time_str):
    """Converts a VTT timestamp string to seconds."""
    h, m, s = time_str.split(':')
    s, ms = s.split('.')
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0

def format_timestamp(seconds):
    """Formats seconds to HH:MM:SS string."""
    td = timedelta(seconds=seconds)
    # Remove microseconds for cleaner display
    return str(td).split('.')[0]

def extract_key_frames(video_path, output_dir, threshold=0.01):
    """
    Extracts frames when the scene changes, using pixel difference.
    Useful for slide presentations where histograms might be identical 
    but content changes position or text.
    
    Args:
        video_path: Path to video.
        output_dir: Output directory.
        threshold: Fraction of pixels that need to change to trigger a new scene (0.01 = 1%).
    """
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video {video_path}")
        return []

    scenes = []
    prev_frame_gray = None
    
    # Parameters
    # min_duration: minimum seconds between scenes to avoid duplicate triggers on transitions
    min_duration = 1.0 
    
    ret, frame = cap.read()
    if not ret:
        return []
        
    # Standardize size for comparison acceleration
    resize_dim = (640, 360) 
    
    # Save first frame
    first_frame_path = os.path.join(output_dir, "frame_0000.jpg")
    cv2.imwrite(first_frame_path, frame)
    scenes.append({'time': 0.0, 'img': "frame_0000.jpg", 'captions': []})
    
    prev_frame_gray = cv2.cvtColor(cv2.resize(frame, resize_dim), cv2.COLOR_BGR2GRAY)
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = 0
    skip_frames = 2 # Check more frequently (every 2nd frame)
    
    total_pixels = resize_dim[0] * resize_dim[1]
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        frame_count += 1
        if frame_count % skip_frames != 0:
            continue
            
        curr_frame_small = cv2.resize(frame, resize_dim)
        curr_frame_gray = cv2.cvtColor(curr_frame_small, cv2.COLOR_BGR2GRAY)
        
        # Calculate absolute difference
        diff = cv2.absdiff(prev_frame_gray, curr_frame_gray)
        # Threshold the difference (pixels that changed significantly)
        _, diff_thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
        
        # Count non-zero pixels (changed pixels)
        changed_pixels = cv2.countNonZero(diff_thresh)
        change_ratio = changed_pixels / total_pixels
        
        timestamp = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
        
        # If change ratio > threshold, it's a new slide/scene
        if change_ratio > threshold and (timestamp - scenes[-1]['time'] > min_duration):
            filename = f"frame_{int(timestamp):04d}.jpg"
            filepath = os.path.join(output_dir, filename)
            cv2.imwrite(filepath, frame)
            scenes.append({'time': timestamp, 'img': filename, 'captions': []})
            
            # Update reference frame strictly to the new scene
            prev_frame_gray = curr_frame_gray
            
        # Optional: update prev_frame continuously to track slow drift? 
        # For slides, "cuts" are sudden. We want to compare against the *last saved state* 
        # to know if we have moved away from it.
        # BUT transitions (fades) might confuse this.
        # Let's comparison against `prev_frame_gray` which we ONLY update when we detect a scene.
        # This ensures that if we have a Slide A, and small elements appear one by one, 
        # we trigger a new scene when enough difference accumulates from Slide A.
        # Actually, standard scene detection usually compares adjacent frames.
        # Let's compare to the *last saved scene frame* to be sure we are capturing distinct states.
        
        # Correction: If we compare to the last scene frame, we might miss a sequence of 
        # Slide A -> Slide B -> Slide A. (Difference would go up then down).
        # Actually, comparing to the *immediately previous* frame is correct for CUT detection.
        # Comparing to *last saved* is correct for "Keyframe" detection (significant change from last capture).
        # Since user wants "screens", "Keyframe" logic is better.
        
    cap.release()
    return scenes

def process_vtt(vtt_path, scenes):
    """Associates captions with scenes based on time."""
    captions = webvtt.read(vtt_path)
    
    # Helper to find which scene a caption belongs to.
    # A caption belongs to the latest scene that started before the caption starts.
    
    current_scene_idx = 0
    
    for caption in captions:
        start_seconds = time_str_to_seconds(caption.start)
        text = caption.text.strip().replace('\n', ' ')
        
        # Advance scene index if the next scene started before this caption
        # We want to find the scene where: scene.time <= caption.start < next_scene.time
        while (current_scene_idx + 1 < len(scenes) and 
               scenes[current_scene_idx + 1]['time'] <= start_seconds):
            current_scene_idx += 1
            
        scenes[current_scene_idx]['captions'].append(text)

    return scenes

def generate_html(scenes, output_html):
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            .scene { margin-bottom: 40px; border-bottom: 1px solid #ccc; padding-bottom: 20px; }
            img { max-width: 100%; height: auto; border: 1px solid #ddd; }
            .timestamp { color: #666; font-size: 0.9em; margin-bottom: 5px; }
            .captions { font-size: 1.1em; line-height: 1.5; margin-top: 10px; }
        </style>
    </head>
    <body>
        <h1>Video Storyboard</h1>
    """
    
    for scene in scenes:
        time_display = format_timestamp(scene['time'])
        caption_text = " ".join(scene['captions'])
        
        html_content += f"""
        <div class="scene">
            <div class="timestamp">Time: {time_display}</div>
            <img src="frames/{scene['img']}" alt="Scene at {time_display}">
            <div class="captions">{caption_text}</div>
        </div>
        """
        
    html_content += "</body></html>"
    
    with open(output_html, 'w') as f:
        f.write(html_content)

import argparse

def main():
    parser = argparse.ArgumentParser(description="Generate a storyboard from a video and VTT file.")
    parser.add_argument("video_file", help="Path to the video file")
    parser.add_argument("vtt_file", help="Path to the VTT caption file")
    parser.add_argument("--output_dir", default=".", help="Directory to save output (default: same as input)")
    parser.add_argument("--threshold", type=float, default=0.01, help="Scene detection threshold (default: 0.01)")
    
    args = parser.parse_args()
    
    video_file = args.video_file
    vtt_file = args.vtt_file
    output_base_dir = args.output_dir
    
    # Ensure output directories exist
    output_frames_dir = os.path.join(output_base_dir, "assets", "frames")
    if not os.path.exists(output_frames_dir):
        os.makedirs(output_frames_dir)
        
    output_html = os.path.join(output_base_dir, "storyboard.html")
    
    print(f"Processing {video_file}...")
    print(f"Outputting to {output_base_dir}")
    
    print("Extracting frames...")
    # Pass the full path to extract_key_frames
    scenes = extract_key_frames(video_file, output_frames_dir, threshold=args.threshold)
    print(f"Extracted {len(scenes)} scenes.")
    
    print("Processing captions...")
    scenes = process_vtt(vtt_file, scenes)
    
    # Update image paths in scenes to be relative for the HTML
    # The HTML is in output_base_dir. Frames are in output_base_dir/assets/frames
    # So relative path is assets/frames/filename
    for scene in scenes:
        scene['img'] = f"assets/frames/{os.path.basename(scene['img'])}"
    
    print("Generating HTML...")
    generate_html(scenes, output_html)
    print(f"Done! Open {output_html} to view the storyboard.")

if __name__ == "__main__":
    main()
