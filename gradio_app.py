"""Gradio UI for longform-lore-videos pipeline."""

import os
import requests
import time
from typing import Optional

import gradio as gr

# API configuration
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")


class LongformLoreGradio:
    """Gradio app for longform-lore-videos pipeline."""

    def __init__(self):
        """Initialize Gradio app."""
        self.current_job_id: Optional[str] = None

    def submit_job(
        self,
        topic: str,
        genre: str,
        chapters: int,
        quality: str,
        voice_clone_url: Optional[str] = None,
    ) -> tuple:
        """Submit a new job to the FastAPI backend."""
        if not topic or len(topic) > 500:
            return None, "Topic must be 1-500 characters", gr.update(visible=False)

        payload = {
            "topic": topic,
            "genre": genre,
            "chapters": chapters,
            "quality": quality,
            "voice_clone_url": voice_clone_url,
        }

        try:
            response = requests.post(f"{API_BASE_URL}/jobs", json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            self.current_job_id = data["job_id"]
            return data, None, gr.update(visible=True)
        except requests.exceptions.RequestException as e:
            return None, f"API error: {str(e)}", gr.update(visible=False)

    def poll_progress(self) -> tuple:
        """Poll job progress from FastAPI backend."""
        if not self.current_job_id:
            return gr.update(), gr.update(), gr.update(), gr.update()

        try:
            response = requests.get(
                f"{API_BASE_URL}/jobs/{self.current_job_id}", timeout=5
            )
            response.raise_for_status()
            data = response.json()

            # Update status badge
            status_map = {
                "queued": "blue",
                "generating_script": "blue",
                "generating_narration": "blue",
                "generating_music": "blue",
                "generating_images": "blue",
                "generating_subtitles": "blue",
                "assembling_video": "blue",
                "complete": "success",
                "failed": "error",
            }
            status_map.get(data.get("status"), "neutral")

            # Update progress bar
            progress_pct = data.get("progress_pct", 0)
            stage = data.get("stage")

            # Update log
            log_entries = [
                f"[{time.strftime('%H:%M:%S')}] Stage: {stage or 'unknown'}",
                f"[{time.strftime('%H:%M:%S')}] Progress: {progress_pct}%",
            ]
            if data.get("error"):
                log_entries.append(f"[{time.strftime('%H:%M:%S')}] ERROR: {data['error']}")

            return (
                gr.update(value=data.get("status", ""), elem_id="status-badge"),
                gr.update(value=stage or "Unknown stage"),
                gr.update(value=progress_pct),
                "\n".join(log_entries[-5:]),
            )
        except requests.exceptions.RequestException:
            return (
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(),
            )

    def download_video(self) -> str:
        """Download the completed video."""
        if not self.current_job_id:
            return None

        try:
            response = requests.get(
                f"{API_BASE_URL}/jobs/{self.current_job_id}/download",
                timeout=30,
                stream=True,
            )
            response.raise_for_status()
            return f"{API_BASE_URL}/jobs/{self.current_job_id}/download"
        except requests.exceptions.RequestException as e:
            return f"Download failed: {str(e)}"

    def create_ui(self) -> gr.Blocks:
        """Create Gradio UI."""
        with gr.Blocks(title="Longform Lore Video Generator") as demo:
            gr.Markdown(
                """
                # 🎥 Longform Lore Video Generator
                Generate long-form lore videos from a topic and genre.
                """
            )

            with gr.Tab("Generate Video"):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### Input")

                        topic_input = gr.Textbox(
                            label="Topic",
                            placeholder="e.g. The rise of the Byzantine Empire",
                            max_lines=3,
                        )

                        genre_input = gr.Dropdown(
                            label="Genre",
                            choices=[
                                "historical",
                                "scifi",
                                "fantasy",
                                "narrative",
                                "educational",
                            ],
                            value="historical",
                        )

                        chapters_slider = gr.Slider(
                            label="Chapters",
                            minimum=2,
                            maximum=15,
                            value=5,
                            step=1,
                        )

                        quality_input = gr.Radio(
                            label="Quality",
                            choices=["draft", "standard", "hq"],
                            value="standard",
                        )

                        voice_input = gr.Audio(
                            label="Voice Clone (optional)",
                            type="filepath",
                            visible=True,
                        )

                        submit_btn = gr.Button("Generate Video", variant="primary")

                    with gr.Column(scale=1):
                        gr.Markdown("### Progress")

                        status_badge = gr.Textbox(
                            label="Status",
                            value="Ready",
                            interactive=False,
                        )

                        stage_label = gr.Label(
                            label="Current Stage",
                            value="Waiting for input...",
                        )

                        progress_bar = gr.Number(
                            label="Progress",
                            value=0,
                        )

                        progress_text = gr.Textbox(
                            label="Log",
                            lines=5,
                            max_lines=5,
                            interactive=False,
                        )

                with gr.Row(visible=False) as output_row:
                    with gr.Column():
                        gr.Markdown("### Output")

                        video_output = gr.Video(
                            label="Generated Video",
                            visible=False,
                        )

                        download_btn = gr.Button("Download Video", variant="secondary")

                        script_preview = gr.Accordion(
                            label="Script Preview",
                            visible=False,
                        )

                        with script_preview:
                            gr.Markdown()

            with gr.Tab("History"):
                gr.Markdown("### Job History")
                gr.Markdown("Job history will be displayed here.")

            # Event handlers
            submit_btn.click(
                self.submit_job,
                [
                    topic_input,
                    genre_input,
                    chapters_slider,
                    quality_input,
                    voice_input,
                ],
                [status_badge, gr.Markdown(), output_row],
            ).then(
                self.poll_progress,
                outputs=[status_badge, stage_label, progress_bar, progress_text],
                every=1,
            )

            download_btn.click(
                self.download_video,
                outputs=video_output,
            )

        return demo


if __name__ == "__main__":
    app = LongformLoreGradio()
    demo = app.create_ui()
    demo.launch(server_name="0.0.0.0", server_port=7860)
