# Grok3 Deep Search Article Generation and Notion Upload System

## Introduction
This project implements a simple loop mission that utilizes the Grok3 deep search funciton to automatically generate high-quality articles and upload them to Notion. The system automates the process of content creation and publication, assisting users in building a rich content repository with minimal manual effort.

## Features
- **Deep Research:** Uses the Grok3 module to perform in-depth data mining and research.
- **Article Generation:** Automatically generates well-crafted articles based on the research results.
- **Notion Upload:** Seamlessly uploads the generated articles to a Notion database for easy management and review.

## Environment Setup
- **Python Environment:** Use the uv tool to install the required Python dependencies.
- **Node Environment:** Use pnpm to install Node dependencies. Make sure your Node environment is correctly set up.

## Configuration
This project requires a configuration file (.env) in the project root containing various API keys and endpoints. Create a .env file in the project root with the following keys:

- `NOTION_API_KEY`: Your Notion API key (e.g., <YOUR_NOTION_API_KEY>).
- `NOTION_DATABASE_ID`: The ID of your Notion database (e.g., <YOUR_NOTION_DATABASE_ID>).
- `OPENROUTER_API_KEY`: Your API key for the OpenRouter service (e.g., <YOUR_OPENROUTER_API_KEY>).
- `OPENROUTER_BASE_URL`: The base URL for the OpenRouter API (e.g., <YOUR_OPENROUTER_BASE_URL>).
- `SEEDREAM`: A seed string for Dream-related functionalities (e.g., <YOUR_SEEDREAM>).
- `DREAMINA`: The API endpoint for Dreamina image generation (e.g., <YOUR_DREAMINA_ENDPOINT>).
- `GROK_API_KEY`: Your API key for Grok (e.g., <YOUR_GROK_API_KEY>).
- `GROK3API`: The API endpoint for Grok3 (e.g., <YOUR_GROK3API_ENDPOINT>).
- `DAILY_TIME`: The scheduled time for the daily loop task (e.g., "17:19").
- `DISCORD_WEBHOOK_ID`: The Discord webhook identifier for notifications (e.g., <YOUR_DISCORD_WEBHOOK_ID>).

Make sure to replace the placeholder values with your actual credentials.

## Usage
1. **Install Dependencies:**
   - For Python, run: `uv install`
   - For Node, run: `pnpm install`
2. **Run the Project:**
   - Execute the entry point using the appropriate command, for example:
     - For Python: `python app.py`
     - For Node: `pnpm start`
3. **Loop Task:**
   - The project operates in a continuous loop. Each cycle performs data research, article generation, and Notion upload.
   - Detailed logs are maintained for every key step, enabling you to trace execution and troubleshoot issues efficiently.

## Logging
The system logs detailed information for every critical step (research, article generation, and upload) to facilitate debugging and issue identification.

## Cautions
- Avoid modifying or deleting essential code without proper backup.
- In case of issues, check the log outputs for detailed error messages and troubleshooting information.

## License
This project is licensed under the MIT License. Please refer to the LICENSE file for more details.

## Contact
For any questions or issues, please contact the project maintainer.
