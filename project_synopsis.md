# Project Synopsis: Video Storyboard Library

This document outlines the content structure and technical logic of the Video Storyboard Library project. It is intended to provide context for writing copy and further development.

## 1. Project Overview
**Goal**: Automatically convert educational videos into accessible, static HTML storyboards. This allows users to "read" a video at their own pace, verifying content visually and textually without scrubbing through a timeline.

**Live Site Structure**:
- **Home (`index.html`)**: A central library listing all available video storyboards.
- **Project Structure**: Each video has its own dedicated folder (e.g., `videos/lesson_04_forms/`) containing the generated storyboard and assets.

## 2. Content & User Experience
The website hosts a collection of "Visual Transcripts".

**The Storyboard Experience**:
Each storyboard page (`storyboard.html`) presents a linear timeline of the video:
- **Visuals**: High-resolution keyframes extracted automatically when the scene changes in the video (e.g., slide transitions).
- **Text**: The exact transcript text spoken during that specific scene.
- **Accessibility**: All content is plain HTML/CSS, searchable, and screen-reader friendly.
- **Timestamps**: Each scene is marked with its specific timestamp (e.g., `0:02:35`) for reference.

**Current Content**:
1.  **Making Color Accessible**: A guide on using color contrast and accessible palettes.
2.  **Lesson 04 - Forms**: A tutorial on designing accessible web forms (labels, errors, autocomplete).

## 3. Code Logic Synopsis (`storyboard_generator.py`)

The core engine is a Python script that automates the conversion process.

### How it Works:
1.  **Input**:
    - Video File (`.mp4`)
    - Caption File (`.vtt` WebVTT format)

2.  **Step 1: Smart Scene Detection**
    - The script scans the video frame-by-frame.
    - It uses **Frame Difference** analysis (pixel-by-pixel comparison) to detect visual changes.
    - **Trigger**: When the visual difference between the current frame and the last captured scene exceeds a threshold (1%), it registers a "Scene Change".
    - **Result**: It captures and saves a high-quality JPEG of that new slide/scene into an `assets/frames/` folder.

3.  **Step 2: Caption Alignment**
    - The script parses the `.vtt` file to extract all spoken lines and their start/end times.
    - It intelligently maps each caption line to the correct visual scene. 
    - *Logic*: A caption belongs to the most recent scene that appeared before the caption started speaking.

4.  **Step 3: HTML Generation**
    - It assembles an HTML page combining the captured images and their aligned text.
    - It handles logical formatting and uses relative paths (e.g., `assets/frames/frame_001.jpg`) so the output folder is portable.

### Usage
The tool is run via command line:
`python3 scripts/storyboard_generator.py [video_path] [vtt_path] --output_dir [target_folder]`

## 4. Technical Specifications
- **Inputs**: MP4 Video (720p/1080p), WebVTT Transcript.
- **Outputs**:
    - `storyboard.html` (The viewable page)
    - `assets/frames/` (Directory of extracted JPEGs)
- **Dependencies**: Python 3, OpenCV (for video analysis), webvtt-py (for caption parsing).
