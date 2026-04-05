"""
Unit tests for error handling module.

Tests verify error code definitions, error_response, and success_response functions.
"""

from mail_manager.errors import ErrorCodes, error_response, success_response


class TestErrorCodes:
    """Tests for error code definitions."""

    def test_user_codes_start_with_user(self) -> None:
        """USER codes have USER_ prefix."""
        assert ErrorCodes.USER_EMAIL_NOT_FOUND.startswith("USER_")
        assert ErrorCodes.USER_INVALID_MESSAGE_ID.startswith("USER_")
        assert ErrorCodes.USER_MISSING_PARAMETER.startswith("USER_")
        assert ErrorCodes.USER_INVALID_PARAMETER.startswith("USER_")

    def test_server_codes_start_with_server(self) -> None:
        """SERVER codes have SERVER_ prefix."""
        assert ErrorCodes.SERVER_IMAP_CONNECTION_FAILED.startswith("SERVER_")
        assert ErrorCodes.SERVER_SMTP_CONNECTION_FAILED.startswith("SERVER_")
        assert ErrorCodes.SERVER_SMTP_SEND_FAILED.startswith("SERVER_")
        assert ErrorCodes.SERVER_DATABASE_ERROR.startswith("SERVER_")
        assert ErrorCodes.SERVER_CHROMADB_ERROR.startswith("SERVER_")

    def test_biz_codes_start_with_biz(self) -> None:
        """BIZ codes have BIZ_ prefix."""
        assert ErrorCodes.BIZ_EMAIL_ALREADY_SENT.startswith("BIZ_")
        assert ErrorCodes.BIZ_PERMISSION_DENIED.startswith("BIZ_")
        assert ErrorCodes.BIZ_ACCOUNT_NOT_CONFIGURED.startswith("BIZ_")


class TestErrorResponse:
    """Tests for error_response function."""

    def test_error_response_has_status_error(self) -> None:
        """error_response returns status: error."""
        result = error_response(ErrorCodes.USER_EMAIL_NOT_FOUND, "Not found")
        assert result["status"] == "error"

    def test_error_response_includes_code(self) -> None:
        """error_response includes error code."""
        result = error_response(ErrorCodes.USER_EMAIL_NOT_FOUND, "Not found")
        assert result["code"] == ErrorCodes.USER_EMAIL_NOT_FOUND

    def test_error_response_includes_message(self) -> None:
        """error_response includes message."""
        result = error_response(ErrorCodes.USER_EMAIL_NOT_FOUND, "Email not found")
        assert result["message"] == "Email not found"

    def test_error_response_has_three_keys(self) -> None:
        """error_response has exactly status, code, and message."""
        result = error_response(ErrorCodes.SERVER_IMAP_CONNECTION_FAILED, "Connection failed")
        assert set(result.keys()) == {"status", "code", "message"}

    def test_error_response_with_different_codes(self) -> None:
        """error_response works with different error codes."""
        result = error_response(ErrorCodes.SERVER_SMTP_SEND_FAILED, "SMTP error")
        assert result["code"] == ErrorCodes.SERVER_SMTP_SEND_FAILED
        assert result["status"] == "error"


class TestSuccessResponse:
    """Tests for success_response function."""

    def test_success_response_has_status_success(self) -> None:
        """success_response returns status: success."""
        result = success_response()
        assert result["status"] == "success"

    def test_success_response_includes_default_message(self) -> None:
        """success_response includes default message."""
        result = success_response()
        assert result["message"] == "Success"

    def test_success_response_includes_custom_message(self) -> None:
        """success_response includes custom message."""
        result = success_response(message="Email sent successfully")
        assert result["message"] == "Email sent successfully"

    def test_success_response_includes_data(self) -> None:
        """success_response merges data into response."""
        result = success_response(data={"count": 5, "results": []})
        assert result["count"] == 5
        assert result["results"] == []

    def test_success_response_with_data_and_message(self) -> None:
        """success_response can have both data and message."""
        result = success_response(data={"email_id": "abc123"}, message="Email saved")
        assert result["status"] == "success"
        assert result["message"] == "Email saved"
        assert result["email_id"] == "abc123"

    def test_success_response_without_data(self) -> None:
        """success_response without data has only status and message."""
        result = success_response(message="Operation completed")
        assert result["status"] == "success"
        assert result["message"] == "Operation completed"
        assert "data" not in result


class TestErrorResponseFormat:
    """Tests for error response format consistency."""

    def test_all_user_errors_are_strings(self) -> None:
        """All error codes should be strings."""
        assert isinstance(ErrorCodes.USER_EMAIL_NOT_FOUND, str)
        assert isinstance(ErrorCodes.USER_INVALID_MESSAGE_ID, str)

    def test_all_server_errors_are_strings(self) -> None:
        """All server error codes should be strings."""
        assert isinstance(ErrorCodes.SERVER_IMAP_CONNECTION_FAILED, str)
        assert isinstance(ErrorCodes.SERVER_SMTP_SEND_FAILED, str)

    def test_error_response_is_json_serializable(self) -> None:
        """error_response result should be JSON serializable."""
        import json

        result = error_response(ErrorCodes.USER_EMAIL_NOT_FOUND, "Not found")
        # Should not raise
        json_str = json.dumps(result)
        assert '"status": "error"' in json_str

    def test_success_response_is_json_serializable(self) -> None:
        """success_response result should be JSON serializable."""
        import json

        result = success_response(data={"count": 1})
        # Should not raise
        json_str = json.dumps(result)
        assert '"status": "success"' in json_str
