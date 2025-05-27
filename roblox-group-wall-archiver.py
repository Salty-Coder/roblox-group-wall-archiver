from typing import Set, List

from jinja2 import Environment, FileSystemLoader
from datetime import datetime, timezone
from pathlib import Path
from enum import Enum
from getpass import getpass

from dateutil.parser import parse
from timeit import default_timer as timer

import os
import aiofiles
import aiohttp
import asyncio
import shutil

import typer
import json
import questionary

root_path = Path(__file__).parent
html_assets_path = root_path / "html_assets"
cached_images_path = root_path / "cached_images"

template_loader = FileSystemLoader(searchpath=html_assets_path)
template_environment = Environment(loader=template_loader, enable_async=True)

index_template = template_environment.get_template("index.html")
group_template = template_environment.get_template("group.html")

app = typer.Typer()
#cutoff_date = datetime(2019, 1, 1, tzinfo=timezone.utc)


debug_enabled = False  # Set to True to enable debug output
def debug(text: str):
    if debug_enabled:
        print(f"[DEBUG] {text}")

class OutputFormat(Enum):
    json = "json"
    html = "html"

class ImageFormat(Enum):
    webp = "webp"
    png = "png"


async def get_user(
        id: int
):
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://users.roblox.com/v1/users/{id}"
        ) as response:
            return await response.json()
        




def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]



async def get_group_icons(
        session: aiohttp.ClientSession,
        group_ids: List[int],
        path1: Path,
        path2: Path,
        image_format: ImageFormat,  # webp, png
        rest_delay: float = 0.8,
        auth: str = None,
        size: str = "150x150",  # 150x150, 420x420
):

    if len(group_ids) == 0: return


    path1 = Path(path1)
    if not path1.is_dir() or not path1.exists():
        path1.mkdir(parents=True)


    # Filter out IDs we already have
    filtered_group_ids = [
        gid for gid in group_ids if not (path1 / f"{gid}.{image_format.value}").is_file()
    ]
    for group_id_chunk in chunks(filtered_group_ids, 100):   # Splits group_ids into chunks of 100
        await asyncio.sleep(rest_delay)
        delay = rest_delay
        attempts_left = 10

        primaryurl = f"https://thumbnails.roblox.com/v1/batch"
        backupurl = f"https://thumbnails.roproxy.com/v1/batch"
        url = primaryurl
        cookiestouse = {".ROBLOSECURITY": auth} if auth else {}

        while attempts_left > 0:

            payload = [
                        {
                            "type": "GroupIcon",
                            "targetId": group_id,
                            "format": image_format.value,
                            "size": size
                        }
                        for group_id in group_ids
                    ]
            
            async with session.post(url=url,json=payload, raise_for_status=False, cookies=cookiestouse) as response:
                
                if response.status == 429:
                    if url == primaryurl:
                        print(f"Rate limiteda. Retrying with proxy API in {delay} seconds...")
                        await asyncio.sleep(delay)
                        url = backupurl
                        cookiestouse = {}
                        delay *= 3
                        attempts_left -= 1
                    else:
                        print(f"Rate limitedb. Retrying with main API in {delay} seconds...")
                        await asyncio.sleep(delay)
                        url = primaryurl
                        cookiestouse = {".ROBLOSECURITY": auth} if auth else {}
                        delay *= 3 
                        attempts_left -= 1
                    continue

                elif response.status != 200:
                    typer.echo(f"Failed to get some group icons. Status code: {response.status}. Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                    delay *= 3
                    attempts_left -= 5
                    continue

                data = (await response.json())["data"]
                for item in data:
                    image_url = item["imageUrl"]
                    group_id = item["targetId"]
                    file_path = path1 / f"{group_id}.{image_format.value}"
                    
                    delay1 = rest_delay
                    attempts_left1 = 10
                    while attempts_left1 > 0:
                        async with session.get(image_url, raise_for_status=False) as img_resp:

                            if img_resp.status == 429:
                                print(f"Rate limited. Retrying in {delay1} seconds...")
                                await asyncio.sleep(delay1)
                                delay1 *= 2
                                attempts_left1 -= 1
                                continue

                            elif img_resp.status != 200:
                                typer.echo(f"Failed to get some group icons. Status code: {img_resp.status}. Retrying in {delay1} seconds...")
                                await asyncio.sleep(delay1)
                                delay1 *= 2 
                                attempts_left1 -= 1
                                continue

                            async with aiofiles.open(file_path, "wb") as f:
                                await f.write(await img_resp.read())
                            break

                    if attempts_left1 == 0:
                        typer.echo(f"Failed to get a group icon after multiple attempts. Skipping.")       
                break  # Exit the retry loop if successful

        if attempts_left == 0:
            typer.echo(f"Failed to get some group icons after multiple attempts. Skipping.")            


    path2 = Path(path2)
    if not path2.is_dir() or not path2.exists():
        path2.mkdir(parents=True)

    # Copy the files from path1 to path2 that were in group_ids
    for group_id in group_ids:
        src_file = path1 / f"{group_id}.{image_format.value}"
        dest_file = path2 / f"{group_id}.{image_format.value}"
        if src_file.is_file():
            shutil.copy(src_file, dest_file)


async def get_headshots(
        session: aiohttp.ClientSession,
        user_ids: List[int],
        path1: Path,
        path2: Path,
        image_format: ImageFormat,
        rest_delay: float = 0.8,
        auth: str = None,
        size: str = "48x48"
):
    user_ids = list(set(user_ids))  # Remove duplicates
    if len(user_ids) == 0: return

    # Check if path exists, if not create it
    path1 = Path(path1)
    if not path1.is_dir() or not path1.exists():
        debug(f"Creating directory: {path1}")
        path1.mkdir(parents=True)


    # Filter out IDs we already have
    filtered_user_ids = [
        uid for uid in user_ids if not (path1 / f"{uid}.{image_format.value}").is_file()
    ]
    for user_id_chunk in chunks(filtered_user_ids, 100):   # Splits user_ids into chunks of 100
        await asyncio.sleep(rest_delay)
        delay = rest_delay
        attempts_left = 10

        primaryurl = f"https://thumbnails.roblox.com/v1/users/avatar-headshot"
        backupurl = f"https://thumbnails.roproxy.com/v1/users/avatar-headshot"
        url = primaryurl
        cookiestouse = {".ROBLOSECURITY": auth} if auth else {}

        while attempts_left > 0:
            async with session.get(
                    url=url,
                    params={
                        "userIds": user_id_chunk,
                        "size": size,
                        "format": image_format.value,
                        "isCircular": "false"
                    },
                    raise_for_status=False,
                    cookies=cookiestouse
            ) as response:
                debug(f"Requested {url}. Status: {response.status}")

                if response.status == 429:
                    if url == primaryurl:
                        print(f"Rate limited. Retrying with proxy API in {delay} seconds...")
                        await asyncio.sleep(delay)
                        url = backupurl
                        cookiestouse = {}
                        delay *= 3
                        attempts_left -= 1
                    else:
                        print(f"Rate limited. Retrying with main API in {delay} seconds...")
                        await asyncio.sleep(delay)
                        url = primaryurl
                        cookiestouse = {".ROBLOSECURITY": auth} if auth else {}
                        delay *= 3 
                        attempts_left -= 1
                    continue

                elif response.status != 200:
                    print(f"Failed to get some headshots. Status code: {response.status}. Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                    delay *= 3
                    attempts_left -= 5
                    continue

                debug("got some batch headshot data")

                data = (await response.json())["data"]
                for item in data:
                    image_url = item["imageUrl"]
                    user_id = item["targetId"]
                    file_path = path1 / f"{user_id}.{image_format.value}"
                    
                    delay1 = rest_delay
                    attempts_left1 = 10
                    while attempts_left1 > 0:
                        async with session.get(image_url, raise_for_status=False) as img_resp:

                            if img_resp.status == 429:
                                print(f"Rate limited. Retrying in {delay1} seconds...")
                                await asyncio.sleep(delay1)
                                delay1 *= 2
                                attempts_left1 -= 1
                                continue

                            elif img_resp.status != 200:
                                typer.echo(f"Failed to get some headshots. Status code: {img_resp.status}. Retrying in {delay1} seconds...")
                                await asyncio.sleep(delay1)
                                delay1 *= 2 
                                attempts_left1 -= 5
                                continue

                            async with aiofiles.open(file_path, "wb") as f:
                                await f.write(await img_resp.read())
                            break

                    if attempts_left1 == 0:
                        typer.echo(f"Failed to get a headshot after multiple attempts. Skipping.")       
                break  # Exit the retry loop if successful

        if attempts_left == 0:
            typer.echo(f"Failed to get some headshots after multiple attempts. Skipping.")            

    path2 = Path(path2)
    if not path2.is_dir() or not path2.exists():
        path2.mkdir(parents=True)

    for user_id in user_ids:
        src_file = path1 / f"{user_id}.{image_format.value}"
        dest_file = path2 / f"{user_id}.{image_format.value}"
        if src_file.is_file():
            shutil.copy(src_file, dest_file)



async def get_groups(
        user_id: int
):
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://groups.roblox.com/v1/users/{user_id}/groups/roles"
        ) as response:
            return await response.json()
    """
    Example response:
    {
        "data": [
            {
                "group": {
                    "id": 0,
                    "name": "",
                    "description": "",
                    "owner": {
                        "hasVerifiedBadge": false,
                        "userId": 0,
                        "username": "",
                        "displayName": ""
                    },
                    "shout": null,
                    "memberCount": 0,
                    "isBuildersClubOnly": false,    # why is this still a thing 💀
                    "publicEntryAllowed": true,
                    "hasVerifiedBadge": true
                },
                "role": {
                    "id": 0,
                    "name": "Member",
                    "rank": 1
                }
            }
        ]
    }
    """


async def get_custom_group_info(
        id: int
):
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://groups.roblox.com/v1/groups/{id}"
        ) as response:
            return await response.json()
        

async def get_raw_posts(
        session: aiohttp.ClientSession,
        group_id: int,
        cursor: str = "",
        page_size: int = 100,
        rest_delay: float = 0.8,
        auth: str = None,
):
    debug(f"Waiting {rest_delay} seconds...")

    await asyncio.sleep(rest_delay)

    delay = rest_delay
    attempts_left = 10
    data = "error"
    
    primaryurl = f"https://groups.roblox.com/v2/groups/{group_id}/wall/posts?cursor={cursor}&limit={page_size}&sortOrder=Desc"
    backupurl = f"https://groups.roproxy.com/v2/groups/{group_id}/wall/posts?cursor={cursor}&limit={page_size}&sortOrder=Desc"
    url = primaryurl
    cookiestouse = {".ROBLOSECURITY": auth} if auth else {}
    while attempts_left > 0:
        async with session.get(
                url,
                raise_for_status=False,
                cookies=cookiestouse,
        ) as response:
            
            debug(f"Requested {url}. Status: {response.status}")
            
            if response.status == 429:
                    if url == primaryurl:
                        print(f"Rate limited. Retrying with proxy API in {delay} seconds...")
                        await asyncio.sleep(delay)
                        url = backupurl
                        cookiestouse = {} # I don't trust these proxies idk
                        delay *= 3  # exponential backoff
                        attempts_left -= 1
                    else:
                        print(f"Rate limited. Retrying with main API in {delay} seconds...")
                        await asyncio.sleep(delay)
                        url = primaryurl  # Reset to primary URL for next attempt
                        cookiestouse = {".ROBLOSECURITY": auth} if auth else {}
                        delay *= 3
                        attempts_left -= 1
                    
                    continue

            elif response.status != 200:
                typer.echo(f"Failed to get wall posts. Status code: {response.status}. Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
                delay *= 3
                attempts_left -= 1
                continue

            debug("successfully got some data")
            data = await response.json()
            break

    return data
    


async def get_group_walls(
    session: aiohttp.ClientSession,
    groups: List[dict],
    auth: str,
    first_n,
    rest_delay: float = 0.8
):

    finaldata = {}


    while first_n == None:
            raw = await async_confirm("Would you like to only store the oldest x wall posts for the selected groups? (Choose N for all wall posts)", default=False)
            if raw == None:
                typer.echo("Cancelled. Exiting...")
                raise typer.Exit(code=1)
            if raw == True:
                while first_n == None or str(first_n).isdigit() == False:
                    first_n = input(f"How many posts to save? (oldest to newest) ").strip()
                    if first_n.isdigit():
                        first_n = int(first_n)
            else:
                first_n = 0



    for group in groups:
        group_id = group["group"]["id"]
        typer.echo(f"Getting wall messages for group '{group['group']['name']}' (ID: {group_id})...")

        messages = []

        page_size = 100  # 10, 25, 50, 100

        raw_messages = await get_raw_posts(
            session=session,
            group_id=group_id,
            cursor="",
            page_size=page_size,
            rest_delay=rest_delay,
            auth=auth
        )
        debug("Got first batch of messages.")


        messages.extend(raw_messages["data"])


        if raw_messages != "error" and raw_messages["nextPageCursor"] is not None:
            while raw_messages != "error" and raw_messages["nextPageCursor"]:
                raw_messages = await get_raw_posts(
                    session=session,
                    group_id=group_id,
                    cursor=raw_messages["nextPageCursor"],
                    page_size=page_size,
                    rest_delay=rest_delay
                )
                messages.extend(raw_messages["data"])


        

        
        if first_n > 0:
            messages = messages[-first_n:]  # Discard up to the oldest n messages

        if raw_messages == "error":
            typer.echo(f"Failed to get some wall posts for group '{group['group']['name']}'.")


        for group in groups: 
            if group["group"]["shout"] == None:
                groupinfo = await get_custom_group_info(id=group["group"]["id"])     # After adding custom group ID system, i realised having group shout in the data is kinda cool but maybe a little unnecessary
                group["group"]["shout"] = groupinfo["shout"] if "shout" in groupinfo else None
                debug(group["group"]["shout"])


        data = {
            "name": group["group"]["name"],
            "id": group_id,
            "description": group["group"]["description"],
            "owner": {
                "userId": group["group"]["owner"]["userId"],
                "username": group["group"]["owner"]["username"],
                "displayName": group["group"]["owner"]["displayName"],
                "hasVerifiedBadge": group["group"]["owner"].get("hasVerifiedBadge", False)
            },
            "memberCount": group["group"]["memberCount"],
            "hasVerifiedBadge": group["group"].get("hasVerifiedBadge", False),
            "shout": group["group"].get("shout", None),
            "wall": messages
        }
        finaldata[group_id] = data
        #typer.echo(f"Found {len(messages)} messages in group '{group['group']['name']}' (ID: {group_id})")


    wrapped_data = {
        "archived_on": datetime.now(timezone.utc).isoformat(),
        "data": finaldata
    }
    """
    WrappedData structure:

    {
        "archived_on": "2025-05-25T17:00:00Z",
        "data": {
            "groupid": {
                "name": "group name",
                "id": groupid,
                "description": "",
                "owner": {
                    "userId": 0,
                    "username": "",
                    "displayName": "",
                    "hasVerifiedBadge": false
                },
                "memberCount": 0,
                "hasVerifiedBadge": false,
                "shout": null,
                "wall": [
                    {
                        "id": 0,
                        "poster": {
                            "user": {
                                "hasVerifiedBadge": false,
                                "userId": 0,
                                "username": "",
                                "displayName": ""
                            },
                            "role": {
                                "id": 0,
                                "name": "Owner",
                                "rank": 255
                            }
                        },
                        "body": "message body",
                        "created": "2023-12-29T09:37:52.323Z",
                        "updated": "2023-12-29T09:37:52.323Z"
                    }
                ]
            }
        }
    }
    """
    return wrapped_data


def prompt_group_selection(groups, user_id):

    owned_groups = [
            g for g in groups
            if g["group"].get("owner", {}).get("userId") == int(user_id)
    ]
    show_only_owned = False
    if len(owned_groups) > 0:
        show_only_owned = questionary.confirm("Only show groups you own?").ask()

    if show_only_owned == None:
        typer.echo("Cancelled. Exiting...")
        raise typer.Exit(code=1)
    
    if show_only_owned:
        groups = owned_groups

    choices = [
        questionary.Choice(
            title=f"{item['group']['name']}",
            value=item
        )
        for item in groups
    ]

    selected = questionary.checkbox(
        "Select groups:",
        choices=choices
    ).ask()

    if selected == None:
        typer.echo("Cancelled. Exiting...")
        raise typer.Exit(code=1)

    return selected



def confirm_sync(prompt: str, default: bool = True) -> bool | None:
    return questionary.confirm(prompt, default=default).ask()

async def async_confirm(prompt: str, default: bool = True) -> bool | None:
    return await asyncio.to_thread(confirm_sync, prompt, default)


async def htmlCreation(
    session: aiohttp.ClientSession,
    data: dict,
    archive_date: datetime,
    path: Path,
    rest_delay: int,
    download_headshots: bool,
    download_group_icons: bool,
    image_format: ImageFormat,
    auth: str
):
    (path / "assets").mkdir(parents=True, exist_ok=True)
    for a_path in {
        html_assets_path / "style.css",
        html_assets_path / "favicon.ico",
        html_assets_path / "favicon.svg",
        html_assets_path / "placeholder.webp",
        html_assets_path / "verified-icon.png",
        html_assets_path / "font" / "BuilderSans-Regular-400.otf",

    }:
        b_path = path / "assets" / a_path.name
        shutil.copy(a_path, b_path)


    placeholder_path = path / "assets" / "placeholder.webp"
    
    if not rest_delay: rest_delay = 0.8  # Probably a good starting value idk


    # On second thought, i was actually accidently spamming api, so this bit probably isnt even needed, but pass it as an argument if you really want
    """  
    while auth == None: # Only really sees this if we chose to use existing JSON file
            raw = await async_confirm("Would you like to provide your .ROBLOSECURITY cookie? This may reduce rate limits if fetching images/icons.", default=False)
            if raw == True:
                while auth == None or auth.startswith("_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|_") == False:
                    auth = getpass("Enter your .ROBLOSECURITY: ").strip()

                session.cookie_jar.update_cookies({
                    ".ROBLOSECURITY": auth
                })

            else:
                auth = False
    """
    if auth == None: auth = False

    while download_group_icons == None:
        raw = await async_confirm("Would you like to download group icons?")
        if raw == None:
            typer.echo("Cancelled. Exiting...")
            raise typer.Exit(code=1)
        if raw == True: download_group_icons = True
        else: download_group_icons = False

    if download_group_icons:
        await get_group_icons(
            session=session,
            group_ids = list(data["data"].keys()),
            path1=cached_images_path / "group_icons",
            path2=path / "group_icons",
            image_format = image_format,
            rest_delay = rest_delay,
            auth=auth,
        )


    while download_headshots == None:
        raw = await async_confirm("Would you like to download user headshot photos?")
        if raw == None:
            typer.echo("Cancelled. Exiting...")
            raise typer.Exit(code=1)
        if raw == True: download_headshots = True
        else: download_headshots = False

                    
    if download_headshots:
        user_ids = list({
            message["poster"]["user"]["userId"]
            for group in data["data"].values()
            for message in group["wall"]
            if message.get("poster") and message["poster"].get("user")
        })
        await get_headshots(
            session=session,
            user_ids = user_ids,
            path1=cached_images_path / "headshots",
            path2=path / "headshots",
            image_format = image_format,
            rest_delay = rest_delay,
            auth=auth,
        )

    async with aiofiles.open(
        file=path / "index.html",
        mode="w",
        encoding="utf-8"
    ) as index_file:
        await index_file.write(await index_template.render_async(
            groups=[
                {
                    "path": f"groups/{group_id}.html",
                    "name": group["name"],
                    "thumbnail": f"group_icons/{group_id}.{image_format.value}" if Path(path / "group_icons" / f"{group_id}.{image_format.value}").is_file() else f"assets/placeholder.webp",
                    "verified": group["hasVerifiedBadge"],
                    "owner": {
                        "name": group["owner"]["username"] if group.get("owner") and group["owner"].get("username") else "???",
                        "display_name": group["owner"]["displayName"] if group.get("owner") and group["owner"].get("displayName") else "???",
                        "verified": group["owner"]["hasVerifiedBadge"] if group.get("owner") and group["owner"].get("hasVerifiedBadge") else False
                    }
                } for group_id, group in data["data"].items()
            ],
            archive_date=archive_date.strftime("%d/%m/%Y, %H:%M:%S %Z")
        ))

    (path / "groups").mkdir(parents=True, exist_ok=True)
    for group_id, group in data["data"].items():
        group_path = path / "groups" / f"{group_id}.html"

        async with aiofiles.open(
            file=group_path,
            mode="w",
            encoding="utf-8"
        ) as group_file:
                        
            messagestorender = []
            for message in group["wall"]:
                poster = (message.get("poster") or {}).get("user", {})
                role = (message.get("poster") or {}).get("role", {})
                created_dt = None
                if "created" in message:
                    try:
                        created_dt = datetime.fromisoformat(message["created"].replace("Z", "+00:00"))
                    except ValueError:
                        pass

                messagestorender.append({
                    "author": {
                        "verified": chr(0xE000) if poster.get("hasVerifiedBadge") else "",
                        "name": poster.get("username", "???"),
                        "display_name": poster.get("displayName", "???"),
                        "profile_url": f"https://www.roblox.com/users/{poster.get('userId')}/profile" if "userId" in poster else "",
                        "headshot": f"../headshots/{poster.get('userId')}.{image_format.value}" if poster.get("userId") and Path(path / "headshots" / f"{poster.get('userId')}.{image_format.value}").is_file() else f"../assets/placeholder.webp",
                        "role": role.get("name", "???")
                    },
                    "body": message.get("body", ""),
                    "created_date": f"{created_dt.strftime('%b')} {created_dt.day}, {created_dt.year}" if created_dt else "???",
                    "created_time": created_dt.strftime("%I:%M %p") if created_dt else "???"
                })

            shout_created_dt = None
            if group.get("shout") and "updated" in group["shout"]:
                try:
                    shout_created_dt = datetime.fromisoformat(group["shout"]["updated"].replace("Z", "+00:00"))
                except ValueError:
                    pass

            await group_file.write(await group_template.render_async(
                group={
                    "name": group["name"],
                    "thumbnail": f"../group_icons/{group_id}.{image_format.value}" if Path(path / "group_icons" / f"{group_id}.{image_format.value}").is_file() else placeholder_path,
                    "verified": chr(0xE000) if group["hasVerifiedBadge"] else "",
                    "description": group["description"],
                    "members": group["memberCount"],
                    "group_url": f"https://www.roblox.com/communities/{group.get('id')}/roblox-group-wall-archiver" if group.get('id') else "",
                    "owner": {
                        "name": group["owner"]["username"] if group.get("owner") and group["owner"].get("username") else "???",
                        "display_name": group["owner"]["displayName"] if group.get("owner") and group["owner"].get("displayName") else "???",
                        "verified": chr(0xE000) if group.get("owner") and group["owner"].get("hasVerifiedBadge") and group["owner"]["hasVerifiedBadge"] else "",
                        "profile_url": f"https://www.roblox.com/users/{group["owner"].get('userId')}/profile" if group.get('owner') and group["owner"].get('userId') else "",
                    },
                    "shout": {
                        "body": group["shout"]["body"] if group.get("shout") and group["shout"].get("body") else None,
                        "poster": {
                            "name": group["shout"]["poster"]["username"] if group.get("shout") and group["shout"].get("poster") and group["shout"]["poster"].get("username") else "???",
                            "display_name": group["shout"]["poster"]["displayName"] if group.get("shout") and group["shout"].get("poster") and group["shout"]["poster"].get("displayName") else "???",
                            "verified": chr(0xE000) if group.get("shout") and group["shout"].get("poster") and group["shout"]["poster"].get("hasVerifiedBadge") else "",
                            "profile_url": f"https://www.roblox.com/users/{group["shout"]["poster"].get('userId')}/profile" if group.get('shout') and group["shout"].get('poster') and group["shout"]["poster"].get('userId')  else "",
                            "headshot": f"../headshots/{group["shout"]["poster"].get('userId')}.{image_format.value}" if group.get("shout") and group["shout"].get("poster") and group["shout"]["poster"].get("userId") and Path(path / "headshots" / f"{group["shout"]["poster"].get('userId')}.{image_format.value}").is_file() else f"../assets/placeholder.webp",
                        },
                        "created_date": f"{shout_created_dt.strftime('%b')} {shout_created_dt.day}, {shout_created_dt.year}" if shout_created_dt else "???",
                        "created_time": shout_created_dt.strftime("%I:%M %p") if shout_created_dt else "???"
                    }
                },
                messages = messagestorender,
                archive_date=archive_date.strftime("%d/%m/%Y, %H:%M:%S %Z")
            ))

async def htmlCreationSync(
    data: dict,
    archive_date: datetime,
    path: Path,
    rest_delay: int,
    download_headshots: bool,
    download_group_icons: bool,
    image_format: ImageFormat,
    auth: str
):
    async with aiohttp.ClientSession(raise_for_status=True) as session:
        await htmlCreation(session, data, archive_date, path, rest_delay, download_headshots, download_group_icons, image_format, auth)
    

async def main2(
    start_time: float,
    path: Path,
    output_format: OutputFormat,
    rest_delay: int,
    groups: List[dict],
    hide_deleted_users: bool,
    download_headshots: bool,
    download_group_icons: bool,
    image_format: ImageFormat,
    auth: str,
    first_n: int,
    add_to_existing: bool,

):
    async with aiohttp.ClientSession(
        raise_for_status=True
    ) as session:
        
        
        archive_date = datetime.now(timezone.utc)

        """
        while auth == None:
            raw = await async_confirm("Would you like to provide your .ROBLOSECURITY cookie? This may reduce rate limits.", default=False)
            if raw == True:
                while auth == None or auth.startswith("_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|_") == False:
                    auth = getpass("Enter your .ROBLOSECURITY: ").strip()

                session.cookie_jar.update_cookies({
                    ".ROBLOSECURITY": auth
                })

            else:
                auth = False
        """
        if auth == None: auth = False

        typer.echo(f"Saving group walls. This may take a while depending on the size of group walls...")

        data = await get_group_walls(session, groups, auth, first_n)


        has_null_posters = False
        for group in data["data"].values():
            for message in group["wall"]:
                if message.get("poster") is None:
                    has_null_posters = True
                    break
            if has_null_posters:
                break
        if has_null_posters:
            while hide_deleted_users == None:
                raw = await async_confirm("Would you like to hide messages from deleted users? These messages aren't visible on Roblox.")
                if raw == None:
                    typer.echo("Cancelled. Exiting...")
                    raise typer.Exit(code=1)
                if raw == True: hide_deleted_users = True
                else: hide_deleted_users = False


        if hide_deleted_users:
            for group in data["data"].values():
                group["wall"] = [
                message for message in group["wall"]
                if message.get("poster") is not None
            ]

        
        # Get existing data from json file and add our new data to it if add_to_existing is True
        if add_to_existing:
            existing_data_path = path / "archived-data.json"
            if existing_data_path.is_file():
                async with aiofiles.open(existing_data_path, mode="r", encoding="utf-8") as file:
                    existing_data = json.loads(await file.read())
                if "data" in existing_data and "archived_on" in existing_data:
                    combined = existing_data["data"].copy()
                    combined.update(data["data"])
                    data["data"] = combined
                else:
                    typer.echo("Invalid existing JSON file. Creating a new one.")
            else:
                typer.echo("No existing JSON file found. Creating a new one.")


        async with aiofiles.open(
            file= path / "archived-data.json",
            mode="w",
            encoding="utf-8"
        ) as file:
            await file.write(json.dumps(data, indent=2))

        while output_format == None:
            raw = await async_confirm("Data has been saved to a JSON file. Would you like to also save data as HTML?")
            if raw == None:
                typer.echo("Cancelled. Exiting...")
                raise typer.Exit(code=1)
            if raw == True: output_format = OutputFormat.html 
            else: output_format = OutputFormat.json 
               
        if output_format == OutputFormat.html:
            
            await htmlCreation(session, data, archive_date, path, rest_delay, download_headshots, download_group_icons, image_format, auth)
                

        end_time = timer()
        typer.echo(f"Nice! Completed in {end_time - start_time:.01f} seconds.")


def main(
        path: Path,
        output_format: OutputFormat,
        user_id: int,
        rest_delay: int,
        hide_deleted_users: bool,
        download_headshots: bool,
        download_group_icons: bool,
        image_format: ImageFormat,
        use_existing_json: bool,
        input_json: Path,
        auth: str,
        first_n: int,
        custom_group_ids: str,
        add_to_existing: bool
):

    
    while use_existing_json == None:
        raw = questionary.select(
            "Choose a mode",
            choices=["Archive and save group walls 💎", "Create HTML from existing JSON file"],
        ).ask()
        if raw == None:
            typer.echo("Cancelled. Exiting...")
            raise typer.Exit(code=1)
        
        if raw == "Archive and save group walls 💎": use_existing_json = False
        else: use_existing_json = True

    if use_existing_json:
        while input_json == None:
            while True:
                raw = input("Enter path to existing JSON file: ").strip()
                if Path(raw).is_file():
                    input_json = Path(raw)
                    break
                print("File doesn't exist. Please enter a valid path.")

        print("Using existing JSON file for HTML creation...")


        with open(input_json, "r", encoding="utf-8") as file:
            data = json.load(file)
            if "data" not in data or "archived_on" not in data:
                raise ValueError("Invalid JSON file. Expected 'data' and 'archived_on' fields.")
            
        if not path:
            while True:
                raw = input("Enter new directory to save HTML group wall data to (e.g output): ").strip()
                if not Path(raw).is_dir():
                    os.mkdir(raw)
                    path = Path(raw)
                    break
                print("Directory already exists. Please enter a valid directory path.")
        start_time = timer()

        archive_date = parse(data["archived_on"])

        asyncio.run(htmlCreationSync(data, archive_date, path, rest_delay, download_headshots, download_group_icons, image_format, auth))

        end_time = timer()
        typer.echo(f"Nice! Completed in {end_time - start_time:.01f} seconds.")
        exit(0)




    


    while custom_group_ids == None:
        raw = questionary.confirm("Would you like to archive custom group IDs?", default=False).ask()
        if raw == None:
            typer.echo("Cancelled. Exiting...")
            raise typer.Exit(code=1)
        if raw == True:
            raw2 = None
            while raw2 == None or not all(id.strip().isdigit() for id in raw2.split(",")):
                raw2 = input("Enter custom group IDs, separated by commas: ").strip()
                if raw2:
                    custom_group_ids = list(dict.fromkeys(   # Should supposedly strip input, remove dupes, convert to ints, and play fortnite or something idk
                        int(id.strip()) for id in raw2.split(",") if id.strip().isdigit()
                    ))
                else:
                    typer.echo("No custom group IDs provided. Please enter valid IDs.")
                    raw2 = None
            typer.echo(f"Archiving {len(custom_group_ids)} custom group IDs: {custom_group_ids}")
            break
        else:
            custom_group_ids = False

    
    groupstouse = []

    if custom_group_ids != None and custom_group_ids != False and len(custom_group_ids) > 0:

        for group_id in custom_group_ids:
            groupdata = asyncio.run(get_custom_group_info(id=group_id))
            groupdata = {"group": groupdata}
            groupstouse.append(groupdata)

    else:
        if not user_id:
            user_id = input("Enter your Roblox UserID: ").strip()

        user = asyncio.run(get_user(
            id=int(user_id)
        ))
        user_name = user["name"]
        user_display_name = user["displayName"]

        if user_name == user_display_name:
            name_string = user_name
        else:
            name_string = f"{user_display_name} (@{user_name})"

        typer.echo(f"Checking groups for {name_string}...")


        # Get groups
        raw_groups = asyncio.run(get_groups(
            user_id=user_id
        ))
        groups = raw_groups["data"]
        debug(f"Found {len(groups)} groups")


        selected = prompt_group_selection(groups, user_id)
        while selected == []:
            typer.echo("No groups selected. Please select at least one group.")
            selected = prompt_group_selection(groups, user_id)
        
        groupstouse = selected


    while add_to_existing == None:
        raw = questionary.select(
            "What would you like to do?",
            choices=["Create new file", "Add to existing file"]
            ).ask()
        if raw == None:
            typer.echo("Cancelled. Exiting...")
            raise typer.Exit(code=1)
        if raw == "Create new file":
            add_to_existing = False
        else: add_to_existing = True


    if not path:
        while True:
            txt = "Enter new directory to save group wall data to (e.g output): " if add_to_existing == False else "Enter directory where existing file is (file must be named 'archived-data.json'): "
            raw = input(txt).strip()
            if add_to_existing == False:
                if not Path(raw).is_dir():
                    os.mkdir(raw)
                    path = Path(raw)
                    break
                else:
                    print("Directory already exists. Please enter a valid directory path.")
            else:
                path_obj = Path(raw)
                if path_obj.is_dir() and (path_obj / "archived-data.json").is_file():
                    path = path_obj
                    debug(f"Using existing file to save data to.")
                    break
                else:
                    print("Directory doesn't contain existing 'archived-data.json' file. Please enter a valid directory path.")
            


    start_time = timer()

    asyncio.run(main2(
        start_time=start_time,
        path=path,
        output_format=output_format,
        rest_delay=rest_delay,
        groups=groupstouse,
        hide_deleted_users=hide_deleted_users,
        download_headshots=download_headshots,
        download_group_icons=download_group_icons,
        image_format=image_format,
        auth=auth,
        first_n=first_n,
        add_to_existing=add_to_existing
    ))

    
def hidden_default_option(*args, **kwargs):  # cba to do it individually on all of the options, and we dont want it showing None as default because who cares
    kwargs["show_default"] = False
    return typer.Option(*args, **kwargs)


@app.command()
def root(
        path: Path = hidden_default_option(
            default=None,
            help="The directory path to save archived data to. Must be non-existent.",
            resolve_path=True
        ),
        output_format: OutputFormat = hidden_default_option(
            default=None,
            help="The output format to use. 'html' for HTML and JSON, or 'json' for JSON only."
        ),
        user_id: int = hidden_default_option(
            default=None,
            help="Your Roblox UserID."
        ),
        rest_delay: float = hidden_default_option(
            default=None,
            help="How long to wait between requests. Increase this if you encounter ratelimit errors."
        ),
        hide_deleted_users: bool = hidden_default_option(
            default=None,
            help="Whether or not to save group wall messages from deleted users (not visible on Roblox).",
        ),
        download_headshots: bool = hidden_default_option(
            default=None,
            help="Whether or not to download user headshot photos."
        ),
        download_group_icons: bool = hidden_default_option(
            default=None,
            help="Whether or not to download group icons."
        ),
        image_format: ImageFormat = hidden_default_option(
            default="webp",
            help="The image format to use. 'webp' or 'png'."
        ),
        use_existing_json: bool = hidden_default_option(
            default=None,
            help="Whether or not to skip archiving, and use an existing json file for HTML creation."
        ),
        input_json: Path = hidden_default_option(
            default=None,
            help="Where to find the existing JSON file to use for HTML creation.",
            resolve_path=True
        ),
        auth: str = hidden_default_option(
            default=None,
            help="Provide your .ROBLOSECURITY to potentially reduce rate limits.",
        ),
        debug_flag: bool = hidden_default_option(
            False,
            "--debug",
            help="Prints some nerdy stuff to the console.",
        ),
        first_n: int = hidden_default_option(
            default=None,
            help="Only save the oldest n wall posts.",
        ),
        custom_group_ids: str = hidden_default_option(
            default=None,
            help="Custom group IDs to archive, separated by commas.",
        ),
        add_to_existing: bool = hidden_default_option(
            default=None,
            help="Whether or not to add to an existing file instead of creating a new one.",
        ),
        
):
    
    os.system('cls' if os.name == 'nt' else 'clear')

    global debug_enabled
    if debug_flag: debug_enabled = True

    if use_existing_json == True:
        assert input_json.is_file() and input_json.exists(), "Creating HTML from existing JSON requires a valid JSON file."

    main(path,output_format,user_id,rest_delay,hide_deleted_users,download_headshots,download_group_icons,image_format,use_existing_json, input_json, auth, first_n, custom_group_ids, add_to_existing)


if __name__ == '__main__':
    try:
        app()
    except KeyboardInterrupt:
        print("\nCancelled by user. Exiting...")
        raise typer.Exit(code=0)