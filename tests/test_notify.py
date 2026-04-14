"""
通知模块测试
"""

from unittest.mock import MagicMock, patch


class TestDesktopNotification:
    """测试桌面通知"""

    @patch("src.utils.notify.subprocess.run")
    def test_send_notification_darwin(self, mock_run):
        """测试 macOS 通知发送"""
        mock_run.return_value = MagicMock(returncode=0)

        from src.utils.notify import send_notification

        with patch("sys.platform", "darwin"):
            result = send_notification("Test", "Hello")
            assert result is True
            mock_run.assert_called_once()

    def test_send_notification_non_darwin(self):
        """测试非 macOS 平台返回 False"""
        from src.utils.notify import send_notification

        with patch("sys.platform", "linux"):
            result = send_notification("Test", "Hello")
            assert result is False

    def test_notify_workflow_complete(self):
        """测试工作流完成通知"""
        from src.utils.notify import notify_workflow_complete

        with patch("src.utils.notify.send_notification") as mock_send:
            mock_send.return_value = True
            result = notify_workflow_complete("build", "completed", 5, 10.5)
            assert result is True
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert "工作流完成" in call_args[1]["title"]

    def test_notify_quest_update(self):
        """测试 Quest 更新通知"""
        from src.utils.notify import notify_quest_update

        with patch("src.utils.notify.send_notification") as mock_send:
            mock_send.return_value = True
            result = notify_quest_update("MyQuest", "Step 1 done")
            assert result is True
            mock_send.assert_called_once()


class TestDingTalkNotification:
    """测试钉钉通知"""

    @patch("src.utils.notify.urllib.request.urlopen")
    def test_send_dingtalk_notification_success(self, mock_urlopen):
        """测试钉钉通知发送成功"""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"errcode": 0}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        from src.utils.notify import send_dingtalk_notification

        result = send_dingtalk_notification(
            "https://oapi.dingtalk.com/robot/send?access_token=xxx",
            "Test Title",
            "Test Message",
        )
        assert result is True

    @patch("src.utils.notify.urllib.request.urlopen")
    def test_send_dingtalk_notification_failure(self, mock_urlopen):
        """测试钉钉通知发送失败"""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"errcode": 400001, "errmsg": "error"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        from src.utils.notify import send_dingtalk_notification

        result = send_dingtalk_notification(
            "https://oapi.dingtalk.com/robot/send?access_token=xxx",
            "Test Title",
            "Test Message",
        )
        assert result is False

    def test_notify_workflow_complete_dingtalk_no_webhook(self):
        """测试无 webhook 时返回 False"""
        from src.utils.notify import notify_workflow_complete_dingtalk

        with patch.dict("os.environ", {}, clear=True):
            result = notify_workflow_complete_dingtalk(
                None, "build", "completed", 5, 10.5
            )
            assert result is False

    @patch("src.utils.notify.send_dingtalk_notification")
    def test_notify_workflow_complete_dingtalk_with_env(self, mock_send):
        """测试从环境变量读取 webhook"""
        mock_send.return_value = True

        from src.utils.notify import notify_workflow_complete_dingtalk

        with patch.dict(
            "os.environ",
            {"DINGTALK_WEBHOOK": "https://oapi.dingtalk.com/robot/send?token=xxx"},
        ):
            result = notify_workflow_complete_dingtalk(
                None, "build", "completed", 5, 10.5, "/path/to/project"
            )
            assert result is True
            mock_send.assert_called_once()

    @patch("src.utils.notify.send_dingtalk_notification")
    def test_notify_quest_update_dingtalk(self, mock_send):
        """测试 Quest 钉钉通知"""
        mock_send.return_value = True

        from src.utils.notify import notify_quest_update_dingtalk

        with patch.dict(
            "os.environ",
            {"DINGTALK_WEBHOOK": "https://oapi.dingtalk.com/robot/send?token=xxx"},
        ):
            result = notify_quest_update_dingtalk(
                None, "MyQuest", "Quest completed", "completed"
            )
            assert result is True
            mock_send.assert_called_once()
