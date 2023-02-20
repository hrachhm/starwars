import datetime
from typing import Dict

import petl as etl
import requests

from starwars.utils.default_args import DefaultArgs


class StarwarsEtl:
    def __init__(
        self,
        API_URL: str,
        CSV_FILE_NAME: str,
        CSV_FILE_PATH: str,
        Metadata,
        people_query: str,
        planets_query: str,
    ) -> None:
        self.API_URL = API_URL
        self.CSV_FILE_NAME = CSV_FILE_NAME
        self.CSV_FILE_PATH = CSV_FILE_PATH
        self.Metadata = Metadata
        self.current_etag = ""
        self.people_query = people_query
        self.planets_query = planets_query

    def get_latest_etags(self, query: str) -> str:
        """Get the latest ETag value for the given query.

        Args:
            query (str): The type of table for which to retrieve the latest ETag.

        Returns:
            str: The latest ETag value for the given query, or an empty string if no
                 metadata for the query is found.
        """

        try:
            meta = self.Metadata.objects.filter(table_info_type=query).latest("date")
            print(meta.etag)
        except self.Metadata.DoesNotExist:
            meta = None
        return meta.etag if meta else ""

    def check_for_updates(self, query: str, latest_etag: str) -> bool:
        """Check if there are updates to the data for the given query.

        Args:
            query (str): The query to check for updates.
            latest_etag (str): The latest ETag value for the query.

        Returns:
            bool: True if there are updates, False otherwise.

        Raises:
            Exception: If the API returns a non-200 status code.
        """
        url = f"{self.API_URL}/{query}"

        headers = {"If-None-Match": latest_etag}
        response = requests.get(url, headers=headers)

        if response.status_code == 304:
            print("Data has not changed since last request.")
            return False
        elif response.status_code != 200:
            raise
        else:
            return True

    def get_current_etag(self, url: str) -> str:
        """Get the current ETag value for the given URL.

        Args:
            url (str): The URL to get the ETag for.

        Returns:
            str: The current ETag value for the URL.
        """
        response = requests.get(url)
        return response.headers.get("ETag")

    def get_latest_data(self, query: str) -> Dict[str, etl.Table]:
        """Get the latest data for the given query from the API.

        Args:
            query (str): The query to get the latest data for.

        Returns:
            dict: A dictionary with keys 'etag' and 'table'. 'etag' is the current ETag value for the query,
                  or an empty string if the request failed. 'table' is a petl table containing the data.
        """
        url = f"{self.API_URL}/{query}"

        current_etag = self.get_current_etag(url=url)
        data = list()
        table = None

        if (
            self.check_for_updates(
                query=query, latest_etag=self.get_latest_etags(query)
            )
            == True
        ):
            while url:
                response = requests.get(url)
                json_data = response.json()
                data.extend(json_data["results"])
                url = json_data["next"]

            table = etl.fromdicts(data)

        return {"etag": current_etag, "table": table}

    def convert_datetime(self, date: str) -> str:
        dt = datetime.datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.%fZ")
        return dt.strftime("%Y-%m-%d")

    def get_planets_data(self) -> etl.Table:
        """
        Checks for the latest planets data. If new data is available, generates a new CSV file
        and saves it. If no new data is available, reads the latest CSV file and returns it as a
        petl table.

        Returns:
        - petl.Table

        """
        query = self.planets_query

        planets_data = self.get_latest_data(query=query)
        if planets_data["table"]:
            planets_table = etl.cut(planets_data["table"], "name", "url")
            planets_table = etl.rename(planets_table, {"name": "homeworld_name"})
            self.save_data_to_csv(
                table=planets_table,
                file_name="planets_info.csv",
                file_path=f"{DefaultArgs.DEFAULT_FILE_DIR}planets_info.csv",
                table_info_type=query,
                etag=planets_data["etag"],
            )

        else:
            file_path_latest = (
                self.Metadata.objects.filter(table_info_type=query)
                .latest("date")
                .file_path
            )
            planets_table = etl.fromcsv(file_path_latest)

        return planets_table

    def fix_planets_info_and_columns(
        self, people_info: Dict[str, etl.Table]
    ) -> etl.Table:
        """
        Returns a petl table with the following fields: 'name', 'height', 'mass',
        'hair_color', 'skin_color', 'eye_color', 'birth_year', 'date', and 'homeworld'.
        This method fixes issues related to homeworld URL, renames columns, and converts
        the 'date' field to a Python datetime object.

        Args:
            people_info: A dictionary containing information about the people table.
                The dictionary must have a 'table' key containing a petl table with the
                following fields: 'name', 'height', 'mass', 'hair_color', 'skin_color',
                'eye_color', 'birth_year', 'edited', and 'homeworld'.

        Returns:
            A petl table containing the fields described above.

        Raises:
            None
        """
        planets_table = self.get_planets_data()
        people_table = people_info["table"].join(
            planets_table, lkey="homeworld", rkey="url"
        )

        people_table = people_table.cut(
            "name",
            "height",
            "mass",
            "hair_color",
            "skin_color",
            "eye_color",
            "birth_year",
            "edited",
            "homeworld_name",
        )
        people_table = etl.convert(people_table, "edited", self.convert_datetime)

        return etl.rename(
            people_table, {"edited": "date", "homeworld_name": "homeworld"}
        )

    def save_data_to_csv(
        self,
        table: etl.Table,
        file_name: str,
        file_path: str,
        table_info_type: str,
        etag: str,
    ) -> str:
        """
        Write a petl.Table object to a CSV file at the specified path.

        Args:
            table (petl.Table): A table object containing the data to be written to the CSV file.
            file_name: CSV file name
            file_path (str): The path to the CSV file to write to.
            table_info_type: information about table data (planets ot people)
            etag: etag of the request

        Returns:
            str: message about the result
        """
        try:
            table.tocsv(file_path)
            self._log_new_metadata(
                file_name=file_name,
                file_path=file_path,
                etag=etag,
                table_info_type=table_info_type,
            )
            return f"{file_name} saved successfully "
        except Exception as e:
            return f"An error occurred while trying to save CSV file {e}"

    def _log_new_metadata(
        self,
        file_name: str,
        file_path: str,
        etag: str,
        table_info_type: str,
    ) -> None:
        """Log data files's metadata.

        Parameters
        ----------
        file_name: str
            The name of the data file.
        file_path: str
            The path of the data file.
        etag: str
            An etag associated with the data object.
        table_info_type: str
            An information of table type.

        Returns
        -------
        None
        """
        self.Metadata.objects.create(
            file_name=file_name,
            file_path=file_path,
            table_info_type=table_info_type,
            etag=etag,
        )

    def get_people_data(self) -> str:
        """Get people data from the Star Wars API and save it as a CSV file.

        Returns:
            A status message indicating whether new data was saved or not.
        """

        query = self.people_query

        people_info = self.get_latest_data(query=query)

        if people_info["table"]:
            sw_data = self.fix_planets_info_and_columns(people_info=people_info)
            print(sw_data)
            status_message = self.save_data_to_csv(
                sw_data,
                file_name=self.CSV_FILE_NAME,
                file_path=self.CSV_FILE_PATH,
                table_info_type=query,
                etag=people_info["etag"],
            )
        else:
            file_path_latest = (
                self.Metadata.objects.filter(table_info_type=query)
                .latest("date")
                .file_path
            )
            self._log_new_metadata(
                file_name=self.CSV_FILE_NAME,
                file_path=file_path_latest,
                table_info_type=query,
                etag=people_info["etag"],
            )
            status_message = "Nothing has been updated"

        return status_message

    def start_starwars_data_ingestion(self):
        status_message = self.get_people_data()
        return status_message


class StarWarsLookup:
    def get_table_detailed_view(self, file_path: str) -> etl.Table:
        table = etl.fromcsv(file_path)
        return table

    def get_calcualted_table(self, file_path: str, columns: list[str]) -> etl.Table:
        """
        Calculates the count of values for each column in the selected_columns list for the given CSV file.

        Args:
            file_path (str): The file path for the CSV file to read.
            selected_columns (List[str]): The list of column names for which to calculate the value counts.

        Returns:
            etl.Table: A table containing the value counts for each concatenated column in the selected_columns list.
        """

        table = etl.fromcsv(file_path)

        table = etl.addfield(
            etl.cut(table, columns), "concatenated", lambda row: " ".join(row)
        )

        concate = etl.aggregate(table, "concatenated", len)
        final_table = table.join(concate, lkey="concatenated", rkey="concatenated")
        final_table = etl.cutout(final_table, "concatenated")
        final_table = etl.distinct(etl.rename(final_table, {"value": "count"}))
        return final_table
