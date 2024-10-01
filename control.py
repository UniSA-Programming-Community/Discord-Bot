from discord import Client, Message

from commands import Commands


class Control:
    def __init__(self, client: Client, commands: Commands):
        self.__client = client

        self.__commands = commands

    async def send_message(self, message: Message) -> None:
        message_content = message.content

        if not message_content:
            print('user message is empty')
            return

        response: str = await self.get_response(message)
        if response:
            await message.channel.send(response)

    # finds the appropriate function to call based on the message content
    async def get_response(self, message: Message):
        message_content = message.content.lower()

        if self.__commands.inConvo and message.author.id == self.__commands.currentUserID:
            return await self.__commands.currentFunc(message)

        if not message_content.startswith('!'):
            return False

        command_mapping = {
            '!member': self.__commands.add_role,
            '!spam': self.__commands.renew,
            '!msgnonmembers': self.__commands.msg_non_members,
            '!help': self.__commands.help,
            '!set event': self.__commands.set_event,
            '!see events': self.__commands.display_events,
            '!del event': self.__commands.delete_event,
            '!ping': self.__commands.ping,
            '!debug': self.__commands.debug
        }

        command = message_content.split()[0]
        command_func = command_mapping.get(command)

        if command_func:
            return await command_func(message)

        return False

