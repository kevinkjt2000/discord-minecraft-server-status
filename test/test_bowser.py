from unittest.mock import patch, MagicMock
import asyncio
import random
import asynctest
import discord
from discord.ext import commands
import mockredis
from bowser.bowser import Bowser


class TestBowser(asynctest.TestCase):
    async def setUp(self):
        self.mock_server_id = str(random.randrange(999999))
        self.mock_channel_id = str(random.randrange(999999))
        self.patch_mc = patch('bowser.bowser.Minecraft')
        self.mock_mc = self.patch_mc.start()()
        fake_data = {'host': 'fake_host', 'port': 123}
        self.mock_mc.mc_server.host = fake_data['host']
        self.mock_mc.mc_server.port = fake_data['port']
        self.patch_db = patch('bowser.database.redis.StrictRedis',
                              mockredis.mock_strict_redis_client)
        self.patch_db.start()
        self.bot = commands.Bot(command_prefix=commands.when_mentioned_or('!'))
        self.bowser = Bowser(self.bot)
        self.bot.add_cog(self.bowser)
        self.bowser.db.set_data_of_server_channel(self.mock_server_id, self.mock_channel_id, fake_data)
        self.bot.user = self._get_mock_user(bot=True)
        self.patch_run = asynctest.patch.object(self.bot, 'run')
        self.patch_run.start()
        self.patch_send = asynctest.patch.object(self.bot, 'send_message')
        self.mock_send = self.patch_send.start()

    async def tearDown(self):
        self.patch_send.stop()
        self.patch_run.stop()
        self.patch_db.stop()
        self.patch_mc.stop()
        await self.bot.close()

    async def test__support_dms_by_ignoring_attribute_errors(self):
        mock_message = self._get_mock_command_message('!help')
        mock_message.server = None
        await self.bot.on_message(mock_message)
        await asyncio.sleep(0.02)
        assert self.mock_send.call_count == 1

        mock_message = self._get_mock_command_message('!ip')
        mock_message.server = None
        await self.bot.on_message(mock_message)
        await asyncio.sleep(0.02)
        assert self.mock_send.call_count == 2

    async def test__command_missing_arguments_prints_how_to_get_help(self):
        mock_message = self._get_mock_command_message('!set not_enough')
        mock_message.channel.permissions_for.return_value = discord.permissions.Permissions()
        mock_message.channel.permissions_for.return_value.administrator = True
        await self.bot.on_message(mock_message)
        await asyncio.sleep(0.02)
        self.mock_send.assert_called_once_with(
            mock_message.channel,
            f'Not enough arguments.  Try `!help set` for more information.',
        )

    async def test__owner_can_add_a_server(self):
        mock_message = self._get_mock_command_message(f'!set {self.mock_mc.mc_server.host} {self.mock_mc.mc_server.port}')
        mock_message.channel.permissions_for.return_value = discord.permissions.Permissions()
        mock_message.author = mock_message.server.owner
        await self.bot.on_message(mock_message)
        await asyncio.sleep(0.02)
        self.mock_send.assert_called_once_with(
            mock_message.channel,
            f'Finished adding `{self.mock_mc.mc_server.host}:{self.mock_mc.mc_server.port}`.  Try `!status` now.',
        )

    async def test__nonadmin_cannot_add_a_server(self):
        mock_message = self._get_mock_command_message(f'!set {self.mock_mc.mc_server.host} {self.mock_mc.mc_server.port}')
        mock_message.channel.permissions_for.return_value = discord.permissions.Permissions()
        await self.bot.on_message(mock_message)
        await asyncio.sleep(0.02)
        self.mock_send.assert_called_once_with(
            mock_message.channel,
            'You do not have permission to run this command.',
        )

    async def test__can_fetch_motd(self):
        mock_message = self._get_mock_command_message('!motd')
        await self.bot.on_message(mock_message)
        self.mock_mc.get_motd.assert_called_once()
        self.mock_send.assert_called_once_with(
            mock_message.channel,
            self.mock_mc.get_motd(),
        )

    async def test__can_fetch_forge_version(self):
        mock_message = self._get_mock_command_message('!forge_version')
        await self.bot.on_message(mock_message)
        self.mock_mc.get_forge_version_message.assert_called_once()
        self.mock_send.assert_called_once_with(
            mock_message.channel,
            self.mock_mc.get_forge_version_message(),
        )

    async def test__errors_in_command_execution_are_logged(self):
        self.mock_mc.get_formatted_status_message.side_effect = Exception
        await self._assert_status_command_responds_with(
            'Ninjas hijacked the packets, but the author will fix it.')

    async def test__tells_the_user_when_the_ip_is_bad(self):
        from socket import gaierror
        self.mock_mc.get_formatted_status_message.side_effect = gaierror
        await self._assert_status_command_responds_with(
            'The !ip is unreachable; complain to someone in charge.')

    async def test__bot_gives_up_on_discord_command_errors(self):
        self.mock_mc.get_formatted_status_message.side_effect = \
            discord.ext.commands.errors.CommandError
        await self._assert_status_command_responds_with(
            'The bot is giving up; something unknown happened.')

    async def test__command_not_found_is_ignored(self):
        mock_message = self._get_mock_command_message('!lalala')
        await self.bot.on_message(mock_message)
        self.mock_send.assert_not_called()

    async def test__ip_command_responds_with_host_and_port(self):
        mock_message = self._get_mock_command_message('!ip')
        await self.bot.on_message(mock_message)
        self.mock_send.assert_called_once_with(
            mock_message.channel,
            f'{self.mock_mc.mc_server.host}:{self.mock_mc.mc_server.port}',
        )

    async def test__status_command_warns_about_missing_server(self):
        mock_message = self._get_mock_command_message('!status')
        mock_message.channel = self._get_mock_channel(id='some unconfigured channel')
        await self.bot.on_message(mock_message)
        self.mock_mc.get_formatted_status_message.assert_not_called()
        await asyncio.sleep(0.02)
        self.mock_send.assert_called_once_with(mock_message.channel,
            'There is not yet a Minecraft server configured for this discord'
            ' server channel.')

    async def test__status_command_when_the_server_does_not_respond(self):
        self.mock_mc.get_formatted_status_message.side_effect = OSError
        await self._assert_status_command_responds_with(
            'Server did not respond with any information.')

    async def test__status_command_responds_even_with_connection_errors(self):
        self.mock_mc.get_formatted_status_message.side_effect = \
            ConnectionRefusedError
        await self._assert_status_command_responds_with(
            'The server is not accepting connections at this time.')

    async def test__status_command_responds_with_status_message(self):
        msg = self.mock_mc.get_formatted_status_message()
        self.mock_mc.get_formatted_status_message.reset_mock()
        await self._assert_status_command_responds_with(msg)

    async def _assert_status_command_responds_with(self, message):
        mock_message = self._get_mock_command_message('!status')
        await self.bot.on_message(mock_message)
        self.mock_mc.get_formatted_status_message.assert_called_once()
        await asyncio.sleep(0.02)
        self.mock_send.assert_called_once_with(mock_message.channel, message)

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
        if isinstance(channel, str):
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
            spec=discord.Member,
            id=str(random.randrange(999999)),
            name='mock_user',
            bot=bot,
        )