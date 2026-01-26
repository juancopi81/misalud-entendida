"""MiSalud Entendida - Entry point.

Run the Gradio app with:
    uv run python main.py
"""

from src.app import create_app


def main():
    """Launch the MiSalud Entendida Gradio app."""
    app = create_app()
    app.launch()


if __name__ == "__main__":
    main()
