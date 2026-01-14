# Video Storyboard Library

This repository processes videos to generate visual storyboards with captions. It is designed to be hosted on GitHub Pages.

**Live Site:** [https://damiansian.github.io/notebook-storyboards/](https://damiansian.github.io/notebook-storyboards/)

## Project Structure

```
├── index.html              # Main entry point (Library of all videos)
├── scripts/
│   ├── storyboard_generator.py  # Automation script
│   └── requirements.txt         # Python dependencies
└── videos/                 # Folder containing all video projects
    ├── making_color_accessible/
    │   ├── video.mp4
    │   ├── transcript.vtt
    │   ├── storyboard.html      # Generated storyboard
    │   └── assets/              # Extracted frames
    └── [new_project_name]/      # Future projects
```

## How to Add a New Video

1.  **Create a folder**:
    ```bash
    mkdir -p videos/your_project_name
    ```
2.  **Add files**: Place your `video.mp4` and `transcript.vtt` inside that folder.
3.  **Run the generator**:
    ```bash
    source scripts/venv/bin/activate  # Depending on where your venv is
    python3 scripts/storyboard_generator.py videos/your_project_name/video.mp4 videos/your_project_name/transcript.vtt --output_dir videos/your_project_name
    ```
4.  **Update Index**: Manually add a link to `videos/your_project_name/storyboard.html` in `index.html`.
5.  **Commit & Push**:
    ```bash
    git add .
    git commit -m "Add new storyboard: Your Project Name"
    git push origin main
    ```
