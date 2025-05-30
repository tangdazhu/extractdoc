import os
import logging
from django.conf import settings
from pathlib import Path # Ensure Path is imported
import shutil # Added for rmtree

logger = logging.getLogger('converter')

def ensure_user_directories(username: str, date_str: str) -> tuple[str, str]:
    """
    Ensures that the daily upload and converted files directories for a user exist.

    Args:
        username: The username.
        date_str: The date string in YYYYMMDD format.

    Returns:
        A tuple containing the paths to (user_upload_dir, user_converted_dir).
    """
    try:
        base_dir_for_user_data = Path(settings.BASE_DIR) / 'his_pic'
        user_base_dir = base_dir_for_user_data / username / date_str
        user_upload_dir = user_base_dir / 'uploads'
        user_converted_dir = user_base_dir / 'converted_files'

        os.makedirs(user_upload_dir, exist_ok=True)
        os.makedirs(user_converted_dir, exist_ok=True)
        
        logger.info(f"Ensured daily directories exist: Uploads='{user_upload_dir}', Converted='{user_converted_dir}' for user '{username}' on {date_str}")
        return str(user_upload_dir), str(user_converted_dir)
    except Exception as e:
        logger.error(f"Error ensuring user directories for {username} on {date_str}: {e}", exc_info=True)
        # In case of an error, returning paths that might not exist could lead to further issues.
        # Depending on desired error handling, could raise exception or return (None, None)
        raise  # Re-raise the exception to be handled by the caller

def generate_safe_filename(original_filename: str) -> str:
    """Generates a safe filename from the original filename."""
    return Path(original_filename).name

def save_uploaded_file(uploaded_file_obj, upload_dir: str, request_id: str) -> tuple[str | None, str | None, str | None]:
    """
    Saves an uploaded file to the specified upload directory with a unique name.

    Args:
        uploaded_file_obj: The uploaded file object from request.FILES.
        upload_dir: The directory to save the uploaded file to.
        request_id: The unique request ID for this conversion process.

    Returns:
        A tuple (temp_input_path, original_filename, safe_original_filename).
        Returns (None, None, None) if saving fails.
    """
    try:
        original_filename = uploaded_file_obj.name
        safe_original_filename = generate_safe_filename(original_filename)
        
        temp_input_base, temp_input_ext = os.path.splitext(safe_original_filename)
        # Ensure request_id is part of the filename to maintain uniqueness across requests if needed by caller
        temp_input_filename = f"{temp_input_base}_{request_id}_input{temp_input_ext}"
        temp_input_path = os.path.join(upload_dir, temp_input_filename)

        with open(temp_input_path, 'wb+') as destination:
            for chunk in uploaded_file_obj.chunks():
                destination.write(chunk)
        
        logger.info(f"Uploaded and saved temporary input file: {temp_input_path} for original: {original_filename}. RequestID: {request_id}")
        return temp_input_path, original_filename, safe_original_filename
    except Exception as e:
        original_filename_for_log = getattr(uploaded_file_obj, 'name', 'Unknown Filename')
        logger.error(f"Error saving uploaded file {original_filename_for_log} for RequestID {request_id}: {e}", exc_info=True)
        return None, original_filename_for_log, None # Return original_filename for error reporting

def delete_user_data_folder(username: str) -> tuple[bool, str]:
    """
    Deletes the entire data folder for a given user.
    (e.g., his_pic/<username>)

    Args:
        username: The username whose data folder is to be deleted.

    Returns:
        A tuple (success_status, message).
    """
    user_folder_path = Path(settings.BASE_DIR) / 'his_pic' / username
    if user_folder_path.exists() and user_folder_path.is_dir():
        try:
            shutil.rmtree(user_folder_path)
            message = f"User '{username}\'s data folder and all its contents have been successfully deleted."
            logger.info(f"Deleted entire user data folder for {username} at {user_folder_path}")
            return True, message
        except OSError as e:
            message = f"Error deleting data folder for user '{username}\': {e}"
            logger.error(f"Error deleting user data folder for {username} at {user_folder_path}: {e}")
            return False, message
    elif not user_folder_path.exists():
        message = f"User '{username}\'s data folder does not exist. No action taken."
        logger.info(message)
        return True, message # Not an error if it doesn't exist, it's already gone.
    else:
        message = f"Path for user '{username}\'s data ({user_folder_path}) is not a directory."
        logger.warning(message)
        return False, message

def cleanup_temp_files(file_paths_to_delete: list[str], request_id: str, remove_dirs: bool = False):
    """
    Safely deletes a list of temporary files or directories, logging any errors.

    Args:
        file_paths_to_delete: A list of absolute file/directory paths to delete.
        request_id: The unique request ID for logging context.
        remove_dirs: If True, allows deletion of directories using shutil.rmtree. 
                     Otherwise, only files will be deleted.
    """
    if not file_paths_to_delete:
        return

    logger.debug(f"Attempting to cleanup {len(file_paths_to_delete)} temporary items. RequestID: {request_id}. Remove Dirs: {remove_dirs}")
    for item_path in file_paths_to_delete:
        if item_path and os.path.exists(item_path):
            try:
                if os.path.isdir(item_path):
                    if remove_dirs:
                        shutil.rmtree(item_path)
                        logger.info(f"Successfully cleaned up temporary directory (and its contents): {item_path}. RequestID: {request_id}")
                    else:
                        logger.warning(f"Skipping directory {item_path} because remove_dirs is False. RequestID: {request_id}")
                elif os.path.isfile(item_path):
                    os.remove(item_path)
                    logger.info(f"Successfully cleaned up temporary file: {item_path}. RequestID: {request_id}")
                else:
                    logger.warning(f"Item {item_path} is neither a file nor a directory. Skipping. RequestID: {request_id}")
            except OSError as e:
                logger.warning(f"Failed to delete temporary item {item_path}: {e}. RequestID: {request_id}")
        elif item_path:
            logger.debug(f"Temporary item path {item_path} does not exist, skipping cleanup. RequestID: {request_id}") 