"""
vault/signals.py

Registers a post_save signal on Report.

Trigger conditions (ALL must be true):
  1. Record was just created (not an update)
  2. Report has a file attached
  3. No completed extraction already exists (guards against double-trigger edge cases)

Thread is daemon=True so it won't block server shutdown.

Celery upgrade — replace the threading block with:
    from vault.tasks import extract_report_task
    extract_report_task.delay(str(instance.pk))
"""

import logging
import threading

from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


def _extraction_thread_target(report_id: str) -> None:
    """
    Thread target function.
    Isolated here to keep signal handler thin and to make the import
    happen inside the thread (avoids any early circular import issues).
    """
    from vault.services.report_extractor import run_extraction

    try:
        run_extraction(report_id)
    except Exception:
        logger.exception(
            "Unhandled exception in extraction thread for report %s", report_id
        )


@receiver(post_save, sender="vault.Report")
def trigger_extraction_on_report_save(sender, instance, created: bool, **kwargs) -> None:
    """
    Fire background extraction when a new Report with a file is saved.

    Guards:
    - created=True only (updates don't re-trigger)
    - instance.file must exist (no file = nothing to extract)
    """

    if not instance.file:
        logger.debug(
            "Report %s saved without file — extraction skipped.", instance.pk
        )
        return

    logger.info(
        "Report %s created with file — starting extraction thread.", instance.pk
    )

    thread = threading.Thread(
        target=_extraction_thread_target,
        args=(str(instance.pk),),
        daemon=True,
        name=f"report-extraction-{instance.pk}",
    )
    thread.start()