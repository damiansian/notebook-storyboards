import cv2
import webvtt
import os
import shutil
from datetime import timedelta
import datetime

import argparse
import asyncio
import edge_tts

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
            
    cap.release()
    return scenes

def process_vtt(vtt_path, scenes):
    """
    Parses VTT and assigns captions to the correct scene.
    A caption starts in a scene if its start time >= scene start time.
    Actually, we want to accumulate all captions that occur AFTER scene X starts 
    and BEFORE scene X+1 starts.
    """
    try:
        captions = webvtt.read(vtt_path)
    except Exception as e:
        print(f"Error reading VTT: {e}")
        return scenes

    # Add an 'end_time' to scenes only for logic (last scene goes to infinity)
    for i in range(len(scenes) - 1):
        scenes[i]['end_time'] = scenes[i+1]['time']
    scenes[-1]['end_time'] = float('inf')

    for caption in captions:
        # WebVTT start in seconds
        start_seconds = caption.start_in_seconds
        
        # Find which scene this caption belongs to
        for scene in scenes:
            if scene['time'] <= start_seconds < scene['end_time']:
                scene['captions'].append(caption.text)
                break
                
    return scenes

async def generate_audio_for_scenes(scenes, output_dir, voice="en-US-AriaNeural"):
    """
    Generates audio files for each scene using edge-tts.
    """
    print("Generating audio files...")
    audio_dir = os.path.join(output_dir, "audio")
    if os.path.exists(audio_dir):
        shutil.rmtree(audio_dir)
    os.makedirs(audio_dir)
    
    for i, scene in enumerate(scenes):
        text = " ".join(scene['captions']).strip()
        if not text:
            scene['audio'] = None
            continue
            
        # Clean text slightly if needed
        text = text.replace('\n', ' ')
        
        filename = f"audio_{i:03d}.mp3"
        filepath = os.path.join(audio_dir, filename)
        
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(filepath)
        
        # Store relative path for HTML
        scene['audio'] = f"assets/audio/{filename}"
    
    print("Audio generation complete.")
    return scenes

def generate_html(scenes, output_html):
    """
    Generates the HTML storyboard.
    """
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
            audio { width: 100%; margin-top: 10px; }
        </style>
    </head>
    <body>
        <h1>Video Storyboard</h1>
    """
    
    for scene in scenes:
        time_display = str(datetime.timedelta(seconds=int(scene['time'])))
        caption_text = " ".join(scene['captions'])
        
        audio_html = ""
        if scene.get('audio'):
            audio_html = f'<audio controls src="{scene["audio"]}"></audio>'
            
        html_content += f"""
        <div class="scene">
            <div class="timestamp">Time: {time_display}</div>
            <img src="{scene['img']}" alt="Scene at {time_display}">
            <div class="captions">{caption_text}</div>
            {audio_html}
        </div>
        """
        
    html_content += """
    </body>
    </html>
    """
    
    with open(output_html, 'w') as f:
        f.write(html_content)

async def main_async():
    parser = argparse.ArgumentParser(description="Generate a storyboard from a video and VTT file.")
    parser.add_argument("video_file", help="Path to the video file")
    parser.add_argument("vtt_file", help="Path to the VTT caption file")
    parser.add_argument("--output_dir", default=".", help="Directory to save output (default: same as input)")
    parser.add_argument("--threshold", type=float, default=0.01, help="Scene detection threshold (default: 0.01)")
    parser.add_argument("--voice", default="en-US-AriaNeural", help="Voice for TTS (default: en-US-AriaNeural)")
    
    args = parser.parse_args()
    
    video_file = args.video_file
    vtt_file = args.vtt_file
    output_base_dir = args.output_dir
    
    # Ensure output directories exist
    output_frames_dir = os.path.join(output_base_dir, "assets", "frames")
    # Audio dir is created in generate_audio_for_scenes but we pass the assets root
    output_assets_dir = os.path.join(output_base_dir, "assets")
    
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
    for scene in scenes:
        scene['img'] = f"assets/frames/{os.path.basename(scene['img'])}"
        
    print("Generating Audio...")
    # Pass output_assets_dir because generate_audio_for_scenes creates "audio" inside it
    scenes = await generate_audio_for_scenes(scenes, output_assets_dir, voice=args.voice)
    
    print("Generating HTML...")
    generate_html(scenes, output_html)
    print(f"Done! Open {output_html} to view the storyboard.")

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
