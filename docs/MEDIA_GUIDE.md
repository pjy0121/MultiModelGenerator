# Website Media Guide

This document lists the screenshots and videos to be inserted into `docs/index.html`.

## Folder Structure
```
docs/
├── index.html
├── assets/
│   ├── videos/
│   │   ├── demo-main.mp4          # Main demo (full process)
│   │   ├── demo-node-connect.mp4  # Adding and connecting nodes
│   │   ├── demo-execution.mp4     # Workflow execution
│   │   ├── demo-requirements.mp4  # Requirements extraction example
│   │   └── demo-multi-model.mp4   # Multi-model comparison example
│   └── screenshots/
│       ├── concept-diagram.png    # Workflow concept diagram
│       ├── canvas.png             # Workflow canvas
│       ├── node-config.png        # Node settings panel
│       ├── kb-manager.png         # Knowledge base management
│       ├── kb-create-modal.png    # KB creation modal
│       ├── kb-created.png         # KB creation complete
│       ├── node-generation.png    # Generation node settings
│       ├── node-context.png       # Context node settings
│       ├── node-validation.png    # Validation node settings
│       ├── result-panel.png       # Results panel
│       └── save-export.png        # Save and export
```

---

## Required Media List

### Videos (5)

| Filename | Location | Description | Recommended Length |
|----------|----------|-------------|-------------------|
| `demo-main.mp4` | Hero section | Complete workflow configuration to execution | 1-2 min |
| `demo-node-connect.mp4` | Tutorial Step 2 | Adding nodes and dragging to connect | 20-30 sec |
| `demo-execution.mp4` | Feature - Real-time Execution | Clicking execute and streaming results | 30-60 sec |
| `demo-requirements.mp4` | Use Case 1 | Full requirements extraction from tech docs | 1-2 min |
| `demo-multi-model.mp4` | Use Case 2 | Multi-model comparison and ensemble | 1-2 min |

### Screenshots (11)

| Filename | Location | Description |
|----------|----------|-------------|
| `concept-diagram.png` | Core Concept | Node flow diagram (Input→Context→Generation→Validation→Output) |
| `canvas.png` | Feature - Workflow Canvas | Full canvas view with multiple connected nodes |
| `node-config.png` | Feature - Node Settings | Generation node settings panel (model, prompt, etc.) |
| `kb-manager.png` | Feature - Knowledge Base | Left KB list panel (with folder structure) |
| `kb-create-modal.png` | Tutorial Step 1 | KB creation modal (file upload or text input) |
| `kb-created.png` | Tutorial Step 1 | KB shown in list after creation |
| `node-generation.png` | Tutorial Step 3 | Generation node settings screen |
| `node-context.png` | Tutorial Step 3 | Context node settings (KB selection, search intensity) |
| `node-validation.png` | Tutorial Step 3 | Validation node settings screen |
| `result-panel.png` | Tutorial Step 5 | Right panel showing execution results |
| `save-export.png` | Tutorial Step 5 | Save/export buttons and JSON export |

---

## Insertion Method

Placeholders are marked with `<!-- TODO: ... -->` comments.

### Video Insertion
```html
<!-- Before -->
<div class="video-placeholder ...">
    <!-- TODO: Insert main demo video -->
    <!-- <video src="assets/videos/demo-main.mp4" controls class="w-full h-full rounded-2xl"></video> -->
    <div class="text-center text-white/70 z-10">...</div>
</div>

<!-- After -->
<div class="rounded-2xl overflow-hidden shadow-2xl">
    <video src="assets/videos/demo-main.mp4" controls class="w-full h-full"></video>
</div>
```

### Screenshot Insertion
```html
<!-- Before -->
<div class="screenshot-placeholder rounded-xl aspect-video flex items-center justify-center">
    <!-- TODO: Insert workflow canvas screenshot -->
    <!-- <img src="assets/screenshots/canvas.png" alt="Workflow canvas"> -->
    <p class="text-gray-500">Workflow canvas screenshot</p>
</div>

<!-- After -->
<div class="rounded-xl overflow-hidden shadow-lg">
    <img src="assets/screenshots/canvas.png" alt="Workflow canvas" class="w-full h-auto">
</div>
```

---

## Recommendations

### Videos
- Resolution: 1920x1080 or 1280x720
- Format: MP4 (H.264)
- File size: Under 10MB each recommended
- Use mouse cursor highlighting recommended

### Screenshots
- Resolution: Minimum 1280px width
- Format: PNG (transparent background not required)
- Capture app screen only, exclude browser UI
- Mask sensitive information (API keys, etc.)

### GIF Alternative
GIFs can be used instead of videos (if file size is smaller):
```html
<img src="assets/videos/demo-node-connect.gif" alt="Node connection" class="w-full h-auto">
```
