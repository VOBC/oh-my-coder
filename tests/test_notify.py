"""
Tests for src/utils/notify.py

Coverage target: 86% → 95%+
"""

import os
from unittest.mock import MagicMock, patch

from src.utils.notify import (
    notify_quest_update,
    notify_quest_update_dingtalk,
    notify_workflow_complete,
    notify_workflow_complete_dingtalk,
    send_dingtalk_notification,
    send_notification,
)


class TestSendNotification:
    """Test send_notification function."""

    def test_non_darwin_platform(self):
        """On non-macOS, should return False."""
        with patch("sys.platform", "linux"):
            result = send_notification("title", "message")
            assert result is False

    @patch("sys.platform", "darwin")
    @patch("subprocess.run")
    def test_success_with_title_only(self, mock_run):
        """Successfully send notification with title only."""
        mock_run.return_value = MagicMock(returncode=0)
        result = send_notification("Test Title", "Test Message")
        assert result is True
        mock_run.assert_called_once()

    @patch("sys.platform", "darwin")
    @patch("subprocess.run")
    def test_success_with_subtitle(self, mock_run):
        """Successfully send notification with subtitle."""
        mock_run.return_value = MagicMock(returncode=0)
        result = send_notification(
            "Test Title", "Test Message", subtitle="Subtitle"
        )
        assert result is True
        mock_run.assert_called_once()

    @patch("sys.platform", "darwin")
    @patch("subprocess.run")
    def test_success_without_sound(self, mock_run):
        """Successfully send notification without sound."""
        mock_run.return_value = MagicMock(returncode=0)
        result = send_notification("Test Title", "Test Message", sound=False)
        assert result is True
        mock_run.assert_called_once()

    @patch("sys.platform", "darwin")
    @patch("subprocess.run", side_effect=Exception("mock error"))
    def test_exception_handling(self, mock_run):
        """Should return False on exception."""
        result = send_notification("Test Title", "Test Message")
        assert result is False


class TestNotifyWorkflowComplete:
    """Test notify_workflow_complete function."""

    @patch("src.utils.notify.send_notification", return_value=True)
    def test_success(self, mock_send):
        """Successfully notify workflow complete."""
        result = notify_workflow_complete("test_workflow", "completed", 5, 10.5)
        assert result is True
        mock_send.assert_called_once()

    @patch("src.utils.notify.send_notification", return_value=True)
    def test_failed_status(self, mock_send):
        """Notify with failed status (should use ❌ icon)."""
        result = notify_workflow_complete("test_workflow", "failed", 3, 5.2)
        assert result is True
        mock_send.assert_called_once()


class TestNotifyQuestUpdate:
    """Test notify_quest_update function."""

    @patch("src.utils.notify.send_notification", return_value=True)
    def test_success(self, mock_send):
        """Successfully notify quest update."""
        result = notify_quest_update("test_quest", "Quest updated")
        assert result is True
        mock_send.assert_called_once()


class TestSendDingtalkNotification:
    """Test send_dingtalk_notification function."""

    def test_invalid_scheme(self):
        """Invalid URL scheme should return False."""
        result = send_dingtalk_notification(
            "ftp://example.com", "Title", "Message"
        )
        assert result is False

    @patch("urllib.request.urlopen")
    def test_success(self, mock_urlopen):
        """Successfully send DingTalk notification."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"errcode": 0}'
        mock_urlopen.return_value.__enter__ = lambda s: mock_response
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

        result = send_dingtalk_notification(
            "https://oapi.dingtalk.com/robot/send?access_token=xxx",
            "Test Title",
            "Test Message",
        )
        assert result is True

    @patch("urllib.request.urlopen")
    def test_failed_response(self, mock_urlopen):
        """DingTalk API returns errcode != 0."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"errcode": 1, "errmsg": "error"}'
        mock_urlopen.return_value.__enter__ = lambda s: mock_response
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

        result = send_dingtalk_notification(
            "https://oapi.dingtalk.com/robot/send?access_token=xxx",
            "Test Title",
            "Test Message",
        )
        assert result is False

    @patch("urllib.request.urlopen", side_effect=Exception("mock error"))
    def test_exception_handling(self, mock_urlopen):
        """Should return False on exception."""
        result = send_dingtalk_notification(
            "https://oapi.dingtalk.com/robot/send?access_token=xxx",
            "Test Title",
            "Test Message",
        )
        assert result is False


class TestNotifyWorkflowCompleteDingtalk:
    """Test notify_workflow_complete_dingtalk function."""

    @patch("src.utils.notify.send_dingtalk_notification", return_value=True)
    def test_success(self, mock_send):
        """Successfully notify via DingTalk."""
        result = notify_workflow_complete_dingtalk(
            "https://webhook", "test_workflow", "completed", 5, 10.5
        )
        assert result is True

    def test_no_webhook(self):
        """No webhook URL should return False."""
        with patch.dict(os.environ, {}, clear=True):
            result = notify_workflow_complete_dingtalk(
                None, "test_workflow", "completed", 5, 10.5
            )
            assert result is False

    @patch.dict(os.environ, {"DINGTALK_WEBHOOK": "https://env_webhook"})
    @patch("src.utils.notify.send_dingtalk_notification", return_value=True)
    def test_webhook_from_env(self, mock_send):
        """Webhook URL from environment variable."""
        result = notify_workflow_complete_dingtalk(
            None, "test_workflow", "completed", 5, 10.5
        )
        assert result is True
        mock_send.assert_called_once()


class TestNotifyQuestUpdateDingtalk:
    """Test notify_quest_update_dingtalk function."""

    @patch("src.utils.notify.send_dingtalk_notification", return_value=True)
    def test_success(self, mock_send):
        """Successfully notify quest update via DingTalk."""
        result = notify_quest_update_dingtalk(
            "https://webhook", "test_quest", "Quest updated"
        )
        assert result is True

    def test_no_webhook(self):
        """No webhook URL should return False."""
        with patch.dict(os.environ, {}, clear=True):
            result = notify_quest_update_dingtalk(
                None, "test_quest", "Quest updated"
            )
            assert result is False

    @patch.dict(os.environ, {"DINGTALK_WEBHOOK": "https://env_webhook"})
    @patch("src.utils.notify.send_dingtalk_notification", return_value=True)
    def test_webhook_from_env(self, mock_send):
        """Webhook URL from environment variable."""
        result = notify_quest_update_dingtalk(
            None, "test_quest", "Quest updated"
        )
        assert result is True
