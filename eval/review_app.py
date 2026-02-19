"""Gradio app for reviewing and correcting eval labels.

Launch:
    uv run python eval/review_app.py
"""

import csv
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import gradio as gr

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.logger import get_logger

logger = get_logger(__name__)

EVAL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EVAL_DIR.parent
PRESC_JSONL = EVAL_DIR / "prescriptions_labels.jsonl"
LAB_JSONL = EVAL_DIR / "lab_labels.jsonl"
MANIFEST_CSV = EVAL_DIR / "manifest.csv"
BACKUP_DIR = EVAL_DIR / "backups"

STATUS_CHOICES = ["labeled", "reviewed", "needs_fix"]

# ── helpers ──────────────────────────────────────────────────────────────────


def create_backup():
    """Snapshot JSONL + manifest into eval/backups/."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_DIR / f"backup_{ts}"
    dest.mkdir(parents=True, exist_ok=True)
    for src in (PRESC_JSONL, LAB_JSONL, MANIFEST_CSV):
        if src.exists():
            shutil.copy2(src, dest / src.name)
    logger.info("Backup created at %s", dest)


def load_labels() -> list[dict]:
    """Read both JSONL files and return sorted list tagged with _source_file."""
    records: list[dict] = []
    for path in (PRESC_JSONL, LAB_JSONL):
        if not path.exists():
            logger.warning("File not found: %s", path)
            continue
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                rec["_source_file"] = str(path)
                records.append(rec)
    records.sort(key=lambda r: r["doc_id"])
    logger.info("Loaded %d label records", len(records))
    return records


def load_manifest() -> list[dict]:
    """Read manifest.csv into list of dicts."""
    with open(MANIFEST_CSV, newline="") as f:
        return list(csv.DictReader(f))


def save_manifest(rows: list[dict]):
    """Atomic rewrite of manifest.csv."""
    fieldnames = rows[0].keys() if rows else []
    fd, tmp = tempfile.mkstemp(dir=EVAL_DIR, suffix=".csv")
    try:
        with os.fdopen(fd, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        os.replace(tmp, MANIFEST_CSV)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def resolve_images(rec: dict) -> list[str]:
    """Return list of absolute image paths for a record."""
    if rec["doc_type"] == "lab":
        paths = rec.get("image_paths", [])
    else:
        p = rec.get("image_path", "")
        paths = [p] if p else []
    return [str(PROJECT_ROOT / p) for p in paths]


def payload_for_display(rec: dict) -> dict:
    """Extract the editable payload (strip internal keys)."""
    skip = {"doc_id", "doc_type", "image_path", "image_paths",
            "label_status", "annotator", "reviewer", "_source_file"}
    return {k: v for k, v in rec.items() if k not in skip}


def validate_record(doc_type: str, payload: dict) -> str | None:
    """Return error message if payload is invalid, else None."""
    if doc_type == "prescription":
        meds = payload.get("medications")
        if not isinstance(meds, list) or len(meds) == 0:
            return "Las recetas deben tener al menos un medicamento en 'medications'."
    elif doc_type == "lab":
        results = payload.get("results")
        if not isinstance(results, list) or len(results) == 0:
            return "Los laboratorios deben tener al menos un resultado en 'results'."
    return None


def save_record(records: list[dict], idx: int, edited_json: str,
                reviewer: str, status: str, notes: str) -> str:
    """Persist changes to JSONL and manifest. Returns status message."""
    rec = records[idx]
    doc_id = rec["doc_id"]

    # Validate reviewer requirement
    if status == "reviewed" and not reviewer.strip():
        return "Error: debe ingresar un revisor para marcar como 'reviewed'."

    # Parse JSON
    try:
        payload = json.loads(edited_json)
    except json.JSONDecodeError as e:
        return f"Error JSON: {e}"

    # Validate schema
    err = validate_record(rec["doc_type"], payload)
    if err:
        return f"Error de validación: {err}"

    # Merge payload back into record
    skip = {"doc_id", "doc_type", "image_path", "image_paths",
            "label_status", "annotator", "reviewer", "_source_file"}
    # Remove old payload keys
    old_keys = [k for k in rec if k not in skip]
    for k in old_keys:
        del rec[k]
    # Set new payload
    for k, v in payload.items():
        rec[k] = v
    rec["reviewer"] = reviewer.strip()
    rec["label_status"] = status

    # Atomic rewrite of source JSONL
    source_file = Path(rec["_source_file"])
    all_recs_in_file = [r for r in records if r["_source_file"] == str(source_file)]
    fd, tmp = tempfile.mkstemp(dir=EVAL_DIR, suffix=".jsonl")
    try:
        with os.fdopen(fd, "w") as f:
            for r in all_recs_in_file:
                out = {k: v for k, v in r.items() if k != "_source_file"}
                f.write(json.dumps(out, ensure_ascii=False) + "\n")
        os.replace(tmp, source_file)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise

    # Atomic rewrite of manifest
    manifest = load_manifest()
    for row in manifest:
        if row["doc_id"] == doc_id:
            row["reviewer"] = reviewer.strip()
            row["label_status"] = status
            break
    save_manifest(manifest)

    logger.info("Saved %s (status=%s, reviewer=%s)", doc_id, status, reviewer)
    return f"Guardado: {doc_id}"


# ── Gradio app ───────────────────────────────────────────────────────────────


def create_review_app() -> gr.Blocks:
    records = load_labels()
    if not records:
        raise RuntimeError("No records found in JSONL files")

    def get_filtered_ids(show_pending: bool) -> list[str]:
        if show_pending:
            return [r["doc_id"] for r in records if r["label_status"] != "reviewed"]
        return [r["doc_id"] for r in records]

    def get_rec_index(doc_id: str) -> int:
        for i, r in enumerate(records):
            if r["doc_id"] == doc_id:
                return i
        return 0

    def pending_count() -> int:
        return sum(1 for r in records if r["label_status"] != "reviewed")

    def counter_text(doc_id: str, show_pending: bool) -> str:
        ids = get_filtered_ids(show_pending)
        if doc_id in ids:
            pos = ids.index(doc_id) + 1
        else:
            pos = 0
        return f"{pos}/{len(ids)}  ({pending_count()} pendientes)"

    def load_display(doc_id: str, show_pending: bool):
        """Return all component values for a given doc_id."""
        idx = get_rec_index(doc_id)
        rec = records[idx]
        imgs = resolve_images(rec)

        # Image display
        if rec["doc_type"] == "lab" and len(imgs) > 1:
            gallery_val = imgs
            image_val = None
            gallery_visible = True
            image_visible = False
        else:
            gallery_val = None
            image_val = imgs[0] if imgs else None
            gallery_visible = False
            image_visible = True

        payload = payload_for_display(rec)
        json_str = json.dumps(payload, indent=2, ensure_ascii=False)
        ct = counter_text(doc_id, show_pending)

        return (
            image_val,              # image
            gr.update(visible=image_visible),  # image visibility
            gallery_val,            # gallery
            gr.update(visible=gallery_visible),  # gallery visibility
            json_str,               # json editor
            rec.get("reviewer", ""),  # reviewer
            rec.get("label_status", "labeled"),  # status
            ct,                     # counter
            "",                     # status message cleared
        )

    def on_dropdown_change(doc_id, show_pending):
        return load_display(doc_id, show_pending)

    def on_filter_change(show_pending, current_doc_id):
        ids = get_filtered_ids(show_pending)
        if not ids:
            ids = [r["doc_id"] for r in records]
        new_id = current_doc_id if current_doc_id in ids else ids[0]
        display = load_display(new_id, show_pending)
        return (gr.update(choices=ids, value=new_id),) + display

    def navigate(direction: int, current_doc_id: str, show_pending: bool):
        ids = get_filtered_ids(show_pending)
        if not ids:
            ids = [r["doc_id"] for r in records]
        if current_doc_id in ids:
            cur = ids.index(current_doc_id)
        else:
            cur = 0
        new_idx = max(0, min(len(ids) - 1, cur + direction))
        new_id = ids[new_idx]
        display = load_display(new_id, show_pending)
        return (gr.update(value=new_id),) + display

    def on_save(doc_id, edited_json, reviewer, status, show_pending):
        idx = get_rec_index(doc_id)
        msg = save_record(records, idx, edited_json, reviewer, status, "")
        ct = counter_text(doc_id, show_pending)
        # Refresh dropdown in case filter changed
        ids = get_filtered_ids(show_pending)
        if not ids:
            ids = [r["doc_id"] for r in records]
        new_id = doc_id if doc_id in ids else (ids[0] if ids else doc_id)
        return msg, ct, gr.update(choices=ids, value=new_id)

    # ── Build UI ─────────────────────────────────────────────────────────

    with gr.Blocks(title="Revisor de Etiquetas") as app:
        gr.Markdown("# Revisor de Etiquetas")

        init_ids = get_filtered_ids(False)

        with gr.Row():
            dropdown = gr.Dropdown(
                choices=init_ids, value=init_ids[0],
                label="doc_id", scale=3,
            )
            prev_btn = gr.Button("< Anterior", scale=1)
            next_btn = gr.Button("Siguiente >", scale=1)
            counter = gr.Textbox(
                value=counter_text(init_ids[0], False),
                label="Posición", interactive=False, scale=1,
            )

        filter_pending = gr.Checkbox(
            label=f"Mostrar solo pendientes ({pending_count()} pendientes)",
            value=False,
        )

        with gr.Row(equal_height=True):
            with gr.Column(scale=1):
                image_viewer = gr.Image(label="Imagen", height=600)
                gallery_viewer = gr.Gallery(
                    label="Imágenes (multi-página)", visible=False,
                    height=600, columns=1,
                )
            with gr.Column(scale=1):
                json_editor = gr.Code(
                    language="json", label="Payload (editable)",
                    lines=30,
                )

        with gr.Row():
            reviewer_input = gr.Textbox(label="Revisor", scale=2)
            status_input = gr.Dropdown(
                choices=STATUS_CHOICES, value="labeled",
                label="Estado", scale=1,
            )

        save_btn = gr.Button("Guardar", variant="primary")
        status_msg = gr.Textbox(label="Estado", interactive=False)

        # ── Outputs list (shared across handlers) ────────────────────────
        display_outputs = [
            image_viewer, image_viewer, gallery_viewer, gallery_viewer,
            json_editor, reviewer_input, status_input, counter, status_msg,
        ]

        # ── Wiring ──────────────────────────────────────────────────────

        dropdown.change(
            on_dropdown_change,
            inputs=[dropdown, filter_pending],
            outputs=display_outputs,
        )

        filter_pending.change(
            on_filter_change,
            inputs=[filter_pending, dropdown],
            outputs=[dropdown] + display_outputs,
        )

        prev_btn.click(
            lambda doc_id, sp: navigate(-1, doc_id, sp),
            inputs=[dropdown, filter_pending],
            outputs=[dropdown] + display_outputs,
        )

        next_btn.click(
            lambda doc_id, sp: navigate(1, doc_id, sp),
            inputs=[dropdown, filter_pending],
            outputs=[dropdown] + display_outputs,
        )

        save_btn.click(
            on_save,
            inputs=[dropdown, json_editor, reviewer_input,
                    status_input, filter_pending],
            outputs=[status_msg, counter, dropdown],
        )

        # Initial load
        app.load(
            lambda: load_display(init_ids[0], False),
            outputs=display_outputs,
        )

    return app


# ── main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    create_backup()
    app = create_review_app()
    logger.info("Starting review app on port 7861")
    app.launch(server_port=7861, share=False)
