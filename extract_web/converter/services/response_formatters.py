import logging
from typing import List, Dict, Any, Optional
from django.http import JsonResponse

logger = logging.getLogger("converter")


def format_json_response(
    results: List[Dict[str, Any]],
    merge_output: bool,
    overall_status: int = 200,  # HTTP status code for the response
    error_message: Optional[
        str
    ] = None,  # General error message if the whole request fails early
    request_id: Optional[str] = None,
    duration_seconds: Optional[float] = None,  # ADDED duration_seconds
) -> JsonResponse:
    """
    Formats a standardized JSON response for the conversion process.

    Args:
        results: A list of dictionaries, where each dictionary represents a processed file
                 and contains keys like 'original_name', 'converted_name', 'status', 'message', 'download_url'.
                 Can be empty if a general error occurred before file processing.
        merge_output: Boolean indicating if merge output was requested.
        overall_status: The HTTP status code for the JsonResponse.
        error_message: An optional general error message. If provided, the results list
                       might be a single entry representing this general error.
        request_id: Optional request ID for logging.
        duration_seconds: Optional duration of the conversion process in seconds.

    Returns:
        A Django JsonResponse object.
    """
    response_data = {"results": results, "merge_output": merge_output}

    if request_id:
        response_data["request_id"] = request_id
    if duration_seconds is not None:
        response_data["duration_seconds"] = duration_seconds

    if (
        error_message and not results
    ):  # If it's a general error before processing any file
        response_data["results"] = [
            {
                "original_name": "General Error",
                "status": "error",
                "message": error_message,
            }
        ]
    elif error_message:  # Error message to add alongside potentially partial results
        # This case might need refinement: how to best show a general error with partial results?
        # For now, we log it and it doesn't alter the `results` if they already exist.
        logger.warning(
            f"JsonResponse being formatted with an error_message but also existing results. Error: {error_message}. RequestID: {request_id}"
        )

    # We could add more top-level keys to response_data if needed in the future, e.g., 'request_id'
    # if request_id:
    #     response_data['request_id'] = request_id

    return JsonResponse(response_data, status=overall_status)


# Example of a more specific error formatter (can be expanded)
def format_error_response(
    message: str,
    merge_output: bool,  # Important to maintain this key in all responses
    original_item_name: str = "General Operation",
    http_status: int = 200,  # Usually client errors are still 200 OK if JSON is valid
    request_id: Optional[str] = None,
    duration_seconds: Optional[float] = None,  # 新增参数
) -> JsonResponse:
    """
    Creates a JsonResponse for a single error condition.
    """
    error_result = [
        {"original_name": original_item_name, "status": "error", "message": message}
    ]
    logger.error(
        f"Formatting error response: {message} for item: {original_item_name}. RequestID: {request_id}"
    )
    return format_json_response(
        results=error_result,
        merge_output=merge_output,
        overall_status=http_status,
        request_id=request_id,
        duration_seconds=duration_seconds,
    )
