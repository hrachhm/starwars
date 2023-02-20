# Star Wars API and Web App

## How to run
- Make sure you have Docker and Docker Compose installed on your system.
- Open a terminal window and navigate to the directory where the docker-compose.yaml file is saved.
- Run the command docker-compose up to start the containers defined in the docker-compose.yaml file.
- Wait for the process to finish. Once it is done, you should see a message indicating that the server is running on port 8000.
- Open a web browser and go to http://localhost:8000 to access the home page of the app.


## How it works 

The app works with the metadata table in the database. Here's how it works:

- On each run, the app checks for the etag and performs further steps accordingly.
- If there is no data, the app downloads data from the API endpoint.
- The app then performs required transformations on the data and saves it to a CSV file.
- On each run, the app checks for updated data by making one API call to get the latest etag.
- The app then compares the etag with the one that was stored in the database.
- If the etags are the same, the app creates a pseudo-file in the database and links it to the latest file that was downloaded before.
- The app sends a message indicating the status of the process.


## Comments on how the app can be further improved and optimized

The app can be improved and optimized in the following ways:

- The front-end part has a lot of space for improvement.
- Because AWAPI doesn't provide any documentation on how to filter out edited data only, it is not possible to do incremental loads. But as an improvement, it is a must-have feature for such cases to decrease the number of API calls and optimize the solution.
- On the other hand, if the data is quite big, the CSV file can be read by chunks, which will speed up processes and use fewer resources.
- Another solution would be to partition the CSV file and then store them into a directory (data lake solution implementation).
- Speaking about storing the files, it will be better to store them in cloud storage services such as AWS S3 bucket for better scalability and reliability.

