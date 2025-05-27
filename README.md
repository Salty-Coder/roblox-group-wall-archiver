# roblox-group-wall-archiver

![Screenshot of notice about group walls being depreciated](/demo-images/depreciated-wall.png)

Roblox will soon be **deleting all existing group walls** in favour of the new Group Forums system. This tool allows you to **back up and preserve** group wall posts before they are permanently removed.

![A screenshot of an archived group wall](/demo-images/demo-img.png)

---

## Setup

1. **Download Python**: Install Python from the official site: [https://www.python.org/downloads/](https://www.python.org/downloads/)
2. **Clone the Repository**: Download or clone this project to your device.
3. **Install Dependencies**: Either open `Install-Dependencies.bat` or run:

   ```bash
   pip install -r requirements.txt
   ```

---

## Usage

To archive group walls, either:

* **Double-click** `Roblox-Group-Wall-Archiver.bat`, *or*
* Run the program manually with:

  ```bash
  py roblox-group-wall-archiver.py
  ```
  You may need to use **python** or **python3** instead of **py** depending on your device.

By default, you will be prompted to enter the required options interactively during runtime. However, you can skip these prompts by passing them as CLI flags (see below).

To view all available options and usage instructions, run:

```bash
py roblox-group-wall-archiver.py --help
```

♻️ If you frequently use the same options, you can edit the `Roblox-Group-Wall-Archiver.bat` file to include your preferred flags for quicker use in the future.

---

## JSON Archives

This tool generates a **JSON archive** containing group information and wall posts.

This format is **not very human-readable**, but it includes all the necessary data to later generate rich, browsable HTML pages. It contains author IDs, timestamps, post contents, and more.

---

## HTML Archives

Optionally, the tool can also generate a **visually rich HTML archive** that makes browsing your saved group wall posts easy. It displays user icons, timestamps, group icons, and structured formatting for clarity, in a layout similar to the Roblox website - all stored in a single, self contained, portable folder.

### Group List Page
![A screenshot of a list of saved groups](/demo-images/demo-img1.png)
### Group Page
![A screenshot of an archived group page](/demo-images/demo-img3.png)
---

### Image Storage Details

If you choose to download headshots and/or group icons, they are saved to:

- A **cache folder**, so the same images don’t need to be downloaded again in the future.
- The **archive folder**, so your archive remains fully self-contained and portable.

---


## Options and CLI Flags

You can pass options via the command line to skip interactive prompts:

| Option                   | Description                                                       |
| ------------------------ | ----------------------------------------------------------------  |
| `--use-existing-json`    | Skip fetching and use an existing JSON file                       |
| `--custom-group-ids`     | Comma-separated group IDs to archive manually                     |
| `--user-id`              | Your Roblox User ID (if not using custom group IDs)               |
| `--add-to-existing`      | Append new data to existing archive file instead of starting fresh|
| `--path`                 | Directory to save archived data to (must not already exist)       |
| `--output-format`        | Choose `html` (includes JSON) or `json` (JSON only)               |
| `--rest-delay`           | Delay (in seconds) between requests to avoid rate limits          |
| `--first-n`              | Limit to the oldest N wall posts                                  |
| `--hide-deleted-users`   | Skip saving posts from deleted Roblox users                       |
| `--download-headshots`   | Save headshot images of users                                     |
| `--download-group-icons` | Save group icons                                                  |
| `--image-format`         | Choose image format: `webp` (default) or `png`                    |
| `--input-json`           | Path to existing JSON file for HTML generation                    |
| `--auth`                 | Optionally provide `.ROBLOSECURITY` cookie to potentially reduce rate limits |
| `--debug`                | Show additional output for debugging                              |


> ⚠️ Most of these options will be asked interactively during runtime if you don't provide them as flags. However, using CLI flags allows you to skip prompts to speed up the process.

Boolean options can be disabled by prefixing them with `--no-`, e.g. `--no-download-group-icons`.

Example:

```bash
py roblox-group-wall-archiver.py --user-id 123456 --output-format html --no-download-headshots --download-group-icons --rest-delay 2
```

---

## Notes

* All data is stored locally; nothing is uploaded.
* You don't need to provide any Roblox credentials unless you want to (potentially) reduce the risk of rate limits.
* If you do provide `.ROBLOSECURITY`, treat it like a password. It is never logged or stored.

---

If you have questions or want to contribute, feel free to open an issue or submit a pull request!



### If this tool helped you, consider starring the repo ⭐ or sharing it with others who want to preserve their group history!


<br>

## Thanks

This project wouldn't be possible without the amazing work from [@jmkd3d](https://github.com/jmkd3v) on [rbx-pm-archiver](https://github.com/jmkd3v/rbx-pm-archiver), which I used as a starting point for this project.
