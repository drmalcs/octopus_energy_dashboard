# app.py
# This is the Flask backend for the Octopus Energy Dashboard.
# It does two things:
#   1. Serves the web page (templates/index.html) when you open a browser
#   2. Acts as a secure proxy to the Octopus Energy API, keeping your
#      API key secret on your local machine

# --- Imports ---

# Flask        : the web framework itself
# jsonify      : converts Python dicts/lists into JSON responses for the browser
# render_template : loads and serves HTML files from the templates/ folder
# request      : a special Flask object that is automatically populated each time
#                the browser makes a request to one of our routes. It contains
#                everything about that request: the URL, any parameters, headers,
#                etc. Flask creates and manages this object behind the scenes —
#                we just import it and use it. It is not something we create
#                ourselves.
from flask import Flask, jsonify, render_template, request

# The 'requests' library (note: different from Flask's 'request' above) makes
# outgoing HTTP calls to external APIs — in our case, the Octopus Energy API.
# Flask's 'request' is about incoming requests FROM the browser.
# 'requests' (the library) is about outgoing requests TO other servers.
import requests

# os.environ lets us read environment variables loaded from the .env file
import os

# load_dotenv reads the .env file and loads its contents into os.environ
from dotenv import load_dotenv

# For handling and formatting dates and times
from datetime import datetime, timezone

# urlparse and parse_qs are used to extract parameters from paginated URLs
# that the Octopus API returns when there are more results to fetch
from urllib.parse import urlparse, parse_qs

# --- Load credentials ---

# This reads your .env file and makes its contents available via os.environ.
# It must be called before we try to read any environment variables below.
load_dotenv()

# Read our credentials and meter details from the environment.
# These were set in the .env file and loaded by load_dotenv() above.
# Using environment variables keeps secrets out of the code itself,
# which means it is safe to put this file on GitHub.
API_KEY     = os.environ.get("OCTOPUS_API_KEY")
ELEC_MPAN   = os.environ.get("ELECTRICITY_MPAN")
ELEC_SERIAL = os.environ.get("ELECTRICITY_SERIAL")
GAS_MPRN    = os.environ.get("GAS_MPRN")
GAS_SERIAL  = os.environ.get("GAS_SERIAL")
# Agile tariff identifiers — needed to fetch half-hourly unit rates.
# ELEC_PRODUCT_CODE e.g. "AGILE-24-10-01"
# ELEC_TARIFF_CODE  e.g. "E-1R-AGILE-24-10-01-H"  (H = your GSP region)
ELEC_PRODUCT_CODE = os.environ.get("ELEC_PRODUCT_CODE")
ELEC_TARIFF_CODE  = os.environ.get("ELEC_TARIFF_CODE")

# --- Octopus API base URL ---

# All Octopus API endpoints start with this URL.
# We define it once here so it is easy to update if it ever changes.
OCTOPUS_BASE = "https://api.octopus.energy/v1"

# --- Create the Flask app ---

# This creates the Flask application object. __name__ tells Flask where to
# look for templates and static files (i.e. in the same directory as this file).
# All our routes (URL handlers) are attached to this object.
app = Flask(__name__)

# --- Helper function ---

def fetch_octopus(endpoint, params=None):
    """
    Makes an authenticated GET request to the Octopus API.

    endpoint : the path after OCTOPUS_BASE, e.g. "/electricity-meter-points/..."
    params   : optional dict of query parameters, e.g. {"page_size": 100}

    Returns the parsed JSON response as a Python dict, or raises an error.

    Authentication: Octopus uses HTTP Basic Auth where the API key is the
    username and the password is left empty. The requests library handles
    this with the auth=(username, password) parameter.
    """
    # Build the full URL by combining the base URL with the specific endpoint
    url = f"{OCTOPUS_BASE}{endpoint}"

    # Make the GET request with Basic Auth. API_KEY is the username,
    # empty string is the password (Octopus does not require one).
    response = requests.get(url, auth=(API_KEY, ""), params=params)

    # If the request failed (e.g. wrong API key, bad URL), this raises
    # an exception immediately rather than silently returning bad data
    response.raise_for_status()

    # Parse the JSON response body into a Python dict and return it
    return response.json()

# --- Routes ---
# A "route" in Flask maps a URL path to a Python function.
# When the browser requests that URL, Flask calls the corresponding function
# and returns whatever that function sends back.
# The @app.route decorator is what registers each function as a route handler.

@app.route("/")
def index():
    """
    Serves the main web page.
    When you open http://localhost:5000 in your browser, Flask finds
    templates/index.html and sends it to the browser.
    """
    return render_template("index.html")


@app.route("/api/electricity-consumption")
def electricity_consumption():
    """
    Fetches half-hourly electricity consumption from the Octopus API
    and returns it as JSON to the browser.

    The Octopus API returns consumption in kWh for each 30-minute slot.
    Results are paginated (returned in pages of up to 100 records).
    We loop through all pages to collect the full dataset before returning.

    The browser can optionally pass date range parameters in the URL:
      /api/electricity-consumption?period_from=2024-01-01T00:00:00Z&period_to=2024-01-31T23:30:00Z
    """
    # request.args is a dictionary that Flask automatically populates with any
    # parameters the browser appended to the URL after a '?'. For example:
    #   /api/electricity-consumption?period_from=2024-01-01&period_to=2024-02-01
    # Flask parses that query string and makes it available here as request.args.
    # .get() is used instead of request.args["period_from"] so that if no date
    # range is provided, we get None rather than a crash.
    period_from = request.args.get("period_from")
    period_to   = request.args.get("period_to")

    # Build the initial query parameters to send to the Octopus API.
    # page_size=100 requests the maximum number of records per page.
    # order_by="period" returns results in chronological order.
    params = {
        "page_size": 100,
        "order_by": "period",
    }

    # Only add date range parameters if they were provided by the browser.
    # If neither is provided, Octopus returns its most recent available data.
    if period_from:
        params["period_from"] = period_from
    if period_to:
        params["period_to"] = period_to

    # The endpoint URL is specific to your meter, identified by:
    #   ELEC_MPAN   : your electricity meter point administration number
    #   ELEC_SERIAL : your meter's serial number
    endpoint = (
        f"/electricity-meter-points/{ELEC_MPAN}"
        f"/meters/{ELEC_SERIAL}/consumption/"
    )

    # Paginate through all available results.
    # The Octopus API returns a "next" URL in the response if there are
    # more pages of data. We keep fetching until "next" is None.
    all_results = []
    while True:
        data = fetch_octopus(endpoint, params)

        # Add this page's results to our growing list
        all_results.extend(data.get("results", []))

        # Check if there is another page of results
        if data.get("next"):
            # The "next" value is a full URL with updated query parameters.
            # We parse it to extract those parameters for the next request.
            parsed = urlparse(data["next"])
            next_params = parse_qs(parsed.query)
            # parse_qs returns each value as a list e.g. {"page": ["2"]}
            # We flatten those to single values e.g. {"page": "2"}
            params = {k: v[0] for k, v in next_params.items()}
        else:
            # No more pages — we have all the data
            break

    # jsonify converts the Python list into a JSON HTTP response
    # that the browser's JavaScript can read and use to draw graphs
    return jsonify(all_results)


@app.route("/api/gas-consumption")
def gas_consumption():
    """
    Fetches half-hourly gas consumption from the Octopus API.

    Gas is measured in cubic metres (m³) by the smart meter.
    The Octopus API returns this raw m³ figure in the consumption field.
    Note: your bill converts m³ to kWh using a calorific value — we will
    handle that conversion in the frontend if needed.

    The structure of this function is identical to electricity_consumption()
    above — see that function for detailed comments on each step.
    """
    # See electricity_consumption() for a detailed explanation of request.args
    period_from = request.args.get("period_from")
    period_to   = request.args.get("period_to")

    params = {
        "page_size": 100,
        "order_by": "period",
    }
    if period_from:
        params["period_from"] = period_from
    if period_to:
        params["period_to"] = period_to

    # Gas endpoint uses MPRN (meter point reference number) and serial number
    endpoint = (
        f"/gas-meter-points/{GAS_MPRN}"
        f"/meters/{GAS_SERIAL}/consumption/"
    )

    all_results = []
    while True:
        data = fetch_octopus(endpoint, params)
        all_results.extend(data.get("results", []))
        if data.get("next"):
            parsed = urlparse(data["next"])
            next_params = parse_qs(parsed.query)
            params = {k: v[0] for k, v in next_params.items()}
        else:
            break

    return jsonify(all_results)


@app.route("/api/meter-info")
def meter_info():
    """
    Fetches basic information about your electricity meter point.
    This includes your GSP (Grid Supply Point), which identifies your
    electricity region in the UK.
    Useful for confirming the API connection is working correctly.
    """
    endpoint = f"/electricity-meter-points/{ELEC_MPAN}/"
    data = fetch_octopus(endpoint)
    return jsonify(data)


@app.route("/api/electricity-rates")
def electricity_rates():
    """
    Fetches half-hourly Agile unit rates (pence per kWh) from the Octopus API.

    Unlike the consumption endpoints, rates are not tied to your specific meter —
    they are published per tariff and GSP region. This means the URL uses your
    product and tariff codes rather than your MPAN and serial number.

    The rates endpoint is public and does not strictly require authentication,
    but we authenticate anyway for consistency.

    Returns a list of records, each containing:
      value_exc_vat : unit rate in pence per kWh, excluding VAT
      value_inc_vat : unit rate in pence per kWh, including VAT (what you pay)
      valid_from    : start of the half-hour slot
      valid_to      : end of the half-hour slot
    """
    # Read optional date range parameters from the browser request.
    # See electricity_consumption() for a detailed explanation of request.args.
    period_from = request.args.get("period_from")
    period_to   = request.args.get("period_to")

    params = {
        "page_size": 100,
        "order_by": "period",
    }
    if period_from:
        params["period_from"] = period_from
    if period_to:
        params["period_to"] = period_to

    # The rates endpoint is structured differently from the consumption endpoint.
    # It uses the product code and tariff code rather than your meter details.
    endpoint = (
        f"/products/{ELEC_PRODUCT_CODE}"
        f"/electricity-tariffs/{ELEC_TARIFF_CODE}"
        f"/standard-unit-rates/"
    )

    # Paginate through all pages — identical pattern to consumption endpoints
    all_results = []
    while True:
        data = fetch_octopus(endpoint, params)
        all_results.extend(data.get("results", []))
        if data.get("next"):
            parsed = urlparse(data["next"])
            next_params = parse_qs(parsed.query)
            params = {k: v[0] for k, v in next_params.items()}
        else:
            break

    # The rates come back in reverse chronological order even with order_by=period
    # so we sort them oldest-first to match the consumption data order
    all_results.sort(key=lambda r: r["valid_from"])

    return jsonify(all_results)

# --- Run the app ---

# This block only executes when you run this file directly with:
#   python3 app.py
# It will not run if this file is imported as a module by another script.
# debug=True enables two useful development features:
#   - Detailed error messages displayed in the browser if something goes wrong
#   - Automatic server restart when you save changes to this file
# Flask's default port is 5000 but we want to avoid Apple Airplay so this is just
# a random alternative. We could ask for an unused port but I wanted to hardcode
# this into a clickable desktop script that runs "open https://localhost:<port no>
# It's low risk and a proper warning/error will be given if it's already in use.
if __name__ == "__main__":
    app.run(debug=True, port=5454)
