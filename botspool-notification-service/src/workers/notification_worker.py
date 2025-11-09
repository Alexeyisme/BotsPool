"""Background worker for processing scheduled notifications"""
import asyncio
import logging
import signal
import sys
import redis.asyncio as redis

from ..config import settings
from ..services.scheduler import NotificationScheduler
from ..services.dispatcher import NotificationDispatcher

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
shutdown_flag = False


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    global shutdown_flag
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_flag = True


async def process_due_notifications(
    scheduler: NotificationScheduler, dispatcher: NotificationDispatcher
):
    """
    Process all notifications that are due.

    Args:
        scheduler: Notification scheduler
        dispatcher: Notification dispatcher
    """
    try:
        # Get due notifications
        due_notifications = await scheduler.get_due_notifications()

        if not due_notifications:
            return

        logger.info(f"Found {len(due_notifications)} due notifications")

        for notification in due_notifications:
            try:
                # Dispatch notification
                success = await dispatcher.dispatch_scheduled(notification)

                if success:
                    # Mark as sent
                    await scheduler.mark_as_sent(notification.id)
                    logger.info(
                        f"Successfully delivered notification {notification.id}"
                    )
                else:
                    # Mark as failed
                    await scheduler.mark_as_failed(
                        notification.id,
                        "Failed to dispatch (rate limit or delivery error)",
                    )
                    logger.warning(f"Failed to deliver notification {notification.id}")

            except Exception as e:
                logger.error(
                    f"Error processing notification {notification.id}: {e}",
                    exc_info=True,
                )
                # Mark as failed
                await scheduler.mark_as_failed(notification.id, str(e))

    except Exception as e:
        logger.error(f"Error in process_due_notifications: {e}", exc_info=True)


async def notification_worker():
    """
    Main worker loop.
    Checks for due notifications every minute and dispatches them.
    """
    logger.info("Notification worker starting...")

    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Create Redis client
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=False)

    try:
        # Create scheduler and dispatcher
        scheduler = NotificationScheduler(redis_client)
        dispatcher = NotificationDispatcher(redis_client)

        logger.info(
            f"Worker initialized, checking every {settings.WORKER_CHECK_INTERVAL_SECONDS}s"
        )

        while not shutdown_flag:
            try:
                # Process due notifications
                await process_due_notifications(scheduler, dispatcher)

                # Wait for next check
                await asyncio.sleep(settings.WORKER_CHECK_INTERVAL_SECONDS)

            except Exception as e:
                logger.error(f"Error in worker loop: {e}", exc_info=True)
                # Wait a bit before retrying
                await asyncio.sleep(10)

        logger.info("Worker shutdown complete")

    finally:
        # Cleanup
        await dispatcher.close()
        await redis_client.aclose()


def main():
    """Main entry point"""
    try:
        asyncio.run(notification_worker())
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Worker crashed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
