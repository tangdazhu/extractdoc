import os
import dashscope
from http import HTTPStatus
import logging
import json # Added for parsing transcription result
import requests # ADDED requests library

logger = logging.getLogger(__name__)

# It's recommended to set DASHSCOPE_API_KEY in your environment variables.
# If not set, DashScope SDK will try to load it from a default configuration file.
# You can also set it explicitly using: dashscope.api_key = "YOUR_API_KEY"
# For this project, we expect it to be in the environment variables.

def transcribe_audio_dashscope(audio_file_url: str) -> dict:
    """
    Transcribes the given audio file URL using Alibaba Cloud DashScope Speech Transcription
    with the Paraformer-v2 model.

    Args:
        audio_file_url: The publicly accessible URL of the audio file to transcribe.
                        Supported formats include WAV, MP3, M4A, etc.

    Returns:
        A dictionary containing the transcription result or an error.
        Example success: {"status": "success", "transcription": "Hello world.", "raw_response": ...}
        Example error: {"status": "error", "message": "Error message"}
    """
    # REMOVED the explicit check for os.environ.get("DASHSCOPE_API_KEY")
    # The SDK will use the value set by dashscope.api_key = "..." in settings.py
    # or fall back to its own methods of finding the API key (like environment variables if dashscope.api_key wasn't set).

    try:
        logger.debug(f"Current DashScope API Key (at point of call): {dashscope.api_key[:5] if dashscope.api_key else 'Not Set'}") # ADDED for debugging
        # Call the transcription service asynchronously
        task_response = dashscope.audio.asr.Transcription.async_call(
            model='paraformer-v2',  # Explicitly use paraformer-v2
            file_urls=[audio_file_url],
            # language_hints=['zh', 'en'] # Optional: add if you have specific language hints
        )

        if not task_response or task_response.status_code != HTTPStatus.OK:
            logger.error(f"Failed to submit transcription task. Response: {task_response}")
            error_message = task_response.message if task_response and hasattr(task_response, 'message') else "Unknown error submitting task."
            return {"status": "error", "message": f"Failed to submit transcription task: {error_message}"}

        task_id = task_response.output.task_id
        logger.info(f"Transcription task submitted successfully. Task ID: {task_id}")

        # Wait for the transcription result
        transcription_response = dashscope.audio.asr.Transcription.wait(task=task_id)

        if transcription_response.status_code == HTTPStatus.OK:
            logger.info("Transcription completed successfully.")
            # The result is a list of transcriptions, one for each URL.
            # Since we only send one URL, we expect one result.
            
            full_transcription_text = []
            raw_results = transcription_response.output.get('results', [])

            for result_item in raw_results:
                transcription_url = result_item.get('transcription_url')
                if transcription_url:
                    try:
                        # In Python 3, urlopen returns an HTTPResponse object.
                        # We need to read() its content and then decode.
                        with requests.get(transcription_url, stream=True) as r:
                            r.raise_for_status() # Will raise an HTTPError if the HTTP request returned an unsuccessful status code
                            result_content = r.content.decode('utf-8') # ADDED: Log raw content first
                            logger.info(f"Fetched transcription JSON from {transcription_url}: {result_content[:500]}") # ADDED
                            result_data = json.loads(result_content)
                            logger.info(f"Parsed transcription data: {result_data}") # ADDED: Log parsed data
                        
                        # Extract sentences and join them
                        # MODIFIED: Corrected path to extract sentences based on actual JSON structure
                        full_transcription_text = [] # Moved initialization here
                        transcripts = result_data.get('transcripts', [])
                        for transcript_item in transcripts:
                            sentences = transcript_item.get('sentences', [])
                            logger.info(f"Extracted sentences from transcript_item: {sentences}") # MODIFIED
                            for sentence in sentences:
                                full_transcription_text.append(sentence.get('text', ''))
                    except Exception as e:
                        logger.error(f"Error fetching or parsing transcription result from URL {transcription_url}: {e}")
                        # Continue to try and process other results if any, or return partial if this was the only one
                else:
                    logger.warning(f"No transcription_url found in result item: {result_item}")

            final_text = " ".join(full_transcription_text).strip()
            return {
                "status": "success",
                "transcription": final_text,
                "raw_response": transcription_response.output # Store the full output for potential further details
            }
        else:
            logger.error(f"Transcription failed. Status Code: {transcription_response.status_code}, Response: {transcription_response}")
            logger.error(f"Raw transcription_response.output from DashScope (on failure): {transcription_response.output if hasattr(transcription_response, 'output') else 'N/A'}") # ADDED
            error_message = transcription_response.message if hasattr(transcription_response, 'message') else "Unknown transcription error."
            if hasattr(transcription_response, 'output') and transcription_response.output and hasattr(transcription_response.output, 'message'):
                 error_message = transcription_response.output.message
            return {"status": "error", "message": f"Transcription failed: {error_message}", "raw_response": transcription_response}

    except Exception as e:
        logger.error(f"An unexpected error occurred during transcription: {e}", exc_info=True)
        return {"status": "error", "message": f"An unexpected error occurred: {str(e)}"}

# Example Usage (for testing purposes, can be removed or commented out)
if __name__ == '__main__':
    # Ensure DASHSCOPE_API_KEY is set as an environment variable before running this
    # Example: export DASHSCOPE_API_KEY="your_actual_api_key"
    if not os.environ.get("DASHSCOPE_API_KEY"):
        print("Please set the DASHSCOPE_API_KEY environment variable to test.")
    else:
        print(f"DASHSCOPE_API_KEY found: {os.environ.get('DASHSCOPE_API_KEY')[:5]}...") # Print first 5 chars for confirmation
        
        # Replace with a publicly accessible M4A or WAV file URL for testing
        # This is one of the sample URLs from the documentation
        test_audio_url_m4a = 'https://dashscope.oss-cn-beijing.aliyuncs.com/samples/audio/paraformer/hello_world_female2.wav' # Using WAV as per snippet
        
        print(f"Testing transcription for URL: {test_audio_url_m4a}")
        result = transcribe_audio_dashscope(test_audio_url_m4a)
        
        print("\nTranscription Result:")
        if result['status'] == 'success':
            print(f"  Status: Success")
            print(f"  Transcription: {result['transcription']}")
            # print(f"  Raw Response: {result.get('raw_response')}") # Can be very verbose
        else:
            print(f"  Status: Error")
            print(f"  Message: {result['message']}")
            # print(f"  Raw Response: {result.get('raw_response')}")

        # Test with a non-existent or problematic URL (optional)
        # print("\nTesting with a bad URL:")
        # bad_url_result = transcribe_audio_dashscope("http://example.com/nonexistent.wav")
        # print(f"  Status: {bad_url_result['status']}")
        # print(f"  Message: {bad_url_result['message']}") 