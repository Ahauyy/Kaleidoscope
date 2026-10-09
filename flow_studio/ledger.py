import os
import json
import time
from typing import Dict, Any, List, Optional

class JobLedger:
    """
    Persistent state ledger for tracking batch jobs, resuming interrupted sessions,
    and preventing duplicate generations.
    """

    def __init__(self, ledger_path: str):
        self.ledger_path = os.path.abspath(ledger_path)
        os.makedirs(os.path.dirname(self.ledger_path), exist_ok=True)
        self.state: Dict[str, Any] = {
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "items": {}
        }
        self.load()

    def load(self) -> None:
        """Loads state from disk if exists."""
        if os.path.exists(self.ledger_path):
            try:
                with open(self.ledger_path, "r", encoding="utf-8") as f:
                    self.state = json.load(f)
            except Exception as e:
                print(f"⚠️ Warning loading ledger from {self.ledger_path}: {e}")

    def save(self) -> None:
        """Saves current state to disk."""
        self.state["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(self.ledger_path, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)

    def register_item(self, item_id: str, meta: Dict[str, Any], output_check_path: Optional[str] = None) -> None:
        """
        Registers an item into the ledger.
        If output file already exists on disk, auto-marks as COMPLETED.
        """
        if item_id in self.state["items"]:
            # Update meta if already present
            self.state["items"][item_id]["meta"] = meta
            return

        is_done = False
        if output_check_path and os.path.exists(output_check_path) and os.path.getsize(output_check_path) > 1024:
            is_done = True

        self.state["items"][item_id] = {
            "id": item_id,
            "status": "COMPLETED" if is_done else "PENDING",
            "output_path": output_check_path if is_done else None,
            "retries": 0,
            "error": None,
            "meta": meta
        }

    def mark_completed(self, item_id: str, output_path: str) -> None:
        """Marks item as completed and flushes to disk."""
        if item_id in self.state["items"]:
            self.state["items"][item_id]["status"] = "COMPLETED"
            self.state["items"][item_id]["output_path"] = output_path
            self.state["items"][item_id]["completed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            self.save()

    def mark_failed(self, item_id: str, error_msg: str) -> None:
        """Records error and increments retry counter."""
        if item_id in self.state["items"]:
            self.state["items"][item_id]["status"] = "FAILED"
            self.state["items"][item_id]["retries"] = self.state["items"][item_id].get("retries", 0) + 1
            self.state["items"][item_id]["error"] = str(error_msg)
            self.save()

    def get_pending(self, retry_failed: bool = False) -> List[Dict[str, Any]]:
        """Returns items ready to be processed."""
        valid_statuses = ["PENDING"]
        if retry_failed:
            valid_statuses.append("FAILED")
        return [
            item for item in self.state["items"].values()
            if item.get("status") in valid_statuses
        ]

    def get_summary(self) -> Dict[str, int]:
        """Returns count summary of all states."""
        counts = {"total": len(self.state["items"]), "COMPLETED": 0, "PENDING": 0, "FAILED": 0}
        for item in self.state["items"].values():
            st = item.get("status", "PENDING")
            counts[st] = counts.get(st, 0) + 1
        return counts
