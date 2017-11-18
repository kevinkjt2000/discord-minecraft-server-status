from unittest.mock import patch, mock_open, MagicMock
import asyncio
import asynctest
import discord
import random
import unittest
import src.main


class TestMain(unittest.TestCase):
    @patch('src.main.main')
    def test__init_calls_main_once(self, mock_main):
        with patch.object(src.main, '__name__', '__main__'):
            src.main.init()
            mock_main.assert_called_once_with()

    @patch('builtins.open', new_callable=mock_open, read_data="{}")
    def test__get_minecraft_object_can_read_empty_json(self, mock_open):
        mc = src.main.get_minecraft_object_for_server_channel(42, 5)
        assert not mc

    @patch('builtins.open', new_callable=mock_open,
           read_data="""{"42": {"5": {"host": "fake_host", "port": 1234}}}""")
    def test__get_minecraft_object_can_read_host_and_port(self, mock_open):
        mc = src.main.get_minecraft_object_for_server_channel(42, 5)
        assert mc.mc_server.host == "fake_host"
        assert mc.mc_server.port == 1234


class TestBot(asynctest.TestCase):
    def setUp(self):
        self.mock_server_id = str(random.randrange(999999))
        self.mock_channel_id = str(random.randrange(999999))
        self.mock_mc = MagicMock(spec=src.main.Minecraft)
        self.bot = src.main.Bot()
        self.bot.user = self._get_mock_user(bot=True)
        self.mock_run = asynctest.patch.object(self.bot, 'run')
        self.mock_run.start()

    def tearDown(self):
        self.mock_run.stop()
        yield from self.bot.close()

    async def test__status_command_responds_even_with_connection_errors(self):
        self.mock_mc.get_formatted_status_message.side_effect = \
            ConnectionRefusedError

        with patch(
            'src.main.get_minecraft_object_for_server_channel',
            return_value=self.mock_mc,
        ):
            mock_message = self._get_mock_command_message('!status')
            with asynctest.patch.object(self.bot, 'send_message') as mock_send:
                await self.bot.on_message(mock_message)
                await asyncio.sleep(0.3)
                self.mock_mc.get_formatted_status_message.assert_called_once()
                mock_send.assert_called_once_with(
                    mock_message.channel,
                    'The server is not accepting connections at this time.',
                )

    async def test__status_command_responds_with_status_message(self):
        with patch(
            'src.main.get_minecraft_object_for_server_channel',
            return_value=self.mock_mc,
        ):
            mock_message = self._get_mock_command_message('!status')
            with asynctest.patch.object(self.bot, 'send_message') as mock_send:
                await self.bot.on_message(mock_message)
                await asyncio.sleep(0.3)
                self.mock_mc.get_formatted_status_message.assert_called_once()
                mock_send.assert_called_once_with(
                    mock_message.channel,
                    self.mock_mc.get_formatted_status_message(),
                )

    def _get_mock_command_message(self, command):
        return self._get_mock_message(command, channel=self.mock_channel_id)

    def _get_mock_channel(self, **kwargs):
        id = kwargs.pop('id', str(random.randrange(999999)))
        return asynctest.MagicMock(
            spec=discord.Channel,
            id=id,
        )

    def _get_mock_server(self):
        return asynctest.MagicMock(
            spec=discord.Server,
            id=self.mock_server_id,
            me=self.bot.user,
        )

    def _get_mock_message(self, content, **kwargs):
        channel = kwargs.pop('channel', self._get_mock_channel())
        server = kwargs.pop('server', self._get_mock_server())
        if type(channel) is str:
            channel = self._get_mock_channel(id=channel)
        return asynctest.MagicMock(
            spec=discord.Message,
            author=self._get_mock_user(),
            channel=channel,
            server=server,
            content=content,
            mentions=[],
        )

    def _get_mock_user(self, bot=None):
        return asynctest.MagicMock(
            spec=discord.User,
            id=str(random.randrange(999999)),
            name='mock_user',
            bot=bot,
        )
