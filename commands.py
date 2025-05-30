import json

from venv import logger

import discord
import psutil
import requests
from discord import Client, Message, utils, Member
from datetime import datetime, timedelta
from json import dump

import aiohttp

from const import BOT_VERSION, EXEC_ROLE_ID, INDUSTRY_ROLE_ID, UOA_EXEC_ROLE_ID, MEMBER_ROLE_ID
from funcs import Funcs


class Commands:
    def __init__(self, client: Client, funcs: Funcs):
        self.__eventInMemoryName = None
        self.__eventInMemoryTimeStr = None
        self.__eventInMemoryTime = None
        self.__step = None
        self.__start_time = datetime.now()
        self.__client = client
        self.__funcs = funcs
        self.__currentUserID = -1
        self.__inConvo = False
        self.__currentFunc = False

    # prints all commands

    async def help(self):
        activity_log_channel_id = 1270268706349649940
        commands = {
            '!member': 'Makes the mentioned person a member. exec role is needed to use this command\n',
            '!spam': 'Messages all members reminded them to renew membership. used in january. exec role is needed to use this command.\n',
            '!msgnonmembers': 'Messages all people in the discord who have not yet signed up (excluding industry, adelaide CSC execs) and have been in the discord for more then a week. exec role is needed to use this command.\n',
            '!set event': 'Allows you to create an event with a time.\n',
            '!see events': 'Displays all upcoming events.\n',
            '!del event *event name*': 'Deletes the event\n',
            '!ping': 'pings the bot to test for latency\n',
            '!debug': 'gets debugging information\n'

        }
        otherFuncions = [
            f'When a user leaves a message is sent in <#{
                activity_log_channel_id}> containing the users name and current member count.\n',
            'Automatically does not past events\n']

        txt = 'Commands:\n'
        for key in commands:
            txt += f'{key}: {commands[key]}\n'
        txt += '\nOther Functions:\n'
        for item in otherFuncions:
            txt += f'\u2022 {item}\n'

        return txt

    # adds role to mentioned member
    async def add_role(self, message: Message, roleName='member'):
        if await self.__funcs.check_for_role(message.author, EXEC_ROLE_ID):
            role = utils.get(message.guild.roles, name=roleName)
            UID = await self.__funcs.strip_UID(str(message.content))
            target_member = utils.get(self.__client.get_all_members(), id=UID)

            if not target_member:
                return f'Member with UID {UID} not found.'

            if not await self.__funcs.check_for_role(target_member, MEMBER_ROLE_ID):
                await target_member.add_roles(role)
                return f'Role has been successfully added to <@{UID}>.'
            else:
                return f'{target_member.name} already has member role.'
        else:
            return 'You can not apply member role to users as you are not a executive'

    # messages every member - used to remained people of renewal

    async def renew(self, message: Message):
        if not await self.__funcs.check_for_role(message.author, EXEC_ROLE_ID):
            return 'You can not use this command as you are not an executive.'
        if datetime.now().month != 1:
            return 'It is not January, you dont wanna message everyone yet'
        return 'remove this part to actually be able to send it'

        allUsers = self.__client.get_all_members()

        for user in allUsers:
            print(user.name)
            if user != self.__client.user:
                if await self.__funcs.check_for_role(user, 'member'):
                    channel = await user.create_dm()
                    await channel.send(
                        'Hi,\nThis message has been automatically sent to all members to remained you that your membership to the UniSA Programming community automatically expires on the 1st of January. To continue to partipate in our events please renew it.\nThanks!\nhttps://usasa.sa.edu.au/clubs/join/7520/')
        return 'All members have been reminded of there expiring membership '

    # messages people who have been in the server for more than a week and don't have member or other relent role to sign up

    async def msg_non_members(self, message: Message):
        if await self.__funcs.check_for_role(message.author, EXEC_ROLE_ID) == False:
            return 'You can not use this command as you are not an executive.'
        allUsers = self.__client.get_all_members()

        allUsersList = []
        for user in allUsers:
            allUsersList.append(user)

        nonMembers = []
        ignoredRoles = [MEMBER_ROLE_ID, UOA_EXEC_ROLE_ID,
                        INDUSTRY_ROLE_ID, EXEC_ROLE_ID]

        for user in allUsersList:
            flag = False
            for item in ignoredRoles:
                if await self.__funcs.check_for_role(user, item) == True:
                    flag = True
            if flag == False:
                if (datetime.now() - (user.joined_at.replace(tzinfo=None))).days >= 0:
                    nonMembers.append(user)

        for user in nonMembers:
            if isinstance(user, Member):
                try:
                    channel = await user.create_dm()
                    await channel.send("""Hello,
                        can you please sign up to UPC officially through USASA?
                        It only takes a minute, is completely free and non-unisa students can still join through it. Just having people join through USASA supports the club greatly.

                        We will be removing all members from the discord that are not a member on USASA in a few days.
                        https://usasa.sa.edu.au/clubs/join/upc/

                        Thanks.""")
                except discord.errors.HTTPException:
                    message.channel.send(f'{user.name} could not be messaged')

        return f'{[x.name for x in nonMembers]} have all been direct messaged.'

    async def print_requirements(self, message: Message):
        if not await self.__funcs.check_for_role(message.author, EXEC_ROLE_ID):
            return 'You do not have the required permissions to use this command.'
        try:
            with open('requirements.txt', 'r') as f:
                requirements = f.read()

            if len(requirements) > 2000:
                parts = [requirements[i:i + 2000]
                         for i in range(0, len(requirements), 2000)]
                for part in parts:
                    await message.channel.send(f"```{part}```")
            else:
                await message.channel.send(f"```{requirements}```")
        except FileNotFoundError:
            return "The requirements.txt file could not be found."
        except Exception as e:
            return f"An error occurred: {e}"

        return "Requirements have been printed."

    async def set_event(self, message: Message):
        if not await self.__funcs.check_for_role(message.author, EXEC_ROLE_ID):
            return 'You cannot set an event as you are not an exec.'

        if message.content.startswith('!set event'):
            self.__inConvo = True
            self.__currentUserID = message.author.id
            self.__step = 1
            self.__currentFunc = self.set_event
            return 'Enter events in the format {"event1": "h:m dd/m/yy", "event2": "h:m dd/m/yy"}'

        if self.__step == 1:
            try:
                event_schema = json.loads(message.content)

                for event_name, event_time in event_schema.items():
                    datetime_object = datetime.strptime(
                        event_time, '%H:%M %d/%m/%y')

                    if datetime_object < datetime.now():
                        return f'The event time for {event_name} cannot be in the past.'

                self.__eventInMemorySchema = event_schema
                self.__step = 2
                return f"Events have been registered: {', '.join(event_schema.keys())}. Confirm to save."
            except Exception as ex:
                return f'There was an error parsing the event schema. Please enter the correct format: {"event1": "h:m dd/m/yy", "event2": "h:m dd/m/yy"}.\n{ex}'

        if self.__step == 2:
            guild = message.guild

            for event_name, event_time in self.__eventInMemorySchema.items():

                start_time = datetime.strptime(
                    # Make it timezone-aware
                    event_time, '%H:%M %d/%m/%y').astimezone()
                end_time = start_time + timedelta(hours=6)
                await guild.create_scheduled_event(
                    name=event_name,
                    start_time=start_time,
                    end_time=end_time,
                    entity_type=discord.EntityType.external,
                    location='Adelaide',
                    description=f"This is the {event_name} event.",
                    privacy_level=discord.PrivacyLevel.guild_only
                )

            self.__inConvo = False

            return f'Discord events have been created for: {", ".join(self.__eventInMemorySchema.keys())}.'

    async def print_asset(self, message: Message) -> str:
        split_message = message.content.split()
        if len(split_message) < 2:
            return "Error: Message should contain both domain and icon."

        domain = split_message[1]
        icon = split_message[2]
        asset_url = f"https://unisa-programming-community.netlify.app/{
            domain}/{icon}.png"

        if await self.is_valid_image(asset_url):
            return asset_url
        else:
            return "Error: The generated URL is not a valid image."

    async def is_valid_image(self, url: str) -> bool:
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as response:
                    if response.status == 200 and 'image' in response.headers['Content-Type']:
                        return True
            except aiohttp.ClientError:
                return False
        return False

    async def display_events(self):
        with open('events.json', 'r') as file:
            unordered_events = json.load(file)

        sorted_events = sorted(
            unordered_events.items(),
            key=lambda item: datetime.strptime(item[1], '%H:%M %d/%m/%y'),
            reverse=False
        )

        print_events = ["**Upcoming events**"]
        for name, time in sorted_events:
            print_events.append(f'{name} - {time}')

        return '\n'.join(print_events)

    async def delete_event(self, message: Message):
        if not self.__funcs.check_for_role(message.author, EXEC_ROLE_ID):
            return 'you can not delete a event as you are not an exec'
        text = message.content.split()
        text = ' '.join(text[2::])

        events = await self.__funcs.load_json()
        try:
            events.pop(text)
            with open("events.json", 'w') as f:
                dump(events, f)
            return 'Event deleted'
        except KeyError:
            return 'Event does not exist'

    async def ping(self):
        latency = round(self.__client.latency * 1000)
        return f'Pong! {latency}ms'

    async def debug(self):
        memory_usage = psutil.Process().memory_info().rss / 1024 / 1024  # Memory in MB
        current_time = datetime.now()
        uptime = current_time - self.__start_time
        uptime_str = str(timedelta(seconds=int(uptime.total_seconds())))
        latency = round(self.__client.latency * 1000)

        response = requests.get('https://api.ipify.org?format=json')
        data = response.json()

        cpu_freq = psutil.cpu_freq()
        if cpu_freq:
            current_speed = cpu_freq.current
            CPU_response = f"Current CPU Speed: {current_speed:.2f} MHz\n"
        else:
            CPU_response = "Could not retrieve CPU speed information."

        debug_info = (
            f"**Bot Debug Info**:\n"
            f"Version: {BOT_VERSION}\n"
            f"Latency: {latency}ms\n"
            f"IP Address: {data["ip"]}\n"
            f"Uptime: {uptime_str}\n"
            f"Previous Start Time: {self.__start_time}\n"
            f"Memory Usage: {memory_usage:.2f} MB\n"
            f"{CPU_response}"

        )

        return debug_info

    def get_inConvo(self):
        return self.__inConvo

    def get_currentFunc(self):
        return self.__currentFunc

    def get_currentUserID(self):
        return self.__currentUserID

    inConvo = property(get_inConvo)
    currentFunc = property(get_currentFunc)
    currentUserID = property(get_currentUserID)
