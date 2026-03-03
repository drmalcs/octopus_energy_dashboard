# ⚡️⚡️ Octopus Energy Dashboard for people signed up to the Agile Octopus tarrif in the UK

What?: A personal energy monitoring dashboard built in Python and Flask, running locally on my Mac in a web browser.
It connects to the [Octopus Energy REST API](https://developer.octopus.energy/rest/) to pull my half-hourly smart meter data and display it as interactive graphs in a web browser.
Why?:  I created this because I sweitched to Octopus' Agile tarrif and I wanted to see what typical peak energy prices were throughout the day and see if my usage was at the expensive times. The difference between cheap and expensive rates is more than 3 times eg I've seen 35p/kWh and 11p/kWh during the daytime. When people get home from school/work is always the expensive period: around 4PM to 7PM - around a 3x jump.

Is it "live"?: yes/no/kind of. It will ask for the latest available data but that's usually only up to the end of yesterday with no data for today. Octopus could change this in future, of course.

How do I use it? Full instructions below but in brief: clone the GitHub repo, run app.py, visit "127.0.0.1:5454" in a browser. There is also a file you can put on your Mac desktop (or put a symlink there) that, when double clicked, will run the script and pop up a webpage (more below).

Did I hand code this myself? Definitely not. I used Claude to create the Python file and the HTML template file and itterated on that , making suggested edits for tweaks, in Emacs in a Zshell.

So what did I learn?: What flask is; tracking down processes to kill, knowing only the port they're listening to (lsof), that AppleScript can run in a Bash script; that you can run a script in a conda environment in one line of code; make your text editor's backup files invisible to git so your API key doesn't end up in GitHub (the included .gitignore handles this for Emacs only).

## What it does

- Fetches half-hourly electricity consumption (kWh) and gas consumption (m³) from my smart meters via the Octopus API
- Fetches half-hourly "Agile Octopus" tarrif unit rates (pence per kWh) — prices that change every 30 minutes based on the wholesale electricity market
- Calculates the cost of each half-hour slot by multiplying consumption by the unit rate
- Displays everything as interactive charts using [Plotly.js](https://plotly.com/javascript/), with:
  - A toggle between consumption and cost views for both electricity and gas
  - A teal overlay showing the average half-hour cost per day so you can see the daily trend, up or down.
  - An amber line showing how the Agile unit rate varied throughout the day
  - Alternating day bands so it is easy to see where each calendar day begins and ends
  - A hover tooltip showing slot cost, day total, day average and unit rate
  - Preset date range buttons (2 days, 7 days, 30 days, 90 days)

## Why it runs locally

The Octopus API requires an API key for authentication. Running the dashboard as a local Flask application means the key never leaves my machine and never appears in the browser or in any public code. Flask acts as a secure proxy: the browser talks to Flask, Flask talks to the Octopus API with the secret key, and returns the data to the browser.

## Tech stack

- **Python 3.14** with **Flask** — local web server and API proxy
- **Conda** — environment and package management
- **Plotly.js** — interactive charting in the browser
- **Octopus Energy REST API** — smart meter data and Agile tariff rates
- **python-dotenv** — loads API credentials from a local `.env` file that is never committed to GitHub
- **bash and AppleScript** - an optional Bash script that runs some Applescript to pop up a browser window on the current desktop but allows you to kill the python script by killing of the automatically minised terminal window that was created.

## Project structure
```
octopus_energy_dashboard/
├── app.py              # Flask backend — serves the page and proxies API calls
├── requirements.txt    # Python dependencies
├── templates/
│   └── index.html      # Frontend — HTML, CSS and JavaScript (Plotly charts)
├── .env                # Your secret credentials (never committed to Git)
├── .gitignore          # Ensures .env and other local files are excluded
└── README.md           # This file
└── octodashb.command   # make a symlink on the desktop (or copy it there) so you can click to pop up a browser window
```

## Setup

1. Clone the repository
2. Create and activate a Conda environment:
```zsh
   conda create -n octopus_energy_dashboard python=3.14
   conda activate octopus_energy_dashboard
```
3. Install dependencies:
```zsh
   python3 -m pip install flask requests python-dotenv
```
4. Create a `.env` file in the project root (see `.env.example` for the required keys)
5. Run the app:
```zsh
   python3 app.py
```
6. Open `http://127.0.0.1:5454` in your browser
7. Optionally, copy octodashb.command to your Desktop and double click it. It will do the above, with a delay before popping open a Firefox window. If you don't have that installed, edit octodashb.command. To kill the program, right click on Terminal in the dock, find the obvious terminal window (with "⚡️ OCTOPUS DASHBOARD ENGINEE" in its name), click to restore itt and then kill it. 

## Credentials needed

You will need the following from your Octopus account and bills:

| Variable | Description |
|---|---|
| `OCTOPUS_API_KEY` | Your Octopus API key (from your account page) |
| `ELECTRICITY_MPAN` | Your electricity meter point number |
| `ELECTRICITY_SERIAL` | Your electricity meter serial number |
| `GAS_MPRN` | Your gas meter point reference number |
| `GAS_SERIAL` | Your gas meter serial number |
| `ELEC_PRODUCT_CODE` | Your Agile product code e.g. `AGILE-24-10-01` |
| `ELEC_TARIFF_CODE` | Your Agile tariff code e.g. `E-1R-AGILE-24-10-01-H` |

## Caveats

I am running this on MacOS Sequoia 15.7.4. I can't vouch for the portability of this setup. Other than the click-to-launch Bash script, there shouldn't be anything too exotic. Have a go, tell Claude your errors and that it worked on MacOS 15.7.4 . You'll be sorted in no time.
