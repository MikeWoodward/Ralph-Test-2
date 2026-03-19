from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

MBTA_API_BASE_URL = "https://api-v3.mbta.com"


class MBTA:
    """MBTA API client class for interacting with the MBTA V3 API.
    
    The API key is loaded from environment variables or .env file
    and stored as an instance variable.
    """
    
    def __init__(self) -> None:
        """Initialize the MBTA client by loading and storing the API key.
        
        Raises:
            RuntimeError: If MBTA_V3_API_KEY is not set in the environment
                or .env file.
        """

        # Get the api key — .env lives in the Django project root (one level up)
        project_root = Path(__file__).resolve().parent.parent
        dotenv_path = project_root / ".env"
        if dotenv_path.exists():
            load_dotenv(
                dotenv_path=dotenv_path,
                override=False,
            )
        
        api_key = os.getenv("MBTA_V3_API_KEY")
        if not api_key:
            raise RuntimeError(
                "MBTA_V3_API_KEY is not set in the environment or .env file.",
            )
        self.api_key = api_key

        # Defines some variables
        self.lines = []
    
    def _print_exception_with_line_number(
        self,
        error: Exception,
    ) -> None:
        """Print the exception and the line number where it occurred.
        
        Args:
            error: The exception to print.
        """
        traceback_info = error.__traceback__
        while traceback_info and traceback_info.tb_next:
            traceback_info = traceback_info.tb_next

        line_number = (
            traceback_info.tb_lineno if traceback_info else "unknown"
        )
        print(f"Exception on line {line_number}: {error}")

    def _get_subway_line_names(
        self,
    ) -> list[str]:
        """Fetch and return the names of all MBTA subway lines."""
        try:
            response = requests.get(
                url=f"{MBTA_API_BASE_URL}/routes",
                params={
                    "filter[type]": "0,1",
                },
                headers={
                    "x-api-key": self.api_key,
                },
                timeout=10,
            )
            response.raise_for_status()

            data: dict[str, Any] = response.json()
            base_names: set[str] = set()

            for line in data.get("data", []):
                name = (
                    line.get("attributes", {})
                    .get("long_name", "")
                )
                if not name:
                    continue

                if " Line" in name:
                    index = name.find(" Line")
                    base_name = f"{name[:index]} Line"
                    base_names.add(base_name)
                elif " Trolley" in name:
                    base_names.add(name)

            line_names = sorted(base_names)

            return line_names
        except Exception as error:  # noqa: BLE001
            self._print_exception_with_line_number(
                error=error,
            )
            raise

    def _get_lines(
        self,
    ) -> list[dict[str, Any]]:
        """Fetch MBTA lines from the V3 API and return the JSON data list.
        
        Returns:
            List of line dictionaries.
        """
        try:
            response = requests.get(
                url=f"{MBTA_API_BASE_URL}/lines",
                headers={"x-api-key": self.api_key},
                timeout=10,
            )
            response.raise_for_status()

            data = response.json()

            # Prepare the data in a format we can use.
            # First, select only subway lines
            subway_line_names = self._get_subway_line_names()
            subset = [
                x
                for x in data.get("data", [])
                if (
                    x.get("attributes", {}).get("long_name")
                    in subway_line_names
                )
            ]

            # Now, restructure the data to a more usable format.
            line_data = [
                {
                    "name": x.get("attributes", {}).get("long_name"),
                    "line_color": x.get("attributes", {}).get("color"),
                    "line_name": x.get("id")
                }
                for x in subset
            ]

            return line_data

        except Exception as error:  # noqa: BLE001
            self._print_exception_with_line_number(
                error=error,
            )
            raise

    def _get_route_alerts(
        self,
        *,
        route: str,
    ) -> list[dict[str, Any]]:
        """Fetch current alerts for a specific route from MBTA API.
        
        Args:
            route: Route name (e.g., "Orange", "Red", "Blue").
            
        Returns:
            List of alert dictionaries from the API response.
        """
        params = {
            "filter[route]": route,
        }
        
        try:
            response = requests.get(
                url=f"{MBTA_API_BASE_URL}/alerts",
                params=params,
                headers={"x-api-key": self.api_key},
                timeout=10,
            )
            response.raise_for_status()
            
            data = response.json()

            # Sort so the lowest number for severity is at the top
            data.get("data", []).sort(
                key=lambda x: x.get("attributes", {}).get(
                    "severity", "Unknown Severity"
                ),
                reverse=False,
            )
            return data.get("data", [])
        
        except Exception as error:  # noqa: BLE001
            self._print_exception_with_line_number(
                error=error,
            )
            raise

    def _decode_polyline(
        self,
        polyline: str,
    ) -> list[tuple[float, float]]:
        """Decode Google's encoded polyline string into lat/lng coordinates.
        
        Args:
            polyline: Encoded polyline string from MBTA API.
            
        Returns:
            List of (latitude, longitude) tuples in order.
        """
        if not polyline:
            return []
        
        coordinates = []
        index = 0
        lat = 0
        lng = 0
        
        while index < len(polyline):
            # Decode latitude
            shift = 0
            result = 0
            while True:
                byte = ord(polyline[index]) - 63
                index += 1
                result |= (byte & 0x1F) << shift
                shift += 5
                if byte < 0x20:
                    break
            delta_lat = ~(result >> 1) if (result & 1) else (result >> 1)
            lat += delta_lat
            
            # Decode longitude
            shift = 0
            result = 0
            while True:
                byte = ord(polyline[index]) - 63
                index += 1
                result |= (byte & 0x1F) << shift
                shift += 5
                if byte < 0x20:
                    break
            delta_lng = ~(result >> 1) if (result & 1) else (result >> 1)
            lng += delta_lng
            
            # Convert to decimal degrees (encoded as integers * 1e5)
            coordinates.append((lat / 1e5, lng / 1e5))
        
        return coordinates

    def _get_route_shapes(
        self,
        *,
        route: str,
    ) -> list[list[tuple[float, float]]]:
        """Fetch shapes data for a specific route from MBTA API and return decoded coordinates.
        
        Args:
            route: Route name (e.g., "Orange", "Red", "Blue").
            
        Returns:
            List of lists of (latitude, longitude) tuples, in shape order.
        """
        
        try:
            response = requests.get(
                url=f"{MBTA_API_BASE_URL}/shapes",
                params={"filter[route]": route},
                headers={"x-api-key": self.api_key},
                timeout=10,
            )
            response.raise_for_status()
            
            data = response.json()
            shapes = data.get("data", [])
            
            # Decode all polylines into a list of lists.
            # Each list is a polyline decoded to lat/lng coordinates.
            coordinates = [
                self._decode_polyline(
                    shape.get("attributes", {}).get("polyline", "")
                )
                # Only include canonical shapes
                for shape in shapes if shape.get("id").startswith("canonical-")
            ]
            
            return coordinates
        
        except Exception as error:  # noqa: BLE001
            self._print_exception_with_line_number(
                error=error,
            )
            raise

    def _get_route_stations(
        self,
        *,
        route: str,
    ) -> list[dict[str, Any]]:
        """Fetch all stops for a specific route from MBTA API.
        
        Args:
            route: Route name (e.g., "Orange", "Red", "Blue").
            
        Returns:
            List of stop dictionaries from the API response.
        """
        params = {
            "filter[route]": route,
        }
        
        try:
            response = requests.get(
                url=f"{MBTA_API_BASE_URL}/stops",
                params=params,
                headers={"x-api-key": self.api_key},
                timeout=10,
            )
            response.raise_for_status()
            
            data = response.json()

            stops = [
                {
                    "station_id": stop.get("id", ""),
                    "name": stop.get("attributes", {}).get("name", ""),
                    "latitude": stop.get("attributes", {}).get("latitude", ""),
                    "longitude": stop.get("attributes", {}).get("longitude", ""),
                    "address": stop.get("attributes", {}).get("address", ""),
                }
                for stop in data.get("data", [])
            ]

            return stops
        
        except Exception as error:  # noqa: BLE001
            self._print_exception_with_line_number(
                error=error,
            )
            raise

    def _get_station_data(
        self,
        *,
        station_id: str,
    ) -> dict[str, Any] | None:
        """Fetch a single station (stop) by ID from MBTA API.
        
        Args:
            station_id: Station/stop ID (e.g., "place-north").
            
        Returns:
            Station dictionary with id, name, latitude, longitude,
            address, and facilities, or None if station not found.
        """
        params = {
            "filter[id]": station_id,
        }
        
        try:
            # Get the station data
            response = requests.get(
                url=f"{MBTA_API_BASE_URL}/stops",
                params=params,
                headers={"x-api-key": self.api_key},
                timeout=10,
            )
            response.raise_for_status()
            
            data = response.json()
            stops = data.get("data", [])
            
            if not stops:
                return None
            
            stop = stops[0]
            stop_data = {
                "id": stop.get("id", ""),
                "name": stop.get("attributes", {}).get("name", ""),
                "latitude": stop.get("attributes", {}).get("latitude", ""),
                "longitude": stop.get("attributes", {}).get("longitude", ""),
                "address": stop.get("attributes", {}).get("address", ""),
            }

            # Get the facilities for the station
            params = {
                "filter[stop]": station_id,
            }
            response = requests.get(
                url=f"{MBTA_API_BASE_URL}/facilities",
                params=params,
                headers={"x-api-key": self.api_key},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            facilities = data.get("data", [])

            facility_data = []
            for facility in facilities:
                # Some types to ignore
                if facility.get('attributes', {}).get('type', '') in ['PICK_DROP']:
                    continue
                text = facility.get("attributes", {}).get("short_name", "")
                # Remove numbers from the text
                text = re.sub(r'\d+', '', text)
                # Remove any text inside brackets and remove the bracket
                text = re.sub(r'\[.*?\]', '', text)
                # Remove leading and trailing spaces
                text = text.strip()
                # Remove more than two spaces leaving just one space
                text = re.sub(r'  +', ' ', text)
                # Add the type of facility at the front of the text
                facility_type = facility.get('attributes', {}).get('type', '')
                text = f"{facility_type}: {text}"
                # Add the text to the facility data
                facility_data.append(text)
            # Remove any duplicates
            facility_data = list(set(facility_data))
            # Order alphabetically
            facility_data.sort()

            # Add the facility data to the stop data
            stop_data['facilities'] = facility_data

            return stop_data
        except Exception as error:  # noqa: BLE001
            self._print_exception_with_line_number(
                error=error,
            )
            raise

    def _get_route_lines(
        self,
        *,
        line_names: list[str],
    ) -> list[dict[str, Any]]:
        """Fetch route information from MBTA API.
        
        Args:
            line_names: List of line names to filter routes by.
            
        Returns:
            List of route dictionaries from the API response.
        """
        try:
            response = requests.get(
                url=f"{MBTA_API_BASE_URL}/routes",
                headers={"x-api-key": self.api_key},
                timeout=10,
            )
            response.raise_for_status()
            
            data = response.json()
            # Single route response is wrapped in a data object
            route_data = data.get("data")

            if not route_data:
                return []
            
            route_data = [
                {
                    'route_name': route.get('attributes', {}).get(
                        'long_name', ''
                    ),
                    'line_name': route.get('relationships', {}).get(
                        'line', {}
                    ).get('data', {}).get('id', ''),
                }
                for route in route_data
                if route.get('relationships', {}).get('line', {}).get(
                    'data', {}
                ).get('id', '') in line_names
            ]
            return route_data
        
        except Exception as error:  # noqa: BLE001
            self._print_exception_with_line_number(
                error=error,
            )
            raise

    def _get_lines_data(
        self,
    ) -> list[dict[str, Any]]:
        """Build out complete line data including routes, shapes, and stations.
        
        Note: This method returns static/semi-static data that changes very rarely
        (e.g., when new stations are built or routes are modified). This data can
        be cached and reused across multiple API calls. The returned data structure
        is stored in self.lines for use by other methods.
        
        Returns:
            List of line dictionaries, where each dictionary contains:
            
            - "name" (str): The full display name of the line
              (e.g., "Red Line", "Green Line", "Orange Line").
            
            - "line_color" (str): Hex color code for the line
              (e.g., "#DA291C" for Red Line).
            
            - "line_name" (str): The internal line identifier from the MBTA API
              (e.g., "line-Red", "line-Green").
            
            - "route_names" (list[str]): List of full route names associated
              with this line (e.g., ["Red Line", "Ashmont", "Braintree"]).
              This list is populated by matching routes to the line.
            
            - "route_id" (list[str]): List of normalized route names
              used for API calls. These are derived from route_names with
              " Line" and " Trolley" suffixes removed and spaces replaced with
              hyphens (e.g., ["Red", "Ashmont", "Braintree"]).
            
            - "shapes" (list[list[tuple[float, float]]]): List of shape
              coordinate lists. Each inner list contains tuples of
              (latitude, longitude) coordinates representing the route path.
              Multiple shapes may exist for a line if it has multiple branches.
              Structure: [[(lat1, lng1), (lat2, lng2), ...], ...]
            
            - "stations" (list[dict[str, Any]]): List of station dictionaries
              for all stations on all routes of this line. Each station dict
              contains:
              - "station_id" (str): Unique station identifier
                (e.g., "place-north").
              - "name" (str): Station display name.
              - "latitude" (float): Station latitude coordinate.
              - "longitude" (float): Station longitude coordinate.
              - "address" (str): Station street address.
        """
        # Build out the lines data
        # This creates the base line structure with name, color, and line_name
        self.lines = self._get_lines()
        
        # Get the route names and associate them with each line
        # This populates route_names and route_id for each line dictionary
        line_names = [line['line_name'] for line in self.lines]
        routes_lines = self._get_route_lines(line_names=line_names)
        
        # Associate routes with their corresponding lines
        # Each line dict will have route_names (full names) and route_id (normalized)
        for rl in routes_lines:
            for line in self.lines:
                if rl['line_name'] == line['line_name']:
                    if 'route_names' not in line:
                        line['route_names'] = []
                        line['route_id'] = []
                    line['route_names'].append(rl['route_name'])
                    line['route_id'].append(
                        rl['route_name']
                        .replace(" Line", "")
                        .replace(" Trolley", "")
                        .replace(" ", "-")
                    )
        
        # Get shapes and stations for each route
        # Shapes: List of coordinate lists [[(lat, lng), ...], ...]
        # Stations: List of station dicts [{"station_id": ..., "name": ..., ...}, ...]
        for line in self.lines:
            line['shapes'] = []
            line['stations'] = []
            
            for route in line['route_id']:
                line['shapes'] += self._get_route_shapes(route=route)
                line['stations'] += self._get_route_stations(route=route)
        
        return self.lines

    def _get_line_by_name(
        self,
        *,
        line_name: str,
    ) -> dict[str, Any] | None:
        """Return the line dictionary matching the given display line name."""
        if not self.lines:
            self.initialize()

        for line in self.lines:
            if line.get("name") == line_name:
                return line

        return None

    def initialize(
        self,
    ) -> None:
        """Initialize static MBTA data required by real-time methods.
        
        This method populates self.lines with static/semi-static data for all
        subway lines, including routes, shapes, and stations. It should be
        called once after constructing the MBTA client and before calling
        methods that rely on self.lines, such as get_predictions.
        """
        self._get_lines_data()

    def get_line_names(
        self,
    ) -> list[str]:
        """Return the names of all subway lines sorted alphabetically.
        
        If static line data has not yet been loaded, this method will
        initialize it by calling initialize().
        
        Returns:
            List of line names sorted alphabetically.
        """
        if not self.lines:
            self.initialize()
        
        return sorted(
            [
                line.get("name", "")
                for line in self.lines
            ],
        )

    def get_line(
        self,
        *,
        line_name: str,
    ) -> dict[str, Any] | None:
        """Return core data for the specified subway line.
        
        Args:
            line_name: Display name of the line (e.g., "Red Line").
        
        Returns:
            Dictionary containing:
            - "line_color": Hex color code for the line.
            - "shapes": List of polyline coordinate lists.
            - "stations": List of station dictionaries including "station_id".
            
            Returns None if the line is not found.
        """
        line = self._get_line_by_name(
            line_name=line_name,
        )
        if not line:
            return None

        return {
            "line_color": line.get("line_color"),
            "shapes": line.get("shapes", []),
            "stations": line.get("stations", []),
        }

    def get_station(
        self,
        *,
        station_id: str,
    ) -> dict[str, Any] | None:
        """Return detailed data for the specified station.
        
        Args:
            station_id: Station/stop ID (e.g., "place-knncl").
        
        Returns:
            Station dictionary as returned by _get_station_data, or None
            if the station is not found.
        """
        return self._get_station_data(
            station_id=station_id,
        )

    def get_station_facilities(
        self,
        *,
        station_id: str,
    ) -> list[str]:
        """Return the facilities data for the specified station.
        
        Args:
            station_id: Station/stop ID (e.g., "place-knncl").
        
        Returns:
            List of facility description strings for the station. Returns
            an empty list if the station is not found or has no facilities.
        """
        station_data = self._get_station_data(
            station_id=station_id,
        )
        if not station_data:
            return []

        facilities = station_data.get("facilities") or []
        return list(facilities)

    def get_line_alerts(
        self,
        *,
        line_name: str,
    ) -> list[dict[str, Any]]:
        """Fetch current alerts for all routes on a specific line.
        
        Note: This method returns real-time data that changes frequently
        (e.g., service disruptions, delays, closures). This data should be
        fetched fresh for each request and not cached for extended periods.
        
        Args:
            line_name: Display name of the line (e.g., "Red Line").
            
        Returns:
            List of alert dictionaries, each containing:
            - "headline" (str): Alert header/title describing the issue
              (e.g., "Service disruption on Red Line").
            - "severity" (int): Alert severity level (lower numbers indicate
              higher severity). Alerts are sorted by severity (lowest first).
        """
        try:
            line = self._get_line_by_name(
                line_name=line_name,
            )
            if not line:
                return []

            route_ids = line.get("route_id", [])
            all_alerts: list[dict[str, Any]] = []

            for route in route_ids:
                route_alerts = self._get_route_alerts(
                    route=route,
                )
                all_alerts.extend(route_alerts)

            all_alerts.sort(
                key=lambda x: x.get("severity"),
                reverse=False,
            )

            return all_alerts
        except Exception as error:  # noqa: BLE001
            self._print_exception_with_line_number(
                error=error,
            )
            raise

    def get_predictions(
        self,
        *,
        station_id: str,
    ) -> list[dict[str, Any]]:
        """Fetch predicted arrival times for a specific stop from MBTA API.
        
        Note: This method returns real-time data that changes frequently
        (e.g., train arrival predictions update every few seconds). This data
        should be fetched fresh for each request and not cached. Only returns
        predictions for subway routes (filtered from self.lines) and excludes
        cancelled trains.
        
        Args:
            station_id: MBTA stop ID (e.g., "place-gover").
            
        Returns:
            List of prediction dictionaries, each containing:
            - "route" (str): Route identifier (e.g., "Red", "Green-B",
              "Orange", "Blue").
            - "destination" (str): Train destination (trip headsign, e.g.,
              "Alewife", "Braintree").
            - "arrival_time" (str | None): Predicted arrival time in ISO 8601
              format (e.g., "2024-01-15T14:30:00-05:00"), or None if not
              available.
            - "departure_time" (str | None): Predicted departure time in ISO
              8601 format, or None if not available.
            - "comments" (str | None): Status information (e.g., "Stopped at
              station", "Boarding") or None if no status.
            
            Results are sorted by route, then arrival_time, then departure_time.
        """
        try:
            # Get all subway route IDs from static line data
            # This filters predictions to only subway routes (not buses, etc.)
            subway_ids = [
                route_id
                for line in self.lines
                for route_id in line['route_id']
            ]

            # Get real-time predictions for the given station
            # The API returns predictions with related trip, vehicle, and stop data
            response = requests.get(
                url=f"{MBTA_API_BASE_URL}/predictions",
                params={
                    "filter[stop]": station_id,
                    "include": "trip,vehicle,stop",
                },
                headers={"x-api-key": self.api_key},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            predictions = data.get("data", [])

            # Filter the predictions to only subway routes and exclude cancelled trains
            # Each prediction has relationships.route.data.id and
            # attributes.schedule_relationship
            predictions = [
                prediction
                for prediction in predictions
                if (
                    prediction['relationships']['route']['data']['id'] in subway_ids
                    and prediction['attributes']['schedule_relationship'] != 'CANCELLED'
                )
            ]

            # Process predictions to extract useful information
            # Build a lookup dict from the included data (trips, vehicles, stops)
            # Structure: {trip_id: trip_data, vehicle_id: vehicle_data, ...}
            processed_predictions = []
            included = {
                item.get("id"): item
                for item in data.get("included", [])
            }

            # Extract and structure prediction data
            # Each processed prediction dict contains:
            # - route: Route ID (e.g., "Red", "Orange")
            # - destination: Trip headsign (e.g., "Alewife", "Braintree")
            # - arrival_time: ISO 8601 timestamp or None
            # - departure_time: ISO 8601 timestamp or None
            # - comments: Status string (e.g., "Stopped at station") or None
            for prediction in predictions:
                # Get trip ID from prediction relationships
                trip_id = (
                    (prediction.get("relationships") or {})
                    .get("trip", {})
                    .get("data", {})
                    .get("id")
                )
                # Look up trip info from included data
                trip_info = included.get(trip_id, {}) if trip_id else {}

                processed_predictions.append({
                    "route": (
                        (trip_info.get("relationships") or {})
                        .get("route", {})
                        .get("data", {})
                        .get("id")
                    ) or "Unknown",
                    "destination": (
                        (trip_info.get("attributes") or {}).get("headsign")
                    ) or "Unknown",
                    "arrival_time": (
                        (prediction.get("attributes") or {}).get("arrival_time")
                    ),
                    "departure_time": (
                        (prediction.get("attributes") or {})
                        .get("departure_time")
                    ),
                    "comments": (
                        (prediction.get("attributes") or {}).get("status")
                    ) or None,
                })

            # Sort by route, then arrival_time, then departure_time
            # This groups predictions by route and orders them chronologically
            processed_predictions.sort(
                key=lambda p: (
                    p.get("route", ""),
                    p.get("arrival_time") or "9999-12-31T23:59:59Z",
                    p.get("departure_time") or "9999-12-31T23:59:59Z",
                ),
            )

            return processed_predictions
        except Exception as error:  # noqa: BLE001
            self._print_exception_with_line_number(
                error=error,
            )
            raise


if __name__ == "__main__":
    # Create the MBTA class instance
    mbta = MBTA()

    # Load time fetches
    # -----------------
    # Initialize static line data
    mbta.initialize()

    # Get the line names
    print("")
    print("Getting line names")
    print("-------------------")
    line_names = mbta.get_line_names()
    print(line_names)

    line_name = "Red Line"
    station_id = "place-knncl"

    # Get line data
    print(f"Getting data for the {line_name} Line")
    print("-------------------------------")
    line_data = mbta.get_line(line_name=line_name)
    print(line_data)

    # Get the alerts for the Red Line
    print(f"Getting alerts for the {line_name} Line")
    print("-------------------------------")
    line_alerts = mbta.get_line_alerts(line_name=line_name)
    print(line_alerts)

    # Get facilities data for the station
    print(f"Getting facilities data for the {station_id} station")
    print("-------------------------------------------------")
    facilities_data = mbta.get_station_facilities(station_id=station_id)
    print(facilities_data)

    # Get the predictions for the station
    print(f"Getting predictions for the {station_id} station")
    print("---------------------------------------------")
    predictions = mbta.get_predictions(station_id=station_id)
    print(predictions)

    # End of program
    print("")
    print("End of program")
    print("-------------")
