import psutil
import requests
from discord import Client, Message, utils
from datetime import datetime, timedelta
from json import dump

from const import BOT_VERSION, EXEC_ROLE_ID, INDUSTRY_ROLE_ID, UOA_EXEC_ROLE_ID, MEMBER_ROLE_ID
from funcs import Funcs


class Commands:
    def __init__(self, client: Client, funcs: Funcs):
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
            f'When a user leaves a message is sent in <#{activity_log_channel_id}> containing the users name and current member count.\n',
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
            UID = self.__funcs.strip_UID(str(message.content))
            target_member = utils.get(self.__client.get_all_members(), id=UID)

            if not await self.__funcs.check_for_role(target_member, MEMBER_ROLE_ID):
                await target_member.add_roles(role)
                return f'Role has been successfully added to {target_member.name}.'
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
        if not await self.__funcs.check_for_role(message.author, EXEC_ROLE_ID):
            return 'You can not use this command as you are not an executive.'
        allUsers = self.__client.get_all_members()

        allUsersList = []
        for user in allUsers:
            allUsersList.append(user)

        nonMembers = []
        ignoredRoles = [MEMBER_ROLE_ID, UOA_EXEC_ROLE_ID, INDUSTRY_ROLE_ID, EXEC_ROLE_ID]

        for user in allUsersList:
            flag = False
            for item in ignoredRoles:
                if await self.__funcs.check_for_role(user, item):
                    flag = True
            if not flag:
                if (datetime.now() - (user.joined_at.replace(tzinfo=None))).days >= 7:
                    nonMembers.append(user)

        # for user in nonMembers:
        #     if isinstance(user, Member):
        #         try:
        #             channel = await user.create_dm()
        #             await channel.send('Hi,\nYou have been in the UniSA Open Source Community discord for more then a week, and still have not signed up.\nIt only takes a minute to sign up, is free and you don't need to be a UniSA student to do it. Signing up is the best way to support our club and allow us to host as many future events as possible.\nhttps://usasa.sa.edu.au/clubs/join/7520/')
        #         except discord.errors.HTTPException:
        #             print(f"{user.name} could not be messaged")

        return f'{[x.name for x in nonMembers]} have all been direct messaged. - not actually code is commented out'

    async def set_event(self, message: Message):
        # Check if user has the required role
        if not await self.__funcs.check_for_role(message.author, EXEC_ROLE_ID):
            return 'You cannot set an event as you are not a member of the exec team.'

        if not self.__inConvo:
            __eventInMemoryTime = None
            __eventInMemoryTimeStr = None
            __eventInMemoryName = None

        if message.content.startswith('!set event'):
            self.__inConvo = True
            self.__currentUserID = message.author.id
            self.__step = 1
            self.__currentFunc = self.set_event
            return 'Please enter the event date/time in the format (HH:MM DD/MM/YY).'

        if self.__step == 1:
            try:
                __eventInMemoryTime = datetime.strptime(message.content, '%H:%M %d/%m/%y')
                __eventInMemoryTimeStr = __eventInMemoryTime.strftime('%H:%M %d/%m/%y')
                self.__step = 2
                return f'Time is set to {__eventInMemoryTime}. Now, enter the name of the event.'
            except ValueError:
                return 'Invalid time format. Please enter the time in the format (HH:MM DD/MM/YY).'

        if self.__step == 2:
            __eventInMemoryName = message.content
            await self.__funcs.save_event(__eventInMemoryName, __eventInMemoryTimeStr)
            self.__inConvo = False
            return f'Event "{__eventInMemoryName}" has been saved for {__eventInMemoryTimeStr}.'

    async def display_events(self):
        unorderedEvents = self.__funcs.load_json()
        eventOrder = self.__funcs.sort_events(unorderedEvents)

        txt = ''
        for item in eventOrder:
            if datetime.strptime(unorderedEvents[item], '%H:%M %d/%m/%y') > datetime.now():
                txt += f'{item} - {unorderedEvents[item]}\n'
        return txt

    async def delete_event(self, message: Message):
        if not self.__funcs.check_for_role(message.author, EXEC_ROLE_ID):
            return 'you can not delete a event as you are not an exec'
        text = message.content.split()
        text = ' '.join(text[2::])

        events = self.__funcs.load_json()
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
