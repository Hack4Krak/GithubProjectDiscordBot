# <picture> <source srcset="https://raw.githubusercontent.com/Hack4Krak/Hack4KrakSite/refs/heads/master/.github/assets/banner-light.png" media="(prefers-color-scheme: dark)"/> <img src="https://raw.githubusercontent.com/Hack4Krak/Hack4KrakSite/refs/heads/master/.github/assets/banner-dark.png" /> </picture>

## GitHub Projects Discord Bot

This repository provides and integration between [Discord](https://discord.com/) and [GitHub Projects](https://https://docs.github.com/en/issues/planning-and-tracking-with-projects/learning-about-projects/about-projects),
allowing users to discuss GitHub Projects directly from Discord. Whenever a new issue, pull request or draft issue is added
to the project, bot creates a new thread in the specified Discord channel. Every update to the project item is then communicated
in the thread, allowing users to stay up-to-date with the latest changes.

## 🚜 Development

This repository contains two main components:
- [`server.py`](/src/server.py): listens for GitHub webhook events and processes them
- [`bot.py`](/src/bot.py): a Discord bot that creates threads and posts updates

For local development, you can copy the `.env.example` file to `.env` and fill in the first three environment variables.
Then run the following command to install dependencies:

```bash
uv sync
```

To run the server and bot locally, you can use the following command:

```bashbash
uv run start-app
```

## 🚀 Deployment

For deployment follow these steps:
- set all environment variables accordingly,
- update your `github_usernames_to_discord_id_mapping.json`,
- set up a webhook in your GitHub repository to point to your server's `/webhook_endpoint` endpoint,
- use Dockerfile to build the image.

## ⚒️ How it works

1. GitHub sends a webhook event to the server when an issue, pull request or draft issue is added or updated in the project.
2. The server processes the event and extracts relevant information, such as the issue title, description
3. The server updates shared state with the new information which is then used by the bot to post updates.
4. The bot creates a new thread in the specified Discord channel for new issues, pull requests or draft issues.
5. The bot posts updates in the thread whenever the issue, pull request or draft issue is updated.
6. The bot uses the `github_usernames_to_discord_id_mapping.json` file to map GitHub usernames to Discord user IDs,
   allowing it to mention users in the thread.
