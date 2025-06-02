import os
import dashscope
from http import HTTPStatus
import logging
import json # Added for parsing transcription result
import requests # ADDED requests library
from dashscope.audio.asr import VocabularyService # IMPORT VocabularyService

logger = logging.getLogger(__name__)

# It's recommended to set DASHSCOPE_API_KEY in your environment variables.
# If not set, DashScope SDK will try to load it from a default configuration file.
# You can also set it explicitly using: dashscope.api_key = "YOUR_API_KEY"
# For this project, we expect it to be in the environment variables.

def transcribe_audio_dashscope(audio_file_url: str, hotwords: list[str] = None) -> dict:
    """
    Transcribes the given audio file URL using Alibaba Cloud DashScope Speech Transcription
    with the Paraformer-v2 model.

    Args:
        audio_file_url: The publicly accessible URL of the audio file to transcribe.
                        Supported formats include WAV, MP3, M4A, etc.
        hotwords: An optional list of strings to be used as language hints for transcription.

    Returns:
        A dictionary containing the transcription result or an error.
        Example success: {"status": "success", "transcription": "Hello world.", "raw_response": ...}
        Example error: {"status": "error", "message": "Error message"}
    """
    try:
        logger.debug(f"Current DashScope API Key (at point of call): {dashscope.api_key[:5] if dashscope.api_key else 'Not Set'}")
        
        current_model = 'paraformer-v2' # Define the model being used

        call_params = {
            'model': current_model,
            'file_urls': [audio_file_url]
        }
        
        vocabulary_id_to_use = None
        
        if hotwords and isinstance(hotwords, list) and all(isinstance(hw, str) for hw in hotwords) and hotwords:
            logger.info(f"Hotwords provided: {hotwords}. Attempting to create and use a dynamic vocabulary.")
            try:
                service = VocabularyService()
                # Define vocabulary details
                vocab_prefix = "user_temp_vocab" # A prefix for your vocabulary
                # Structure for individual hotwords as per DashScope's advanced usage / vocabulary creation
                hotword_definitions = [{"text": hw, "weight": 4, "lang": "zh"} for hw in hotwords]
                
                logger.info(f"Creating vocabulary with prefix='{vocab_prefix}', model='{current_model}', vocabulary_list={hotword_definitions}")
                
                # Create the vocabulary
                # Note: DashScope might have limits on vocabulary name length or characters if prefix is used in name.
                # The SDK's create_vocabulary might handle naming internally based on prefix.
                created_vocab_id = service.create_vocabulary(
                    prefix=vocab_prefix, # The sample used 'prefix', this is likely for naming/organization.
                    target_model=current_model,
                    vocabulary=hotword_definitions
                )
                
                if created_vocab_id: # create_vocabulary should return the ID string or raise error
                    vocabulary_id_to_use = str(created_vocab_id) # Ensure it's a string
                    call_params['vocabulary_id'] = vocabulary_id_to_use
                    logger.info(f"Successfully created and will use vocabulary_id: {vocabulary_id_to_use}")
                    # If language_hints was previously in call_params, ensure it's removed when using vocabulary_id
                    if 'language_hints' in call_params:
                        del call_params['language_hints']
                        logger.info("Removed 'language_hints' from call_params as 'vocabulary_id' is being used.")
                else:
                    logger.error("Failed to create dynamic vocabulary, create_vocabulary returned a falsy ID.")
                    # Proceed without vocabulary_id, transcription might be less accurate for hotwords.

            except Exception as e_vocab:
                logger.error(f"Error creating dynamic vocabulary for hotwords {hotwords}: {e_vocab}", exc_info=True)
                # Proceed without vocabulary_id if creation fails.
                # Optionally, you could return an error here if hotword accuracy is critical.
        else:
            logger.info("No valid hotwords provided. Not creating or using dynamic vocabulary.")

        # Call the transcription service asynchronously
        logger.info(f"Submitting transcription task with call_params: {call_params}")
        task_response = dashscope.audio.asr.Transcription.async_call(
            **call_params
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
            full_transcription_text = []
            raw_results = transcription_response.output.get('results', [])

            for result_item in raw_results:
                transcription_url = result_item.get('transcription_url')
                if transcription_url:
                    try:
                        with requests.get(transcription_url, stream=True) as r:
                            r.raise_for_status()
                            result_content = r.content.decode('utf-8')
                            logger.info(f"Fetched transcription JSON from {transcription_url}: {result_content[:500]}")
                            result_data = json.loads(result_content)
                        
                        transcripts = result_data.get('transcripts', [])
                        for transcript_item in transcripts:
                            sentences = transcript_item.get('sentences', [])
                            for sentence in sentences:
                                full_transcription_text.append(sentence.get('text', ''))
                    except Exception as e:
                        logger.error(f"Error fetching or parsing transcription result from URL {transcription_url}: {e}")
                else:
                    # This is where the "Failed to convert json string" error was previously observed
                    # If 'code' and 'message' are in result_item, it indicates a subtask failure.
                    if 'message' in result_item:
                         logger.warning(f"No transcription_url found in result item. DashScope subtask message: '{result_item.get('message')}' (Code: {result_item.get('code')}, Status: {result_item.get('subtask_status')}) - Item: {result_item}")
                         # If this specific error occurs, propagate it
                         if result_item.get('message') == 'Failed to convert json string to java object list!':
                             return {"status": "error", "message": f"DashScope ASR subtask failed: {result_item.get('message')}", "raw_response": transcription_response.output}
                    else:
                        logger.warning(f"No transcription_url found in result item and no specific message: {result_item}")


            final_text = " ".join(full_transcription_text).strip()
            return {
                "status": "success",
                "transcription": final_text,
                "raw_response": transcription_response.output
            }
        else:
            logger.error(f"Transcription failed. Status Code: {transcription_response.status_code}, Response: {transcription_response}")
            error_message = "Unknown transcription error."
            raw_output_message = None
            if hasattr(transcription_response, 'output') and transcription_response.output and hasattr(transcription_response.output, 'message'):
                 raw_output_message = transcription_response.output.message
            
            if raw_output_message:
                error_message = raw_output_message
            elif hasattr(transcription_response, 'message') and transcription_response.message:
                error_message = transcription_response.message

            return {"status": "error", "message": f"Transcription failed: {error_message}", "raw_response": transcription_response.output if hasattr(transcription_response, 'output') else transcription_response}

    except Exception as e:
        logger.error(f"An unexpected error occurred during transcription: {e}", exc_info=True)
        return {"status": "error", "message": f"An unexpected server error occurred: {str(e)}"}

# Example Usage (for testing purposes, can be removed or commented out)
if __name__ == '__main__':
    # Ensure DASHSCOPE_API_KEY is set as an environment variable before running this
    # Example: export DASHSCOPE_API_KEY="your_actual_api_key"
    # For local test, you can set it directly:
    # dashscope.api_key = "sk-..." 
    
    if not dashscope.api_key and not os.environ.get("DASHSCOPE_API_KEY"):
        print("Please set the DASHSCOPE_API_KEY environment variable or dashscope.api_key directly to test.")
    else:
        if not dashscope.api_key: # If not set directly, try to use env var for the test print
             print(f"DASHSCOPE_API_KEY found from env: {os.environ.get('DASHSCOPE_API_KEY')[:5]}...")
        else: # API key was set directly
             print(f"DASHSCOPE_API_KEY set directly: {dashscope.api_key[:5]}...")

        test_audio_url_m4a = 'https://dashscope.oss-cn-beijing.aliyuncs.com/samples/audio/paraformer/hello_world_female2.wav'
        test_hotwords = ["你好", "世界", "达摩院"] # Example hotwords
        
        print(f"Testing transcription for URL: {test_audio_url_m4a}")
        result_no_hotwords = transcribe_audio_dashscope(test_audio_url_m4a)
        
        print("\nTranscription Result (without hotwords):")
        if result_no_hotwords['status'] == 'success':
            print(f"  Status: Success")
            print(f"  Transcription: {result_no_hotwords['transcription']}")
        else:
            print(f"  Status: Error")
            print(f"  Message: {result_no_hotwords['message']}")

        print(f"\nTesting transcription for URL: {test_audio_url_m4a} WITH hotwords: {test_hotwords}")
        result_with_hotwords = transcribe_audio_dashscope(test_audio_url_m4a, hotwords=test_hotwords)

        print("\nTranscription Result (with hotwords):")
        if result_with_hotwords['status'] == 'success':
            print(f"  Status: Success")
            print(f"  Transcription: {result_with_hotwords['transcription']}")
        else:
            print(f"  Status: Error")
            print(f"  Message: {result_with_hotwords['message']}")
            # If vocabulary creation failed, the message might indicate that,
            # or it might be a general transcription error if transcription proceeded without vocab_id.
            # Check logs for details on vocabulary_id creation/usage. 