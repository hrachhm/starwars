from starwars.utils.default_args import DefaultArgs
from django.shortcuts import render
from django.views.generic import View
from starwars.models import Metadata
from django.views.generic import DetailView
import datetime
from .utils.starwars_api_helper import StarwarsEtl, StarWarsLookup
import petl as etl



from django.contrib import messages


def home_view(request):
    return render(request, "index.html")


class DownloadDataView(View):
    """
    Django view that handles a GET request to download Star Wars data.
    If the `download_data` parameter is set to 'true' in the request, the view starts an ETL process to download
    data from the Star Wars API and save it to a CSV file. The file name includes the current date and time.
    If the ETL process completes successfully, a success message is added to the user's messages.
    The view then retrieves information about previously downloaded datasets from a metadata table and renders an
    HTML template that displays links to the downloaded datasets.
    """

    def get(self, request):
        """
        Handle a GET request and render the download_data.html template.

        If the 'download_data' parameter is set to 'true', download data from the Star Wars API and save it to a CSV file.
        If the download is successful, add a success message to the user's messages.

        Retrieve information about previously downloaded datasets from a metadata table and pass it to the template.
        """
        if 'download_data' in request.GET and request.GET['download_data'] == 'true':
            # If the 'download_data' parameter is set to 'true', download data from the Star Wars API and save it to a CSV file
            CSV_FILE_NAME = DefaultArgs.CSV_FILE_NAME_PREFIX+f"{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.csv"
            ETL = StarwarsEtl(
                API_URL=DefaultArgs.API_URL,
                CSV_FILE_NAME=CSV_FILE_NAME,
                CSV_FILE_PATH=DefaultArgs.DEFAULT_FILE_DIR+CSV_FILE_NAME,
                Metadata=Metadata,
                people_query = DefaultArgs.PEOPLE_QUERY,
                planets_query = DefaultArgs.PLANETS_QUERY,
            )
            message = ETL.start_starwars_data_ingestion()
            # If the download is successful, add a success message to the user's messages
            messages.success(request, message)

        # Retrieve information about previously downloaded datasets from a metadata table
        datasets = Metadata.objects.filter(table_info_type = "people").all()

        # Render the download_data.html template and pass the datasets to the template
        return render(request, "download_data.html", {"datasets": datasets})


class DatasetDetailView(DetailView):
    """
    Django view that displays a detailed view of a previously downloaded Star Wars dataset.

    This view uses the Django `DetailView` class to display detailed information about a previously downloaded dataset,
    including the dataset's file path and a table of data from the CSV file. The view transforms the raw CSV data
    into a format that can be displayed in an HTML table, and supports pagination using an offset parameter.
    """

    model = Metadata
    template_name = "dataset_detail.html"

    def get_context_data(self, **kwargs):
        """
        Get the context data for the detailed view of a dataset.

        Retrieves information about the dataset from the metadata table and passes it to the template for display.
        Transforms the raw CSV data into a format that can be displayed in an HTML table, and supports pagination
        using an offset parameter.

        Returns:
            A dictionary of context data for use in rendering the dataset_detail.html template.
        """
        context = super().get_context_data(**kwargs)

        # Retrieve information about the dataset from the metadata table
        dataset = self.get_object()

        # Load the CSV file and transform it for display
        data_lookup = StarWarsLookup()
        table = data_lookup.get_table_detailed_view(file_path=dataset.file_path)

        # Get the offset from the request parameters and calculate the start and end indices
        offset = int(self.request.GET.get("offset", "0"))
        batch_size = 10
        start = max(offset, 0)
        end = start + batch_size

        # Get the specified rows based on the offset and batch size
        rows = table[0:end]

        # Pass the transformed data, the offset, and the batch size to the template for display
        context["table"] = rows
        context["offset"] = end
        context["columns"] = etl.header(rows)
        context["is_main"] = True

        columns_basic = self.request.GET.get('columns', '')
        print("thisi is basic", columns_basic)
        # Split the values by '&?columns='
        columns = columns_basic.split('&?columns=')
        # Print the values
        print(columns)
        
        if len(columns) > 0 and columns[0] != "":
            context["table"] = data_lookup.get_calcualted_table(file_path=dataset.file_path, columns=columns)[0:]
            context["columns"] = etl.header( context["table"])
            context["is_main"] = False
            print(context["table"])

        return context

