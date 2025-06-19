"""
Django management command to test real-time speech recognition
"""

import os
import time
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from converter.realtime_speech_processor import create_realtime_recognizer

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Test real-time speech recognition functionality"

    def add_arguments(self, parser):
        parser.add_argument(
            "--duration",
            type=int,
            default=30,
            help="Test duration in seconds (default: 30)",
        )
        parser.add_argument(
            "--language",
            type=str,
            default="zh,en",
            help="Language hints (comma-separated, default: zh,en)",
        )
        parser.add_argument(
            "--api-key",
            type=str,
            help="DashScope API key (optional, uses environment variable if not provided)",
        )

    def handle(self, *args, **options):
        """Main command handler"""
        self.stdout.write(
            self.style.SUCCESS("Starting real-time speech recognition test...")
        )

        # Setup API key
        api_key = options.get("api_key") or os.environ.get("DASHSCOPE_API_KEY")
        if not api_key:
            self.stdout.write(
                self.style.ERROR(
                    "DASHSCOPE_API_KEY not found in environment variables or --api-key argument"
                )
            )
            return

        # Parse language hints
        language_hints = [lang.strip() for lang in options["language"].split(",")]
        duration = options["duration"]

        self.stdout.write(f"Language hints: {language_hints}")
        self.stdout.write(f"Test duration: {duration} seconds")

        # Result counter
        result_count = 0

        def result_handler(result):
            """Handle recognition results"""
            nonlocal result_count
            result_count += 1

            text = result.get("text", "")
            is_final = result.get("is_final", False)
            confidence = result.get("confidence", 0.0)

            status = "FINAL" if is_final else "PARTIAL"
            self.stdout.write(
                f"[{result_count:03d}] {status}: {text} (confidence: {confidence:.2f})"
            )

        try:
            # Create recognizer
            self.stdout.write("Creating recognizer...")
            recognizer = create_realtime_recognizer(
                result_handler=result_handler, language_hints=language_hints
            )

            if not recognizer:
                self.stdout.write(self.style.ERROR("Failed to create recognizer"))
                return

            # Start recognition
            self.stdout.write("Starting recognition...")
            if not recognizer.start_recognition():
                self.stdout.write(self.style.ERROR("Failed to start recognition"))
                return

            self.stdout.write(self.style.SUCCESS("Recognition started successfully!"))
            self.stdout.write(
                "Note: This is a mock implementation. In a real scenario, "
                "you would send audio data to the recognizer."
            )

            # Simulate audio data sending
            self.stdout.write("Simulating audio data...")
            start_time = time.time()

            while time.time() - start_time < duration:
                # Simulate sending audio chunks
                mock_audio_data = b"\x00" * 1024  # Mock audio data
                recognizer.send_audio_data(mock_audio_data)
                time.sleep(1)  # Send data every second

            # Stop recognition
            self.stdout.write("Stopping recognition...")
            if recognizer.stop_recognition():
                self.stdout.write(
                    self.style.SUCCESS("Recognition stopped successfully!")
                )
            else:
                self.stdout.write(self.style.WARNING("Recognition stop returned False"))

            # Summary
            self.stdout.write("\n" + "=" * 50)
            self.stdout.write(f"Test completed!")
            self.stdout.write(f"Total results received: {result_count}")
            self.stdout.write(f"Test duration: {duration} seconds")
            self.stdout.write("=" * 50)

        except KeyboardInterrupt:
            self.stdout.write("\nTest interrupted by user")
            if "recognizer" in locals():
                recognizer.stop_recognition()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Test failed with error: {e}"))
            logger.error(f"Real-time speech test error: {e}", exc_info=True)

        self.stdout.write(
            self.style.SUCCESS("Real-time speech recognition test completed.")
        )
